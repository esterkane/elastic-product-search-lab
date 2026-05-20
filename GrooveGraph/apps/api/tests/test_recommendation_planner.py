from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.external_metadata import NormalizedCandidate
from app.models import (
    Base,
    RecommendationCandidate,
    RecommendationFeedback,
    SpotifyArtist,
    SpotifyPlaylist,
    SpotifyTrack,
    User,
    UserFollowedArtist,
    UserPlaylistTrack,
    UserSavedTrack,
)
from app.recommendation_planner import RecommendationPlannerService


class FakeLastFm:
    def artist_get_similar(self, artist: str, limit: int = 20):
        return [
            NormalizedCandidate(
                kind="artist",
                name="Pixies",
                mbid="pixies-mbid",
                confidence=0.9,
                source="lastfm",
                reason=f"similar to {artist}",
                seed_references=[{"kind": "artist", "name": artist}],
            ),
            NormalizedCandidate(
                kind="artist",
                name="Pixies",
                mbid="pixies-mbid",
                confidence=0.7,
                source="lastfm",
                reason="duplicate",
                seed_references=[{"kind": "artist", "name": "duplicate"}],
            ),
            NormalizedCandidate(
                kind="track",
                name="Saved Song",
                artist_name="Known Artist",
                confidence=0.95,
                source="lastfm",
                reason="would be rediscovery",
                seed_references=[{"kind": "artist", "name": artist}],
            ),
            NormalizedCandidate(
                kind="track",
                name="New Song",
                artist_name="New Artist",
                confidence=0.82,
                source="lastfm",
                reason="new candidate",
                seed_references=[{"kind": "artist", "name": artist}],
            ),
        ]

    def track_get_similar(self, artist: str, track: str, limit: int = 20):
        return []


class FakeMusicBrainz:
    def fetch_artist_relationships(self, mbid: str):
        return {
            "collaborations": [
                {"name": "Throwing Muses", "mbid": "throwing-muses-mbid"},
            ]
        }


def build_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_planner_merges_candidates_filters_existing_tracks_and_stores_provenance() -> None:
    db = build_session()
    user = User(email="listener@example.com")
    artist = SpotifyArtist(spotify_id="spotify:artist:radiohead", name="Radiohead", genres={})
    saved_track = SpotifyTrack(spotify_id="spotify:track:saved", name="Saved Song")
    liked_track = SpotifyTrack(spotify_id="spotify:track:liked", name="Liked Song")
    playlist = SpotifyPlaylist(spotify_id="spotify:playlist:liked", name="Lieblingssongs")
    db.add_all([user, artist, saved_track, liked_track, playlist])
    db.flush()
    db.add_all(
        [
            UserFollowedArtist(user_id=user.id, artist_id=artist.id),
            UserSavedTrack(user_id=user.id, track_id=saved_track.id),
            UserPlaylistTrack(user_id=user.id, playlist_id=playlist.id, track_id=liked_track.id, position=1),
        ]
    )
    db.commit()

    planner = RecommendationPlannerService(lastfm=FakeLastFm(), musicbrainz=FakeMusicBrainz())
    candidates = planner.plan(db, user, "recommend music")

    names = {candidate.name for candidate in candidates}
    assert names == {"Pixies", "New Song", "Throwing Muses"}
    pixies = next(candidate for candidate in candidates if candidate.name == "Pixies")
    assert pixies.confidence == 0.9
    assert len(pixies.seed_references) == 2

    stored = db.scalars(select(RecommendationCandidate)).all()
    assert len(stored) == 3
    for candidate in stored:
        assert candidate.evidence["source"]
        assert candidate.evidence["confidence"] > 0
        assert candidate.evidence["seed_references"]
        assert candidate.reason


def seed_user_profile(db):
    user = User(email="listener@example.com")
    artist = SpotifyArtist(spotify_id="spotify:artist:radiohead", name="Radiohead", genres={})
    saved_track = SpotifyTrack(spotify_id="spotify:track:saved", name="Saved Song")
    playlist_track = SpotifyTrack(spotify_id="spotify:track:liked", name="Liked Song")
    playlist = SpotifyPlaylist(spotify_id="spotify:playlist:liked", name="Lieblingssongs")
    db.add_all([user, artist, saved_track, playlist_track, playlist])
    db.flush()
    db.add_all(
        [
            UserFollowedArtist(user_id=user.id, artist_id=artist.id),
            UserSavedTrack(user_id=user.id, track_id=saved_track.id),
            UserPlaylistTrack(user_id=user.id, playlist_id=playlist.id, track_id=playlist_track.id, position=1),
        ]
    )
    db.commit()
    return user


def test_recommendations_are_explainable_and_have_reasons() -> None:
    db = build_session()
    user = seed_user_profile(db)
    planner = RecommendationPlannerService(lastfm=FakeLastFm(), musicbrainz=FakeMusicBrainz())

    _, recommendations = planner.run(db, user, "recommend music")

    assert recommendations
    for recommendation in recommendations:
        assert recommendation.reason
        assert recommendation.evidence["reason_bullets"]
        assert recommendation.evidence["source_evidence"]
        assert recommendation.evidence["seed_explanation"]
        assert recommendation.evidence["actions"] == ["save", "hide", "research", "add_to_playlist"]
        assert recommendation.evidence["scores"]["final_score"] == recommendation.score


def test_known_liked_tracks_are_filtered() -> None:
    db = build_session()
    user = seed_user_profile(db)
    planner = RecommendationPlannerService(lastfm=FakeLastFm(), musicbrainz=FakeMusicBrainz())

    _, recommendations = planner.run(db, user, "recommend music")

    names = {recommendation.evidence["name"] for recommendation in recommendations}
    assert "Saved Song" not in names


def test_hidden_candidates_stay_hidden() -> None:
    db = build_session()
    user = seed_user_profile(db)
    planner = RecommendationPlannerService(lastfm=FakeLastFm(), musicbrainz=FakeMusicBrainz())
    _, first_recommendations = planner.run(db, user, "recommend music")
    pixies = next(recommendation for recommendation in first_recommendations if recommendation.evidence["name"] == "Pixies")

    planner.record_feedback(db, user, pixies.id, "hidden")
    _, second_recommendations = planner.run(db, user, "recommend music")

    names = {recommendation.evidence["name"] for recommendation in second_recommendations}
    assert "Pixies" not in names
    assert db.scalar(select(RecommendationFeedback).where(RecommendationFeedback.action == "hidden")) is not None


def test_scoring_is_deterministic_for_fixed_inputs() -> None:
    db = build_session()
    user = seed_user_profile(db)
    planner = RecommendationPlannerService(lastfm=FakeLastFm(), musicbrainz=FakeMusicBrainz())

    _, first = planner.run(db, user, "recommend music", include_concert_boost=False)
    _, second = planner.run(db, user, "recommend music", include_concert_boost=False)

    first_projection = [(item.evidence["name"], item.score, item.evidence["scores"]) for item in first]
    second_projection = [(item.evidence["name"], item.score, item.evidence["scores"]) for item in second]
    assert first_projection == second_projection
