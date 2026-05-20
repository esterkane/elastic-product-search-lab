from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.deletion import delete_user_personal_data, disconnect_user_oauth
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
    ToolCall,
    User,
    UserFollowedArtist,
    UserPlaylistTrack,
    UserSavedTrack,
)


def build_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_disconnect_user_oauth_removes_provider_tokens_only() -> None:
    db = build_session()
    user = User(email="listener@example.com")
    db.add(user)
    db.flush()
    db.add_all(
        [
            OAuthAccount(user_id=user.id, provider="spotify", provider_account_id="spotify-1"),
            OAuthAccount(user_id=user.id, provider="github", provider_account_id="github-1"),
        ]
    )
    db.commit()

    deleted = disconnect_user_oauth(db, user.id, provider="spotify")
    db.commit()

    remaining = db.scalars(select(OAuthAccount.provider)).all()
    assert deleted == 1
    assert remaining == ["github"]


def test_delete_user_personal_data_removes_user_owned_records() -> None:
    db = build_session()
    user = User(email="listener@example.com")
    track = SpotifyTrack(spotify_id="track-1", name="Track One")
    artist = SpotifyArtist(spotify_id="artist-1", name="Artist One", genres={})
    playlist = SpotifyPlaylist(spotify_id="playlist-1", name="Playlist One")
    db.add_all([user, track, artist, playlist])
    db.flush()

    session = Session(user_id=user.id, title="Research")
    run = RecommendationRun(user_id=user.id, session_id=session.id, status="done")
    db.add_all([session, run])
    db.flush()

    db.add_all(
        [
            OAuthAccount(user_id=user.id, provider="spotify", provider_account_id="spotify-1"),
            SessionMessage(session_id=session.id, role="user", content="Find similar bands", message_metadata={}),
            UserSavedTrack(user_id=user.id, track_id=track.id),
            UserFollowedArtist(user_id=user.id, artist_id=artist.id),
            UserPlaylistTrack(user_id=user.id, playlist_id=playlist.id, track_id=track.id, position=1),
            RecommendationCandidate(run_id=run.id, track_id=track.id, score=0.9, evidence={}),
            ToolCall(user_id=user.id, session_id=session.id, tool_name="spotify.search", arguments={}),
        ]
    )
    db.commit()

    delete_user_personal_data(db, user.id)
    db.commit()

    for model in [
        User,
        OAuthAccount,
        Session,
        SessionMessage,
        UserSavedTrack,
        UserFollowedArtist,
        UserPlaylistTrack,
        RecommendationRun,
        RecommendationCandidate,
        ToolCall,
    ]:
        assert db.scalar(select(model).limit(1)) is None

    assert db.scalar(select(SpotifyTrack).limit(1)) is not None
    assert db.scalar(select(SpotifyArtist).limit(1)) is not None
    assert db.scalar(select(SpotifyPlaylist).limit(1)) is not None
