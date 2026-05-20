from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.models import (
    Base,
    OAuthAccount,
    RecommendationCandidate,
    RecommendationRun,
    SpotifyPlaylistAction,
    SpotifyTrack,
    User,
)
from app.security import token_cipher
from app.spotify import (
    SpotifyError,
    add_tracks_to_spotify_playlist,
    create_discovery_playlist_from_recommendations,
)


class FakeSpotifyClient:
    def __init__(self, *, existing_uris: set[str] | None = None, fail_on_post: bool = False) -> None:
        self.existing_uris = existing_uris or set()
        self.fail_on_post = fail_on_post
        self.posts: list[tuple[str, dict]] = []

    def get(self, account, path: str, params=None):
        if path == "/me":
            return {"id": "spotify-user"}
        return {}

    def post(self, account, path: str, payload=None):
        if self.fail_on_post:
            raise SpotifyError("Spotify permission denied.", status_code=403, payload={"error": "insufficient_scope"})
        self.posts.append((path, payload or {}))
        if path.endswith("/playlists"):
            return {
                "id": "playlist-new",
                "name": payload["name"],
                "description": payload["description"],
                "owner": {"id": "spotify-user"},
                "external_urls": {"spotify": "https://spotify.example/playlist-new"},
            }
        return {"snapshot_id": "snapshot"}

    def paginate(self, account, path: str, params=None, item_container=None):
        for uri in self.existing_uris:
            yield {"track": {"uri": uri, "id": uri.removeprefix("spotify:track:"), "name": "Existing"}}


def build_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def add_account(db, user: User) -> None:
    db.add(
        OAuthAccount(
            user_id=user.id,
            provider="spotify",
            provider_account_id="spotify-user",
            encrypted_access_token=token_cipher.encrypt("access"),
            encrypted_refresh_token=token_cipher.encrypt("refresh"),
            scopes="playlist-modify-private playlist-modify-public user-library-read",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    db.commit()


def seed_recommendation_run(db):
    user = User(email="listener@example.com")
    spotify_track = SpotifyTrack(spotify_id="spotify-track-1", name="Spotify Song")
    external_track = SpotifyTrack(spotify_id="external:track-2", name="External Song")
    db.add_all([user, spotify_track, external_track])
    db.flush()
    add_account(db, user)
    run = RecommendationRun(user_id=user.id, prompt="recommend", status="done")
    db.add(run)
    db.flush()
    db.add_all(
        [
            RecommendationCandidate(
                run_id=run.id,
                track_id=spotify_track.id,
                candidate_key="track:spotify-song",
                candidate_type="track",
                score=0.9,
                reason="Great fit",
                evidence={"source": "lastfm", "reason_bullets": ["Similar to a seed"]},
            ),
            RecommendationCandidate(
                run_id=run.id,
                track_id=external_track.id,
                candidate_key="track:external-song",
                candidate_type="track",
                score=0.8,
                reason="No URI",
                evidence={"source": "lastfm"},
            ),
        ]
    )
    db.commit()
    return user, run, spotify_track, external_track


def test_create_playlist_from_recommendations_filters_non_spotify_tracks_and_stores_snapshot() -> None:
    db = build_session()
    user, run, _, _ = seed_recommendation_run(db)
    client = FakeSpotifyClient()

    result = create_discovery_playlist_from_recommendations(db, user, client, name="Discovery", run_id=run.id)

    assert result["playlist_id"] == "playlist-new"
    assert result["added_tracks"] == 1
    assert result["skipped_tracks"] == 1
    assert ("users/spotify-user/playlists" in client.posts[0][0]) or (client.posts[0][0] == "/users/spotify-user/playlists")
    assert client.posts[0][1]["description"] == "Created by GrooveGraph from explainable recommendations."
    assert client.posts[1] == ("/playlists/playlist-new/tracks", {"uris": ["spotify:track:spotify-track-1"]})

    actions = db.scalars(select(SpotifyPlaylistAction).order_by(SpotifyPlaylistAction.created_at)).all()
    assert actions[0].source_snapshot["kind"] == "recommendations"
    assert actions[0].source_snapshot["candidates"][0]["reason"] == "Great fit"


def test_add_tracks_filters_duplicates_before_calling_spotify() -> None:
    db = build_session()
    user, _, spotify_track, external_track = seed_recommendation_run(db)
    client = FakeSpotifyClient(existing_uris={"spotify:track:spotify-track-1"})

    result = add_tracks_to_spotify_playlist(
        db,
        user,
        client,
        playlist_id="playlist-existing",
        track_ids=[spotify_track.id, external_track.id],
    )

    assert result["added_tracks"] == 0
    assert result["duplicate_tracks"] == 1
    assert result["skipped_tracks"] == 1
    assert client.posts == []


def test_permission_failure_is_recorded_and_reported() -> None:
    db = build_session()
    user, _, spotify_track, _ = seed_recommendation_run(db)
    client = FakeSpotifyClient(fail_on_post=True)

    with pytest.raises(SpotifyError) as exc:
        add_tracks_to_spotify_playlist(
            db,
            user,
            client,
            playlist_id="playlist-existing",
            track_ids=[spotify_track.id],
        )

    assert exc.value.status_code == 403
    action = db.scalar(select(SpotifyPlaylistAction).where(SpotifyPlaylistAction.status == "failed"))
    assert action is not None
    assert action.error_message == "Spotify permission denied."
