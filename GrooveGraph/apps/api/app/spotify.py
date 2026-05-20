import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    OAuthAccount,
    RecommendationCandidate,
    RecommendationRun,
    SpotifyArtist,
    SpotifyPlaylist,
    SpotifyPlaylistAction,
    SpotifyTrack,
    User,
    UserFollowedArtist,
    UserPlaylistTrack,
    UserSavedTrack,
    UserTopArtist,
    UserTopTrack,
)
from app.security import token_cipher

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"
SPOTIFY_SCOPES = [
    "user-library-read",
    "user-follow-read",
    "user-top-read",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-private",
    "playlist-modify-public",
]
TOP_RANGES = ["short_term", "medium_term", "long_term"]
RESTRICTED_ENDPOINT_MARKERS = [
    "/recommendations",
    "/audio-features",
    "/audio-analysis",
    "/related-artists",
]


class SpotifyError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class RestrictedSpotifyEndpointError(SpotifyError):
    pass


@dataclass
class SpotifyTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scope: str


class SpotifyClient:
    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.http = http_client or httpx.Client(timeout=20)
        self.sleep = sleep

    @staticmethod
    def authorize_url(state: str) -> str:
        params = {
            "client_id": settings.spotify_client_id,
            "response_type": "code",
            "redirect_uri": settings.spotify_redirect_uri,
            "scope": " ".join(SPOTIFY_SCOPES),
            "state": state,
        }
        return f"{SPOTIFY_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> SpotifyTokens:
        response = self.http.post(
            SPOTIFY_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.spotify_redirect_uri,
            },
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
        )
        payload = self._json_or_error(response)
        return self._tokens_from_payload(payload)

    def refresh(self, refresh_token: str) -> SpotifyTokens:
        response = self.http.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(settings.spotify_client_id, settings.spotify_client_secret),
        )
        payload = self._json_or_error(response)
        return self._tokens_from_payload(payload, fallback_refresh_token=refresh_token)

    def get(self, account: OAuthAccount, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request(account, "GET", path, params=params)

    def post(self, account: OAuthAccount, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request(account, "POST", path, json=payload or {})

    def put(self, account: OAuthAccount, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request(account, "PUT", path, json=payload or {})

    def request(
        self,
        account: OAuthAccount,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_allowed(path)
        if self._is_expired(account):
            self.refresh_account(account)

        response = self._send(account, method, path, params=params, json=json)
        if response.status_code == 401:
            self.refresh_account(account)
            response = self._send(account, method, path, params=params, json=json)

        if response.status_code == 429:
            retry_after = float(response.headers.get("Retry-After", "1"))
            self.sleep(retry_after)
            response = self._send(account, method, path, params=params, json=json)

        return self._json_or_error(response)

    def paginate(
        self,
        account: OAuthAccount,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        item_container: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        next_url: str | None = path
        request_params = dict(params or {})

        while next_url:
            if next_url.startswith("https://"):
                payload = self.request_url(account, next_url)
            else:
                payload = self.get(account, next_url, request_params)
            page = payload.get(item_container, payload) if item_container else payload
            for item in page.get("items", []):
                yield item
            next_url = page.get("next")
            request_params = {}

    def request_url(self, account: OAuthAccount, url: str) -> dict[str, Any]:
        self._ensure_allowed(url)
        if self._is_expired(account):
            self.refresh_account(account)
        response = self.http.get(url, headers=self._headers(account))
        if response.status_code == 429:
            self.sleep(float(response.headers.get("Retry-After", "1")))
            response = self.http.get(url, headers=self._headers(account))
        return self._json_or_error(response)

    def refresh_account(self, account: OAuthAccount) -> None:
        refresh_token = token_cipher.decrypt(account.encrypted_refresh_token)
        if not refresh_token:
            raise SpotifyError("Spotify refresh token is missing.")
        tokens = self.refresh(refresh_token)
        account.encrypted_access_token = token_cipher.encrypt(tokens.access_token)
        account.encrypted_refresh_token = token_cipher.encrypt(tokens.refresh_token or refresh_token)
        account.scopes = tokens.scope
        account.expires_at = tokens.expires_at

    def _send(
        self,
        account: OAuthAccount,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        json: dict[str, Any] | None,
    ) -> httpx.Response:
        url = path if path.startswith("https://") else f"{SPOTIFY_API_URL}{path}"
        return self.http.request(method, url, headers=self._headers(account), params=params, json=json)

    def _headers(self, account: OAuthAccount) -> dict[str, str]:
        access_token = token_cipher.decrypt(account.encrypted_access_token)
        if not access_token:
            raise SpotifyError("Spotify access token is missing.")
        return {"Authorization": f"Bearer {access_token}"}

    @staticmethod
    def _ensure_allowed(path: str) -> None:
        if any(marker in path for marker in RESTRICTED_ENDPOINT_MARKERS):
            raise RestrictedSpotifyEndpointError(f"Spotify endpoint is not allowed: {path}")

    @staticmethod
    def _is_expired(account: OAuthAccount) -> bool:
        if account.expires_at is None:
            return True
        expires_at = account.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= datetime.now(UTC) + timedelta(seconds=30)

    @staticmethod
    def _tokens_from_payload(payload: dict[str, Any], fallback_refresh_token: str | None = None) -> SpotifyTokens:
        expires_in = int(payload.get("expires_in", 3600))
        return SpotifyTokens(
            access_token=payload["access_token"],
            refresh_token=payload.get("refresh_token", fallback_refresh_token),
            expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
            scope=payload.get("scope", ""),
        )

    @staticmethod
    def _json_or_error(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if response.status_code >= 400:
            raise SpotifyError("Spotify API request failed.", status_code=response.status_code, payload=payload)
        return payload


def get_spotify_account(db: Session, user_id: Any) -> OAuthAccount | None:
    return db.scalar(
        select(OAuthAccount).where(OAuthAccount.user_id == user_id, OAuthAccount.provider == "spotify")
    )


def create_spotify_playlist_from_recommendations(
    db: Session,
    user: User,
    client: SpotifyClient,
    *,
    name: str,
    candidate_ids: list[Any],
) -> dict[str, Any]:
    return create_discovery_playlist_from_track_ids(db, user, client, name=name, track_ids=candidate_ids)


def create_discovery_playlist_from_recommendations(
    db: Session,
    user: User,
    client: SpotifyClient,
    *,
    name: str,
    run_id: Any | None = None,
    candidate_ids: list[Any] | None = None,
) -> dict[str, Any]:
    candidates = _recommendation_candidates_for_playlist(db, user, run_id=run_id, candidate_ids=candidate_ids)
    return _create_playlist_and_add(
        db,
        user,
        client,
        name=name,
        tracks=[candidate.track for candidate in candidates if getattr(candidate, "track", None)],
        source_snapshot={
            "kind": "recommendations",
            "run_id": str(run_id) if run_id else None,
            "candidates": [_candidate_snapshot(candidate) for candidate in candidates],
        },
    )


def create_discovery_playlist_from_track_ids(
    db: Session,
    user: User,
    client: SpotifyClient,
    *,
    name: str,
    track_ids: list[Any],
) -> dict[str, Any]:
    tracks = db.scalars(select(SpotifyTrack).where(SpotifyTrack.id.in_(track_ids))).all() if track_ids else []
    return _create_playlist_and_add(
        db,
        user,
        client,
        name=name,
        tracks=tracks,
        source_snapshot={"kind": "track_ids", "track_ids": [str(track_id) for track_id in track_ids]},
    )


def add_tracks_to_spotify_playlist(
    db: Session,
    user: User,
    client: SpotifyClient,
    *,
    playlist_id: str,
    track_ids: list[Any],
    source_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    account = _spotify_account_or_error(db, user)
    tracks = db.scalars(select(SpotifyTrack).where(SpotifyTrack.id.in_(track_ids))).all() if track_ids else []
    uris, skipped = _spotify_uris_for_tracks(tracks)
    existing = _playlist_track_uris(account, client, playlist_id)
    deduped = [uri for uri in dict.fromkeys(uris) if uri not in existing]
    duplicate_count = len(uris) - len(deduped)
    action = _record_playlist_action(
        db,
        user,
        action="add_tracks",
        spotify_playlist_id=playlist_id,
        request_metadata={"track_ids": [str(track_id) for track_id in track_ids], "uris": uris},
        source_snapshot=source_snapshot or {"kind": "manual_add"},
        status="pending",
    )
    try:
        if deduped:
            client.post(account, f"/playlists/{playlist_id}/tracks", {"uris": deduped})
        action.status = "done"
        action.result_metadata = {
            "added_tracks": len(deduped),
            "duplicate_tracks": duplicate_count,
            "skipped_tracks": len(skipped),
            "skipped": skipped,
        }
        db.commit()
    except SpotifyError as exc:
        _mark_playlist_action_failed(db, action, exc)
        raise
    return {"playlist_id": playlist_id, **action.result_metadata}


def save_spotify_track(
    db: Session,
    user: User,
    client: SpotifyClient,
    *,
    track_id: Any,
) -> dict[str, Any]:
    account = _spotify_account_or_error(db, user)
    track = db.get(SpotifyTrack, track_id)
    if track is None:
        raise SpotifyError("Track not found.", status_code=404)
    uri = spotify_track_uri(track)
    if not uri:
        return {"status": "skipped", "reason": "Track does not have a Spotify URI."}
    try:
        client.put(account, "/me/tracks", {"ids": [track.spotify_id]})
    except SpotifyError:
        raise
    if not db.scalar(select(UserSavedTrack).where(UserSavedTrack.user_id == user.id, UserSavedTrack.track_id == track.id)):
        db.add(UserSavedTrack(user_id=user.id, track_id=track.id, saved_at=datetime.now(UTC)))
        db.commit()
    return {"status": "saved", "track_id": str(track.id), "spotify_uri": uri}


def spotify_playlist_items(
    db: Session,
    user: User,
    client: SpotifyClient,
    *,
    playlist_id: str,
) -> dict[str, Any]:
    account = _spotify_account_or_error(db, user)
    items = []
    for item in client.paginate(account, f"/playlists/{playlist_id}/tracks", params={"limit": 100}):
        track = item.get("track") or {}
        items.append(
            {
                "spotify_id": track.get("id"),
                "uri": track.get("uri"),
                "name": track.get("name"),
                "artist_names": [artist.get("name") for artist in track.get("artists", []) if artist.get("name")],
                "external_url": (track.get("external_urls") or {}).get("spotify"),
            }
        )
    return {"playlist_id": playlist_id, "items": items}


def spotify_track_uri(track: SpotifyTrack) -> str | None:
    if track.spotify_id.startswith("external:"):
        return None
    if track.spotify_id.startswith("spotify:track:"):
        return track.spotify_id
    return f"spotify:track:{track.spotify_id}"


def _create_playlist_and_add(
    db: Session,
    user: User,
    client: SpotifyClient,
    *,
    name: str,
    tracks: list[SpotifyTrack],
    source_snapshot: dict[str, Any],
) -> dict[str, Any]:
    account = _spotify_account_or_error(db, user)
    action = _record_playlist_action(
        db,
        user,
        action="create_from_recommendations",
        spotify_playlist_id=None,
        request_metadata={"name": name, "track_ids": [str(track.id) for track in tracks]},
        source_snapshot=source_snapshot,
        status="pending",
    )
    try:
        me = client.get(account, "/me")
        playlist = client.post(
            account,
            f"/users/{me['id']}/playlists",
            {
                "name": name,
                "description": "Created by GrooveGraph from explainable recommendations.",
                "public": False,
            },
        )
        stored_playlist = upsert_spotify_playlist(db, playlist)
        db.flush()
        action.playlist_id = stored_playlist.id
        action.spotify_playlist_id = playlist["id"]
        add_result = add_tracks_to_spotify_playlist(
            db,
            user,
            client,
            playlist_id=playlist["id"],
            track_ids=[track.id for track in tracks],
            source_snapshot=source_snapshot,
        )
        action.status = "done"
        action.result_metadata = {
            "playlist_id": playlist["id"],
            "external_url": (playlist.get("external_urls") or {}).get("spotify"),
            **add_result,
        }
        db.commit()
    except SpotifyError as exc:
        _mark_playlist_action_failed(db, action, exc)
        raise
    return action.result_metadata


def _recommendation_candidates_for_playlist(
    db: Session,
    user: User,
    *,
    run_id: Any | None,
    candidate_ids: list[Any] | None,
) -> list[RecommendationCandidate]:
    query = select(RecommendationCandidate, SpotifyTrack).join(RecommendationRun, RecommendationRun.id == RecommendationCandidate.run_id).join(
        SpotifyTrack, SpotifyTrack.id == RecommendationCandidate.track_id
    ).where(RecommendationRun.user_id == user.id, RecommendationCandidate.track_id.is_not(None))
    if run_id:
        query = query.where(RecommendationCandidate.run_id == run_id)
    else:
        latest_run = db.scalar(select(RecommendationRun.id).where(RecommendationRun.user_id == user.id).order_by(RecommendationRun.created_at.desc()).limit(1))
        if latest_run:
            query = query.where(RecommendationCandidate.run_id == latest_run)
    if candidate_ids:
        query = query.where(RecommendationCandidate.id.in_(candidate_ids))
    rows = db.execute(query.order_by(RecommendationCandidate.score.desc())).all()
    candidates = []
    for candidate, track in rows:
        candidate.track = track  # type: ignore[attr-defined]
        candidates.append(candidate)
    return candidates


def _spotify_uris_for_tracks(tracks: list[SpotifyTrack]) -> tuple[list[str], list[dict[str, str]]]:
    uris: list[str] = []
    skipped: list[dict[str, str]] = []
    for track in tracks:
        uri = spotify_track_uri(track)
        if uri:
            uris.append(uri)
        else:
            skipped.append({"track_id": str(track.id), "name": track.name, "reason": "missing_spotify_uri"})
    return uris, skipped


def _playlist_track_uris(account: OAuthAccount, client: SpotifyClient, playlist_id: str) -> set[str]:
    uris: set[str] = set()
    for item in client.paginate(account, f"/playlists/{playlist_id}/tracks", params={"limit": 100}):
        uri = (item.get("track") or {}).get("uri")
        if uri:
            uris.add(uri)
    return uris


def _spotify_account_or_error(db: Session, user: User) -> OAuthAccount:
    account = get_spotify_account(db, user.id)
    if account is None:
        raise SpotifyError("Spotify account is not connected.", status_code=401)
    return account


def _record_playlist_action(
    db: Session,
    user: User,
    *,
    action: str,
    spotify_playlist_id: str | None,
    request_metadata: dict[str, Any],
    source_snapshot: dict[str, Any],
    status: str,
) -> SpotifyPlaylistAction:
    row = SpotifyPlaylistAction(
        user_id=user.id,
        spotify_playlist_id=spotify_playlist_id,
        action=action,
        status=status,
        request_metadata=request_metadata,
        result_metadata={},
        source_snapshot=source_snapshot,
    )
    db.add(row)
    db.flush()
    return row


def _mark_playlist_action_failed(db: Session, action: SpotifyPlaylistAction, exc: SpotifyError) -> None:
    action.status = "failed"
    action.error_message = str(exc)
    action.result_metadata = {"status_code": exc.status_code, "payload": exc.payload}
    db.commit()


def _candidate_snapshot(candidate: RecommendationCandidate) -> dict[str, Any]:
    return {
        "id": str(candidate.id),
        "score": candidate.score,
        "reason": candidate.reason,
        "evidence": candidate.evidence,
        "track_id": str(candidate.track_id) if candidate.track_id else None,
    }


def upsert_spotify_track(db: Session, payload: dict[str, Any]) -> SpotifyTrack:
    track = db.scalar(select(SpotifyTrack).where(SpotifyTrack.spotify_id == payload["id"]))
    if track is None:
        track = SpotifyTrack(spotify_id=payload["id"], name=payload.get("name", "Unknown track"))
        db.add(track)
    track.name = payload.get("name", track.name)
    track.album_name = (payload.get("album") or {}).get("name")
    track.duration_ms = payload.get("duration_ms")
    track.preview_url = payload.get("preview_url")
    track.external_url = (payload.get("external_urls") or {}).get("spotify")
    return track


def upsert_spotify_artist(db: Session, payload: dict[str, Any]) -> SpotifyArtist:
    artist = db.scalar(select(SpotifyArtist).where(SpotifyArtist.spotify_id == payload["id"]))
    if artist is None:
        artist = SpotifyArtist(spotify_id=payload["id"], name=payload.get("name", "Unknown artist"), genres={})
        db.add(artist)
    artist.name = payload.get("name", artist.name)
    artist.genres = {"items": payload.get("genres", [])}
    artist.external_url = (payload.get("external_urls") or {}).get("spotify")
    return artist


def upsert_spotify_playlist(db: Session, payload: dict[str, Any]) -> SpotifyPlaylist:
    playlist = db.scalar(select(SpotifyPlaylist).where(SpotifyPlaylist.spotify_id == payload["id"]))
    if playlist is None:
        playlist = SpotifyPlaylist(spotify_id=payload["id"], name=payload.get("name", "Untitled playlist"))
        db.add(playlist)
    playlist.name = payload.get("name", playlist.name)
    playlist.description = payload.get("description")
    playlist.owner_spotify_id = (payload.get("owner") or {}).get("id")
    playlist.external_url = (payload.get("external_urls") or {}).get("spotify")
    return playlist


def sync_spotify_library(db: Session, user: User, client: SpotifyClient) -> dict[str, int]:
    account = get_spotify_account(db, user.id)
    if account is None:
        raise SpotifyError("Spotify account is not connected.", status_code=401)

    counts = {
        "saved_tracks": sync_saved_tracks(db, user, account, client),
        "followed_artists": sync_followed_artists(db, user, account, client),
        "playlists": sync_playlists(db, user, account, client),
    }

    for time_range in TOP_RANGES:
        counts[f"top_tracks_{time_range}"] = sync_top_tracks(db, user, account, client, time_range)
        counts[f"top_artists_{time_range}"] = sync_top_artists(db, user, account, client, time_range)

    db.commit()
    return counts


def sync_saved_tracks(db: Session, user: User, account: OAuthAccount, client: SpotifyClient) -> int:
    count = 0
    for item in client.paginate(account, "/me/tracks", params={"limit": 50}):
        track_payload = item.get("track")
        if not track_payload:
            continue
        track = upsert_spotify_track(db, track_payload)
        db.flush()
        if not db.scalar(select(UserSavedTrack).where(UserSavedTrack.user_id == user.id, UserSavedTrack.track_id == track.id)):
            db.add(UserSavedTrack(user_id=user.id, track_id=track.id))
        count += 1
    return count


def sync_followed_artists(db: Session, user: User, account: OAuthAccount, client: SpotifyClient) -> int:
    count = 0
    for artist_payload in client.paginate(
        account, "/me/following", params={"type": "artist", "limit": 50}, item_container="artists"
    ):
        artist = upsert_spotify_artist(db, artist_payload)
        db.flush()
        if not db.scalar(
            select(UserFollowedArtist).where(UserFollowedArtist.user_id == user.id, UserFollowedArtist.artist_id == artist.id)
        ):
            db.add(UserFollowedArtist(user_id=user.id, artist_id=artist.id))
        count += 1
    return count


def sync_playlists(db: Session, user: User, account: OAuthAccount, client: SpotifyClient) -> int:
    count = 0
    liked_playlist_synced = False
    for playlist_payload in client.paginate(account, "/me/playlists", params={"limit": 50}):
        playlist = upsert_spotify_playlist(db, playlist_payload)
        db.flush()
        count += 1
        if _is_liked_playlist(playlist_payload):
            sync_playlist_tracks(db, user, account, client, playlist)
            liked_playlist_synced = True

    if settings.spotify_liked_songs_playlist_id and not liked_playlist_synced:
        try:
            payload = client.get(account, f"/playlists/{settings.spotify_liked_songs_playlist_id}")
        except SpotifyError:
            return count
        playlist = upsert_spotify_playlist(db, payload)
        db.flush()
        sync_playlist_tracks(db, user, account, client, playlist)

    return count


def sync_playlist_tracks(
    db: Session, user: User, account: OAuthAccount, client: SpotifyClient, playlist: SpotifyPlaylist
) -> int:
    db.execute(delete(UserPlaylistTrack).where(UserPlaylistTrack.user_id == user.id, UserPlaylistTrack.playlist_id == playlist.id))
    count = 0
    for position, item in enumerate(client.paginate(account, f"/playlists/{playlist.spotify_id}/tracks", params={"limit": 100})):
        track_payload = item.get("track")
        if not track_payload:
            continue
        track = upsert_spotify_track(db, track_payload)
        db.flush()
        db.add(UserPlaylistTrack(user_id=user.id, playlist_id=playlist.id, track_id=track.id, position=position))
        count += 1
    return count


def sync_top_tracks(db: Session, user: User, account: OAuthAccount, client: SpotifyClient, time_range: str) -> int:
    db.execute(delete(UserTopTrack).where(UserTopTrack.user_id == user.id, UserTopTrack.time_range == time_range))
    count = 0
    for rank, track_payload in enumerate(
        client.paginate(account, "/me/top/tracks", params={"limit": 50, "time_range": time_range}), start=1
    ):
        track = upsert_spotify_track(db, track_payload)
        db.flush()
        db.add(UserTopTrack(user_id=user.id, track_id=track.id, time_range=time_range, rank=rank))
        count += 1
    return count


def sync_top_artists(db: Session, user: User, account: OAuthAccount, client: SpotifyClient, time_range: str) -> int:
    db.execute(delete(UserTopArtist).where(UserTopArtist.user_id == user.id, UserTopArtist.time_range == time_range))
    count = 0
    for rank, artist_payload in enumerate(
        client.paginate(account, "/me/top/artists", params={"limit": 50, "time_range": time_range}), start=1
    ):
        artist = upsert_spotify_artist(db, artist_payload)
        db.flush()
        db.add(UserTopArtist(user_id=user.id, artist_id=artist.id, time_range=time_range, rank=rank))
        count += 1
    return count


def _is_liked_playlist(payload: dict[str, Any]) -> bool:
    if settings.spotify_liked_songs_playlist_id and payload.get("id") == settings.spotify_liked_songs_playlist_id:
        return True
    return payload.get("name") == settings.spotify_liked_songs_playlist_name
