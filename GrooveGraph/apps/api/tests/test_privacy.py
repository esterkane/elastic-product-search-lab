from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.deletion import disconnect_spotify_user_data
from app.models import (
    Base,
    OAuthAccount,
    RecommendationCandidate,
    RecommendationRun,
    Session,
    SessionMessage,
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
from app.privacy import privacy_export, redact_tokens
from app.security import token_cipher


def build_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def seed_privacy_user(db):
    user = User(email="listener@example.com", display_name="Listener")
    track = SpotifyTrack(spotify_id="spotify-track-1", name="Track One", album_name="Album One")
    artist = SpotifyArtist(spotify_id="spotify-artist-1", name="Artist One", genres={"items": ["indie"]})
    playlist = SpotifyPlaylist(spotify_id="playlist-1", name="Lieblingssongs")
    db.add_all([user, track, artist, playlist])
    db.flush()
    account = OAuthAccount(
        user_id=user.id,
        provider="spotify",
        provider_account_id="spotify-user",
        encrypted_access_token=token_cipher.encrypt("raw-access-token"),
        encrypted_refresh_token=token_cipher.encrypt("raw-refresh-token"),
        scopes="user-library-read playlist-read-private",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session = Session(user_id=user.id, title="radiohead-session")
    run = RecommendationRun(user_id=user.id, prompt="recommend", status="done")
    db.add_all([account, session, run])
    db.flush()
    db.add_all(
        [
            UserSavedTrack(user_id=user.id, track_id=track.id),
            UserFollowedArtist(user_id=user.id, artist_id=artist.id),
            UserPlaylistTrack(user_id=user.id, playlist_id=playlist.id, track_id=track.id, position=1),
            UserTopTrack(user_id=user.id, track_id=track.id, time_range="short_term", rank=1),
            UserTopArtist(user_id=user.id, artist_id=artist.id, time_range="short_term", rank=1),
            SessionMessage(session_id=session.id, role="user", content="Tell me about Radiohead", message_metadata={}),
            RecommendationCandidate(
                run_id=run.id,
                track_id=track.id,
                candidate_key="track:track-one",
                candidate_type="track",
                score=0.9,
                reason="Because of Artist One",
                evidence={"source": "lastfm"},
            ),
        ]
    )
    db.commit()
    return user


def test_spotify_disconnect_deletes_user_linked_spotify_data() -> None:
    db = build_session()
    user = seed_privacy_user(db)

    counts = disconnect_spotify_user_data(db, user.id)
    db.commit()

    assert counts["oauth_accounts"] == 1
    for model in [OAuthAccount, UserSavedTrack, UserFollowedArtist, UserPlaylistTrack, UserTopTrack, UserTopArtist]:
        assert db.scalar(select(model).limit(1)) is None
    assert db.scalar(select(SpotifyTrack).limit(1)) is not None
    assert db.scalar(select(SpotifyArtist).limit(1)) is not None


def test_tokens_are_redacted_in_logs() -> None:
    text = redact_tokens(
        "Authorization: Bearer raw-access-token access_token=abc refresh_token=def "
        "{'encrypted_access_token': 'secret-a', 'encrypted_refresh_token': 'secret-r'}"
    )

    assert "raw-access-token" not in text
    assert "abc" not in text
    assert "def" not in text
    assert "secret-a" not in text
    assert "secret-r" not in text
    assert "[REDACTED]" in text


def test_privacy_export_omits_tokens_and_includes_user_data() -> None:
    db = build_session()
    user = seed_privacy_user(db)

    exported = privacy_export(db, user)
    serialized = str(exported)

    assert exported["user"]["email"] == "listener@example.com"
    assert exported["oauth_accounts"][0]["tokens"] == "[REDACTED]"
    assert exported["saved_tracks"][0]["name"] == "Track One"
    assert exported["followed_artists"][0]["name"] == "Artist One"
    assert exported["sessions"][0]["messages"][0]["content"] == "Tell me about Radiohead"
    assert exported["recommendations"][0]["candidates"][0]["reason"] == "Because of Artist One"
    assert exported["data_rules"]["model_training"] == "GrooveGraph does not train ML/AI models on Spotify content."
    assert "raw-access-token" not in serialized
    assert "raw-refresh-token" not in serialized
