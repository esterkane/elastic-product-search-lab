import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    AgentCheckpoint,
    OAuthAccount,
    RecommendationCandidate,
    RecommendationFeedback,
    RecommendationRun,
    Session as UserSession,
    SessionMessage,
    ToolCall,
    User,
    UserFollowedArtist,
    UserPlaylistTrack,
    UserSavedTrack,
    UserTopArtist,
    UserTopTrack,
    SpotifyPlaylistAction,
)


def disconnect_user_oauth(db: Session, user_id: uuid.UUID, provider: str | None = None) -> int:
    statement = delete(OAuthAccount).where(OAuthAccount.user_id == user_id)
    if provider is not None:
        statement = statement.where(OAuthAccount.provider == provider)
    result = db.execute(statement)
    return result.rowcount or 0


def disconnect_spotify_user_data(db: Session, user_id: uuid.UUID) -> dict[str, int]:
    counts = {
        "saved_tracks": db.execute(delete(UserSavedTrack).where(UserSavedTrack.user_id == user_id)).rowcount or 0,
        "followed_artists": db.execute(delete(UserFollowedArtist).where(UserFollowedArtist.user_id == user_id)).rowcount or 0,
        "playlist_tracks": db.execute(delete(UserPlaylistTrack).where(UserPlaylistTrack.user_id == user_id)).rowcount or 0,
        "top_tracks": db.execute(delete(UserTopTrack).where(UserTopTrack.user_id == user_id)).rowcount or 0,
        "top_artists": db.execute(delete(UserTopArtist).where(UserTopArtist.user_id == user_id)).rowcount or 0,
        "playlist_actions": db.execute(delete(SpotifyPlaylistAction).where(SpotifyPlaylistAction.user_id == user_id)).rowcount or 0,
        "oauth_accounts": disconnect_user_oauth(db, user_id, provider="spotify"),
    }
    return counts


def delete_user_personal_data(db: Session, user_id: uuid.UUID) -> None:
    session_ids = select(UserSession.id).where(UserSession.user_id == user_id)
    run_ids = select(RecommendationRun.id).where(RecommendationRun.user_id == user_id)

    db.execute(delete(ToolCall).where(ToolCall.user_id == user_id))
    db.execute(delete(AgentCheckpoint).where(AgentCheckpoint.user_id == user_id))
    db.execute(delete(SessionMessage).where(SessionMessage.session_id.in_(session_ids)))
    db.execute(delete(RecommendationFeedback).where(RecommendationFeedback.user_id == user_id))
    db.execute(delete(RecommendationCandidate).where(RecommendationCandidate.run_id.in_(run_ids)))
    db.execute(delete(RecommendationRun).where(RecommendationRun.user_id == user_id))
    db.execute(delete(UserPlaylistTrack).where(UserPlaylistTrack.user_id == user_id))
    db.execute(delete(SpotifyPlaylistAction).where(SpotifyPlaylistAction.user_id == user_id))
    db.execute(delete(UserTopArtist).where(UserTopArtist.user_id == user_id))
    db.execute(delete(UserTopTrack).where(UserTopTrack.user_id == user_id))
    db.execute(delete(UserFollowedArtist).where(UserFollowedArtist.user_id == user_id))
    db.execute(delete(UserSavedTrack).where(UserSavedTrack.user_id == user_id))
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    db.execute(delete(OAuthAccount).where(OAuthAccount.user_id == user_id))
    db.execute(delete(User).where(User.id == user_id))
