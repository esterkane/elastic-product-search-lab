import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings


@dataclass
class NormalizedCandidate:
    kind: str
    name: str
    artist_name: str | None = None
    mbid: str | None = None
    url: str | None = None
    confidence: float = 0.5
    source: str = "unknown"
    reason: str = ""
    seed_references: list[dict[str, str]] = field(default_factory=list)

    @property
    def dedupe_key(self) -> str:
        if self.mbid:
            return f"{self.kind}:mbid:{self.mbid.lower()}"
        artist = (self.artist_name or "").strip().lower()
        return f"{self.kind}:{artist}:{self.name.strip().lower()}"

    def merge(self, other: "NormalizedCandidate") -> "NormalizedCandidate":
        seed_refs = {tuple(sorted(ref.items())): ref for ref in [*self.seed_references, *other.seed_references]}
        sources = sorted(set(filter(None, [self.source, other.source])))
        reasons = sorted(set(filter(None, [self.reason, other.reason])))
        return NormalizedCandidate(
            kind=self.kind,
            name=self.name,
            artist_name=self.artist_name or other.artist_name,
            mbid=self.mbid or other.mbid,
            url=self.url or other.url,
            confidence=max(self.confidence, other.confidence),
            source="+".join(sources),
            reason="; ".join(reasons),
            seed_references=list(seed_refs.values()),
        )


class CandidateNormalizer:
    def from_lastfm_artist(self, payload: dict[str, Any], *, seed: dict[str, str]) -> NormalizedCandidate:
        score = float(payload.get("match") or 0.5)
        return NormalizedCandidate(
            kind="artist",
            name=payload.get("name", "Unknown artist"),
            mbid=payload.get("mbid") or None,
            url=payload.get("url"),
            confidence=min(max(score, 0.0), 1.0),
            source="lastfm",
            reason=f"Last.fm similarity from {seed.get('name', 'seed')}",
            seed_references=[seed],
        )

    def from_lastfm_track(self, payload: dict[str, Any], *, seed: dict[str, str]) -> NormalizedCandidate:
        score = float(payload.get("match") or 0.5)
        artist_payload = payload.get("artist") or {}
        artist_name = artist_payload.get("name") if isinstance(artist_payload, dict) else str(artist_payload)
        return NormalizedCandidate(
            kind="track",
            name=payload.get("name", "Unknown track"),
            artist_name=artist_name,
            mbid=payload.get("mbid") or None,
            url=payload.get("url"),
            confidence=min(max(score, 0.0), 1.0),
            source="lastfm",
            reason=f"Last.fm track similarity from {seed.get('name', 'seed')}",
            seed_references=[seed],
        )

    def merge_duplicates(self, candidates: list[NormalizedCandidate]) -> list[NormalizedCandidate]:
        merged: dict[str, NormalizedCandidate] = {}
        for candidate in candidates:
            if candidate.dedupe_key in merged:
                merged[candidate.dedupe_key] = merged[candidate.dedupe_key].merge(candidate)
            else:
                merged[candidate.dedupe_key] = candidate
        return sorted(merged.values(), key=lambda item: item.confidence, reverse=True)


