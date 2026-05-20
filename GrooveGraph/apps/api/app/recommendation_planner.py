import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import settings
from app.external_metadata import CandidateNormalizer, LastFmService, MusicBrainzService, NormalizedCandidate
from app.models import (
    Event,
    RecommendationCandidate,
    RecommendationFeedback,
    RecommendationRun,
    SpotifyArtist,
    SpotifyPlaylist,
    SpotifyTrack,
    User,
    UserFollowedArtist,
    UserPlaylistTrack,
    UserSavedTrack,
    UserTopArtist,
    UserTopTrack,
)


class LastFmLike(Protocol):
    def artist_get_similar(self, artist: str, limit: int = 20) -> list[NormalizedCandidate]: ...
    def track_get_similar(self, artist: str, track: str, limit: int = 20) -> list[NormalizedCandidate]: ...


class MusicBrainzLike(Protocol):
    def fetch_artist_relationships(self, mbid: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class RecommendationResult:
    id: str
    type: str
    name: str
    artist_name: str | None
    confidence: float
    reason_bullets: list[str]
    source_evidence: list[dict[str, Any]]
    seed_explanation: str
    actions: list[str]
    scores: dict[str, float]


class RecommendationPlannerService:
    max_external_seeds = 12
    max_musicbrainz_expansions = 8

    def __init__(
        self,
        lastfm: LastFmLike | None = None,
        musicbrainz: MusicBrainzLike | None = None,
        normalizer: CandidateNormalizer | None = None,
    ) -> None:
        self.lastfm = lastfm or LastFmService()
        self.musicbrainz = musicbrainz or MusicBrainzService()
        self.normalizer = normalizer or CandidateNormalizer()

    def plan(self, db: Session, user: User, prompt: str, *, allow_rediscovery: bool = False) -> list[NormalizedCandidate]:
        candidates = self._generate_candidates(db, user)
        filtered = candidates if allow_rediscovery else self._filter_existing(db, user, candidates)
        self._store_candidates(db, user, prompt, filtered)
        return filtered

    def run(
        self,
        db: Session,
        user: User,
        prompt: str = "recommend music",
        *,
        allow_rediscovery: bool = False,
        include_concert_boost: bool = True,
        limit: int = 20,
    ) -> tuple[RecommendationRun, list[RecommendationCandidate]]:
        candidates = self._generate_candidates(db, user)
        if not allow_rediscovery:
            candidates = self._filter_existing(db, user, candidates)
        candidates = self._filter_hidden(db, user, candidates)
        scored = [
            (candidate, self._score_candidate(db, user, candidate, include_concert_boost=include_concert_boost))
            for candidate in candidates
        ]
        scored.sort(key=lambda item: (-item[1]["final_score"], _candidate_key(item[0])))
        run = self._store_scored_candidates(db, user, prompt, scored[:limit])
        db.commit()
        stored = db.scalars(
            select(RecommendationCandidate)
            .where(RecommendationCandidate.run_id == run.id)
            .order_by(desc(RecommendationCandidate.score), RecommendationCandidate.candidate_key)
        ).all()
        return run, stored

    def latest(self, db: Session, user: User) -> tuple[RecommendationRun | None, list[RecommendationCandidate]]:
        run = db.scalar(
            select(RecommendationRun)
            .where(RecommendationRun.user_id == user.id)
            .order_by(desc(RecommendationRun.created_at))
            .limit(1)
        )
        if run is None:
            return None, []
        candidates = db.scalars(
            select(RecommendationCandidate)
            .where(RecommendationCandidate.run_id == run.id)
            .order_by(desc(RecommendationCandidate.score), RecommendationCandidate.candidate_key)
        ).all()
        return run, candidates

    def record_feedback(
        self,
        db: Session,
        user: User,
        candidate_id: uuid.UUID,
        action: str,
        notes: str | None = None,
    ) -> RecommendationFeedback:
        if action not in {"liked", "hidden", "saved", "added_to_playlist"}:
            raise ValueError("Unsupported recommendation feedback action.")
        candidate = db.get(RecommendationCandidate, candidate_id)
        if candidate is None or not candidate.candidate_key:
            raise ValueError("Recommendation candidate not found.")
        run = db.get(RecommendationRun, candidate.run_id)
        if run is None or run.user_id != user.id:
            raise ValueError("Recommendation candidate not found.")
        feedback = db.scalar(
            select(RecommendationFeedback).where(
                RecommendationFeedback.user_id == user.id,
                RecommendationFeedback.candidate_key == candidate.candidate_key,
            )
        )
        if feedback is None:
            feedback = RecommendationFeedback(user_id=user.id, candidate_key=candidate.candidate_key)
            db.add(feedback)
        feedback.candidate_id = candidate.id
        feedback.action = action
        feedback.notes = notes
        db.commit()
        db.refresh(feedback)
        return feedback

    def _generate_candidates(self, db: Session, user: User) -> list[NormalizedCandidate]:
        seeds = self._seed_items(db, user)
        candidates: list[NormalizedCandidate] = []
        for seed in seeds[: self.max_external_seeds]:
            if seed["kind"] == "artist":
                candidates.extend(self.lastfm.artist_get_similar(seed["name"], limit=10))
            elif seed["kind"] == "track" and seed.get("artist"):
                candidates.extend(self.lastfm.track_get_similar(seed["artist"], seed["name"], limit=10))

        if not candidates:
            candidates.extend(self._profile_fallback_candidates(seeds))

        expanded = [*candidates]
        for candidate in candidates[: self.max_musicbrainz_expansions]:
            if candidate.kind == "artist" and candidate.mbid:
                try:
                    relationships = self.musicbrainz.fetch_artist_relationships(candidate.mbid)
                except Exception:
                    continue
                for collaborator in relationships.get("collaborations", []):
                    expanded.append(
                        NormalizedCandidate(
                            kind="artist",
                            name=collaborator["name"],
                            mbid=collaborator.get("mbid"),
                            confidence=max(candidate.confidence * 0.75, 0.3),
                            source="musicbrainz",
                            reason=f"MusicBrainz collaboration related to {candidate.name}",
                            seed_references=[{"kind": "artist", "name": candidate.name}],
                        )
                    )
        return self.normalizer.merge_duplicates(expanded)

    @staticmethod
    def _profile_fallback_candidates(seeds: list[dict[str, str]]) -> list[NormalizedCandidate]:
        candidates: list[NormalizedCandidate] = []
        seen: set[str] = set()
        for index, seed in enumerate(seeds):
            if seed["kind"] != "artist":
                continue
            name = seed["name"]
            key = name.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append(
                NormalizedCandidate(
                    kind="artist",
                    name=name,
                    confidence=max(0.35, 0.68 - index * 0.01),
                    source="spotify_profile",
                    reason="Profile-based fallback because Last.fm is not configured",
                    seed_references=[seed],
                )
            )
            if len(candidates) >= 40:
                break
        return candidates

    def _seed_items(self, db: Session, user: User) -> list[dict[str, str]]:
        seeds: list[dict[str, str]] = []
        saved_tracks = db.execute(
            select(SpotifyTrack)
            .join(UserSavedTrack, UserSavedTrack.track_id == SpotifyTrack.id)
            .where(UserSavedTrack.user_id == user.id)
        ).scalars()
        for track in saved_tracks:
            seeds.append({"kind": "track", "name": track.name, "artist": ""})

        followed_artists = db.execute(
            select(SpotifyArtist)
            .join(UserFollowedArtist, UserFollowedArtist.artist_id == SpotifyArtist.id)
            .where(UserFollowedArtist.user_id == user.id)
        ).scalars()
        for artist in followed_artists:
            seeds.append({"kind": "artist", "name": artist.name, "source": "followed_artist"})

        top_artists = db.execute(
            select(SpotifyArtist)
            .join(UserTopArtist, UserTopArtist.artist_id == SpotifyArtist.id)
            .where(UserTopArtist.user_id == user.id)
            .order_by(UserTopArtist.rank)
        ).scalars()
        for artist in top_artists:
            seeds.append({"kind": "artist", "name": artist.name, "source": "top_artist"})

        top_tracks = db.execute(
            select(SpotifyTrack)
            .join(UserTopTrack, UserTopTrack.track_id == SpotifyTrack.id)
            .where(UserTopTrack.user_id == user.id)
            .order_by(UserTopTrack.rank)
        ).scalars()
        for track in top_tracks:
            seeds.append({"kind": "track", "name": track.name, "artist": "", "source": "top_track"})

        liked_playlist_tracks = db.execute(
            select(SpotifyTrack)
            .join(UserPlaylistTrack, UserPlaylistTrack.track_id == SpotifyTrack.id)
            .join(SpotifyPlaylist, SpotifyPlaylist.id == UserPlaylistTrack.playlist_id)
            .where(
                UserPlaylistTrack.user_id == user.id,
                SpotifyPlaylist.name == settings.spotify_liked_songs_playlist_name,
            )
            .order_by(UserPlaylistTrack.position)
        ).scalars()
        for track in liked_playlist_tracks:
            seeds.append({"kind": "track", "name": track.name, "artist": "", "source": "playlist"})

        return seeds

    def _filter_existing(
        self, db: Session, user: User, candidates: list[NormalizedCandidate]
    ) -> list[NormalizedCandidate]:
        existing_track_names = self._known_liked_track_names(db, user)
        liked_candidate_keys = set(
            db.scalars(
                select(RecommendationFeedback.candidate_key).where(
                    RecommendationFeedback.user_id == user.id,
                    RecommendationFeedback.action.in_(["liked", "saved", "added_to_playlist"]),
                )
            )
        )
        return [
            candidate
            for candidate in candidates
            if not (
                candidate.kind == "track"
                and (candidate.name.lower() in existing_track_names or _candidate_key(candidate) in liked_candidate_keys)
            )
        ]

    def _filter_hidden(self, db: Session, user: User, candidates: list[NormalizedCandidate]) -> list[NormalizedCandidate]:
        hidden = set(
            db.scalars(
                select(RecommendationFeedback.candidate_key).where(
                    RecommendationFeedback.user_id == user.id,
                    RecommendationFeedback.action == "hidden",
                )
            )
        )
        return [candidate for candidate in candidates if _candidate_key(candidate) not in hidden]

    def _score_candidate(
        self,
        db: Session,
        user: User,
        candidate: NormalizedCandidate,
        *,
        include_concert_boost: bool,
    ) -> dict[str, float]:
        seed_similarity_score = _clamp(candidate.confidence)
        followed_artist_affinity = self._followed_affinity(db, user, candidate)
        playlist_affinity = self._playlist_affinity(candidate)
        novelty_score = 0.62 if candidate.kind == "artist" else 0.74
        graph_distance_score = 0.72 if "musicbrainz" in candidate.source or "neo4j" in candidate.source else 0.48
        evidence_confidence_score = _clamp(candidate.confidence)
        diversity_penalty = self._diversity_penalty(candidate)
        recent_release_or_concert_boost = (
            self._concert_boost(db, candidate) if include_concert_boost else 0.0
        )
        user_feedback_adjustment = self._feedback_adjustment(db, user, candidate)
        final_score = (
            seed_similarity_score * 0.28
            + followed_artist_affinity * 0.14
            + playlist_affinity * 0.12
            + novelty_score * 0.12
            + graph_distance_score * 0.12
            + evidence_confidence_score * 0.14
            + recent_release_or_concert_boost * 0.08
            + user_feedback_adjustment
            - diversity_penalty
        )
        return {
            "seed_similarity_score": round(seed_similarity_score, 4),
            "followed_artist_affinity": round(followed_artist_affinity, 4),
            "playlist_affinity": round(playlist_affinity, 4),
            "novelty_score": round(novelty_score, 4),
            "graph_distance_score": round(graph_distance_score, 4),
            "evidence_confidence_score": round(evidence_confidence_score, 4),
            "diversity_penalty": round(diversity_penalty, 4),
            "recent_release_or_concert_boost": round(recent_release_or_concert_boost, 4),
            "user_feedback_adjustment": round(user_feedback_adjustment, 4),
            "final_score": round(_clamp(final_score), 4),
        }

    def _store_candidates(self, db: Session, user: User, prompt: str, candidates: list[NormalizedCandidate]) -> None:
        scored = [(candidate, self._score_candidate(db, user, candidate, include_concert_boost=False)) for candidate in candidates]
        self._store_scored_candidates(db, user, prompt, scored)
        db.commit()

    def _store_scored_candidates(
        self,
        db: Session,
        user: User,
        prompt: str,
        scored: list[tuple[NormalizedCandidate, dict[str, float]]],
    ) -> RecommendationRun:
        run = RecommendationRun(user_id=user.id, prompt=prompt, status="done")
        db.add(run)
        db.flush()
        for candidate, scores in scored:
            track_id = None
            artist_id = None
            if candidate.kind == "artist":
                artist = self._upsert_external_artist(db, candidate)
                artist_id = artist.id
            elif candidate.kind == "track":
                track = self._upsert_external_track(db, candidate)
                track_id = track.id
            reasons = _reason_bullets(candidate, scores)
            db.add(
                RecommendationCandidate(
                    run_id=run.id,
                    track_id=track_id,
                    artist_id=artist_id,
                    candidate_key=_candidate_key(candidate),
                    candidate_type=candidate.kind,
                    score=scores["final_score"],
                    reason="\n".join(reasons),
                    evidence={
                        "name": candidate.name,
                        "artist_name": candidate.artist_name,
                        "source": candidate.source,
                        "confidence": candidate.confidence,
                        "seed_references": candidate.seed_references,
                        "seed_explanation": _seed_explanation(candidate),
                        "reason_bullets": reasons,
                        "source_evidence": _source_evidence(candidate),
                        "scores": scores,
                        "actions": ["save", "hide", "research", "add_to_playlist"],
                    },
                )
            )
        return run

    def _upsert_external_artist(self, db: Session, candidate: NormalizedCandidate) -> SpotifyArtist:
        spotify_id = f"external:{candidate.mbid or uuid.uuid5(uuid.NAMESPACE_URL, candidate.name)}"
        artist = db.scalar(select(SpotifyArtist).where(SpotifyArtist.spotify_id == spotify_id))
        if artist is None:
            artist = SpotifyArtist(spotify_id=spotify_id, name=candidate.name, genres={})
            db.add(artist)
        artist.name = candidate.name
        artist.external_url = candidate.url
        db.flush()
        return artist

    def _upsert_external_track(self, db: Session, candidate: NormalizedCandidate) -> SpotifyTrack:
        basis = f"{candidate.artist_name or ''}:{candidate.name}:{candidate.mbid or ''}"
        spotify_id = f"external:{candidate.mbid or uuid.uuid5(uuid.NAMESPACE_URL, basis)}"
        track = db.scalar(select(SpotifyTrack).where(SpotifyTrack.spotify_id == spotify_id))
        if track is None:
            track = SpotifyTrack(spotify_id=spotify_id, name=candidate.name)
            db.add(track)
        track.name = candidate.name
        track.external_url = candidate.url
        db.flush()
        return track

    def _known_liked_track_names(self, db: Session, user: User) -> set[str]:
        saved_track_names = {
            name.lower()
            for name in db.execute(
                select(SpotifyTrack.name)
                .join(UserSavedTrack, UserSavedTrack.track_id == SpotifyTrack.id)
                .where(UserSavedTrack.user_id == user.id)
            ).scalars()
        }
        liked_track_names = {
            name.lower()
            for name in db.execute(
                select(SpotifyTrack.name)
                .join(UserPlaylistTrack, UserPlaylistTrack.track_id == SpotifyTrack.id)
                .join(SpotifyPlaylist, SpotifyPlaylist.id == UserPlaylistTrack.playlist_id)
                .where(
                    UserPlaylistTrack.user_id == user.id,
                    SpotifyPlaylist.name == settings.spotify_liked_songs_playlist_name,
                )
            ).scalars()
        }
        return saved_track_names | liked_track_names

    def _followed_affinity(self, db: Session, user: User, candidate: NormalizedCandidate) -> float:
        followed = {
            name.lower()
            for name in db.scalars(
                select(SpotifyArtist.name)
                .join(UserFollowedArtist, UserFollowedArtist.artist_id == SpotifyArtist.id)
                .where(UserFollowedArtist.user_id == user.id)
            )
        }
        seeds = {ref.get("name", "").lower() for ref in candidate.seed_references}
        if candidate.name.lower() in followed or (candidate.artist_name or "").lower() in followed:
            return 0.95
        return 0.75 if seeds & followed else 0.35

    @staticmethod
    def _playlist_affinity(candidate: NormalizedCandidate) -> float:
        if any(ref.get("source") == "playlist" for ref in candidate.seed_references):
            return 0.9
        return 0.55 if candidate.seed_references else 0.2

    @staticmethod
    def _diversity_penalty(candidate: NormalizedCandidate) -> float:
        seed_names = [ref.get("name", "").lower() for ref in candidate.seed_references]
        return 0.08 if candidate.name.lower() in seed_names else 0.0

    def _concert_boost(self, db: Session, candidate: NormalizedCandidate) -> float:
        cutoff = datetime.now(UTC) + timedelta(days=180)
        names = {candidate.name.lower()}
        if candidate.artist_name:
            names.add(candidate.artist_name.lower())
        events = db.scalars(select(Event).where(Event.is_current.is_(True), Event.starts_at <= cutoff)).all()
        for event in events:
            lineup = {str(item).lower() for item in (event.lineup or {}).get("items", [])}
            if names & lineup:
                return 0.8
        return 0.0

    def _feedback_adjustment(self, db: Session, user: User, candidate: NormalizedCandidate) -> float:
        feedback = db.scalar(
            select(RecommendationFeedback).where(
                RecommendationFeedback.user_id == user.id,
                RecommendationFeedback.candidate_key == _candidate_key(candidate),
            )
        )
        if feedback is None:
            return 0.0
        return {
            "liked": 0.1,
            "saved": 0.12,
            "added_to_playlist": 0.14,
            "hidden": -1.0,
        }.get(feedback.action, 0.0)


def recommendation_payload(candidate: RecommendationCandidate) -> dict[str, Any]:
    evidence = candidate.evidence or {}
    return {
        "id": str(candidate.id),
        "type": candidate.candidate_type or ("track" if candidate.track_id else "artist"),
        "track_id": str(candidate.track_id) if candidate.track_id else None,
        "artist_id": str(candidate.artist_id) if candidate.artist_id else None,
        "name": evidence.get("name"),
        "artist_name": evidence.get("artist_name"),
        "score": candidate.score,
        "confidence": evidence.get("scores", {}).get("final_score", candidate.score),
        "reason_bullets": evidence.get("reason_bullets") or ([candidate.reason] if candidate.reason else []),
        "source_evidence": evidence.get("source_evidence", []),
        "seed_explanation": evidence.get("seed_explanation", ""),
        "scores": evidence.get("scores", {}),
        "actions": evidence.get("actions", ["save", "hide", "research", "add_to_playlist"]),
    }


def _candidate_key(candidate: NormalizedCandidate) -> str:
    if candidate.mbid:
        return f"{candidate.kind}:mbid:{candidate.mbid.lower()}"
    artist = (candidate.artist_name or "").strip().lower()
    return f"{candidate.kind}:{artist}:{candidate.name.strip().lower()}"


def _reason_bullets(candidate: NormalizedCandidate, scores: dict[str, float]) -> list[str]:
    reasons = []
    if candidate.reason:
        reasons.append(candidate.reason)
    if candidate.seed_references:
        reasons.append(_seed_explanation(candidate))
    if scores["graph_distance_score"] >= 0.7:
        reasons.append("Graph and metadata relationships support this connection.")
    if scores["recent_release_or_concert_boost"] > 0:
        reasons.append("An upcoming concert increases its current relevance.")
    if not reasons:
        reasons.append("Scored from available music-profile evidence.")
    return reasons


def _seed_explanation(candidate: NormalizedCandidate) -> str:
    if not candidate.seed_references:
        return "No direct seed was recorded for this recommendation."
    labels = []
    for ref in candidate.seed_references[:3]:
        name = ref.get("name") or ref.get("artist") or "a seed"
        kind = ref.get("kind", "seed")
        labels.append(f"{kind} {name}")
    return f"Connected to {', '.join(labels)}."


def _source_evidence(candidate: NormalizedCandidate) -> list[dict[str, Any]]:
    return [
        {
            "source": candidate.source,
            "confidence": candidate.confidence,
            "url": candidate.url,
            "seed_references": candidate.seed_references,
        }
    ]


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))