class MusicBrainzService:
    base_url = "https://musicbrainz.org/ws/2"

    def __init__(self, http_client: httpx.Client | None = None, sleep=time.sleep) -> None:
        self.http = http_client or httpx.Client(timeout=20)
        self.sleep = sleep

    def search_artist_by_name(self, name: str, limit: int = 5) -> list[dict[str, Any]]:
        payload = self._get("/artist", {"query": name, "fmt": "json", "limit": limit})
        return [self._normalize_artist(item) for item in payload.get("artists", [])]

    def lookup_artist_by_mbid(self, mbid: str) -> dict[str, Any]:
        payload = self._get(f"/artist/{mbid}", {"fmt": "json", "inc": "aliases+url-rels+artist-rels"})
        return self._normalize_artist(payload)

    def fetch_artist_relationships(self, mbid: str) -> dict[str, Any]:
        payload = self._get(f"/artist/{mbid}", {"fmt": "json", "inc": "aliases+url-rels+artist-rels"})
        normalized = self._normalize_artist(payload)
        return {
            "artist": normalized,
            "members": self._relationship_targets(payload, {"member of band", "is person"}),
            "groups": self._relationship_targets(payload, {"member of", "group member"}),
            "collaborations": self._relationship_targets(payload, {"collaboration", "collaborates with"}),
            "urls": normalized["urls"],
            "aliases": normalized["aliases"],
        }

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        response = self.http.get(
            f"{self.base_url}{path}",
            params=params,
            headers={"User-Agent": settings.musicbrainz_user_agent, "Accept": "application/json"},
        )
        if response.status_code == 503 and response.headers.get("Retry-After"):
            self.sleep(float(response.headers["Retry-After"]))
            response = self.http.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"User-Agent": settings.musicbrainz_user_agent, "Accept": "application/json"},
            )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize_artist(payload: dict[str, Any]) -> dict[str, Any]:
        relations = payload.get("relations", [])
        return {
            "mbid": payload.get("id"),
            "name": payload.get("name"),
            "sort_name": payload.get("sort-name"),
            "type": payload.get("type"),
            "aliases": [alias.get("name") for alias in payload.get("aliases", []) if alias.get("name")],
            "urls": [
                relation.get("url", {}).get("resource")
                for relation in relations
                if relation.get("target-type") == "url" and relation.get("url", {}).get("resource")
            ],
        }

    @staticmethod
    def _relationship_targets(payload: dict[str, Any], relation_types: set[str]) -> list[dict[str, Any]]:
        targets = []
        for relation in payload.get("relations", []):
            if relation.get("type") not in relation_types:
                continue
            artist = relation.get("artist") or {}
            if artist:
                targets.append({"mbid": artist.get("id"), "name": artist.get("name"), "type": relation.get("type")})
        return targets


class LastFmService:
    base_url = "https://ws.audioscrobbler.com/2.0/"

    def __init__(self, http_client: httpx.Client | None = None, api_key: str | None = None) -> None:
        self.http = http_client or httpx.Client(timeout=20)
        self.api_key = api_key if api_key is not None else settings.lastfm_api_key
        self.normalizer = CandidateNormalizer()

    def artist_get_similar(self, artist: str, limit: int = 20) -> list[NormalizedCandidate]:
        payload = self._get({"method": "artist.getSimilar", "artist": artist, "limit": limit})
        seed = {"kind": "artist", "name": artist}
        return [self.normalizer.from_lastfm_artist(item, seed=seed) for item in payload.get("similarartists", {}).get("artist", [])]

    def track_get_similar(self, artist: str, track: str, limit: int = 20) -> list[NormalizedCandidate]:
        payload = self._get({"method": "track.getSimilar", "artist": artist, "track": track, "limit": limit})
        seed = {"kind": "track", "name": track, "artist": artist}
        return [self.normalizer.from_lastfm_track(item, seed=seed) for item in payload.get("similartracks", {}).get("track", [])]

    def tag_get_similar(self, tag: str) -> list[NormalizedCandidate]:
        payload = self._get({"method": "tag.getSimilar", "tag": tag})
        seed = {"kind": "tag", "name": tag}
        return [
            NormalizedCandidate(
                kind="artist",
                name=item.get("name", "Unknown tag candidate"),
                confidence=0.35,
                source="lastfm",
                reason=f"Last.fm tag similarity from {tag}",
                seed_references=[seed],
            )
            for item in payload.get("similartags", {}).get("tag", [])
        ]

    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key and isinstance(self.http._transport, httpx.HTTPTransport):
            return {}
        response = self.http.get(
            self.base_url,
            params={**params, "api_key": self.api_key or "test", "format": "json"},
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError:
            return {}
        return response.json()
