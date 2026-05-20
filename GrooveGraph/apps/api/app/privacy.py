import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.deletion import delete_user_personal_data
from app.models import (
    AgentCheckpoint,
    OAuthAccount,
    RecommendationCandidate,
    RecommendationFeedback,
    RecommendationRun,
    Session as UserSession,
    SessionMessage,
    SpotifyArtist,
    SpotifyPlaylistAction,
    SpotifyTrack,
    ToolCall,
    User,
    UserFollowedArtist,
    UserPlaylistTrack,
    UserSavedTrack,
    UserTopArtist,
    UserTopTrack,
)

TOKEN_FIELD_PATTERN = re.compile(r"(access_token|refresh_token|encrypted_access_token|encrypted_refresh_token)", re.I)
BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.I)


class TokenRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_tokens(record.getMessage())
        record.args = ()
        return True


def redact_tokens(value: Any) -> str:
    text = str(value)
    text = BEARER_PATTERN.sub("Bearer [REDACTED]", text)
    text = re.sub(r"('|\")?([A-Za-z_]*token[A-Za-z_]*|encrypted_[A-Za-z_]*token)('|\")?\s*:\s*('|\")([^'\"]+)('|\")", r"\1\2\3: \4[REDACTED]\6", text, flags=re.I)
    text = re.sub(r"(access_token|refresh_token|encrypted_access_token|encrypted_refresh_token)=([^&\s]+)", r"\1=[REDACTED]", text, flags=re.I)
    return text


def privacy_export(db: Session, user: User) -> dict[str, Any]:
    session_ids = select(UserSession.id).where(UserSession.user_id == user.id)
    run_ids = select(RecommendationRun.id).where(RecommendationRun.user_id == user.id)
    return {
        "exported_at": datetime.now(UTC).isoformat(),
        "data_rules": {
            "spotify_data": "Stored only as needed to operate GrooveGraph.",
            "model_training": "GrooveGraph does not train ML/AI models on Spotify content.",
            "lyrics": "Full lyrics are not stored unless a licensed provider and plan permits it.",
            "web_claims": "Source provenance is maintained for web claims.",
            "oauth_tokens": "OAuth tokens are encrypted at rest and omitted from exports.",
            "logs": "Raw access and refresh tokens are redacted from logs.",
        },
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "locale": user.locale,
        },
        "oauth_accounts": [
            {
                "provider": account.provider,
                "provider_account_id": account.provider_account_id,
                "scopes": account.scopes.split(" ") if account.scopes else [],
                "expires_at": account.expires_at.isoformat() if account.expires_at else None,
                "tokens": "[REDACTED]",
            }
            for account in db.scalars(select(OAuthAccount).where(OAuthAccount.user_id == user.id)).all()
        ],
        "saved_tracks": [
            _track_export(track)
            for track in db.scalars(
                select(SpotifyTrack)
                .join(UserSavedTrack, UserSavedTrack.track_id == SpotifyTrack.id)
                .where(UserSavedTrack.user_id == user.id)
                .order_by(SpotifyTrack.name)
            ).all()
        ],
        "followed_artists": [
            _artist_export(artist)
            for artist in db.scalars(
                select(SpotifyArtist)
                .join(UserFollowedArtist, UserFollowedArtist.artist_id == SpotifyArtist.id)
                .where(UserFollowedArtist.user_id == user.id)
                .order_by(SpotifyArtist.name)
            ).all()
        ],
        "top_tracks": [
            {"track": _track_export(track), "time_range": row.time_range, "rank": row.rank}
            for row, track in db.execute(
                select(UserTopTrack, SpotifyTrack)
                .join(SpotifyTrack, SpotifyTrack.id == UserTopTrack.track_id)
                .where(UserTopTrack.user_id == user.id)
                .order_by(UserTopTrack.time_range, UserTopTrack.rank)
            ).all()
        ],
        "top_artists": [
            {"artist": _artist_export(artist), "time_range": row.time_range, "rank": row.rank}
            for row, artist in db.execute(
                select(UserTopArtist, SpotifyArtist)
                .join(SpotifyArtist, SpotifyArtist.id == UserTopArtist.artist_id)
                .where(UserTopArtist.user_id == user.id)
                .order_by(UserTopArtist.time_range, UserTopArtist.rank)
            ).all()
        ],
        "playlist_tracks": [
            {
                "playlist_id": str(row.playlist_id),
                "track": _track_export(track),
                "position": row.position,
            }
            for row, track in db.execute(
                select(UserPlaylistTrack, SpotifyTrack)
                .join(SpotifyTrack, SpotifyTrack.id == UserPlaylistTrack.track_id)
                .where(UserPlaylistTrack.user_id == user.id)
                .order_by(UserPlaylistTrack.position)
            ).all()
        ],
        "sessions": [
            {
                "id": str(session.id),
                "title": session.title,
                "messages": [
                    {
                        "role": message.role,
                        "content": message.content,
                        "metadata": message.message_metadata,
                        "created_at": message.created_at.isoformat() if message.created_at else None,
                    }
                    for message in db.scalars(
                        select(SessionMessage).where(SessionMessage.session_id == session.id).order_by(SessionMessage.created_at)
                    ).all()
                ],
            }
            for session in db.scalars(select(UserSession).where(UserSession.user_id == user.id).order_by(UserSession.created_at)).all()
        ],
        "recommendations": [
            {
                "run_id": str(run.id),
                "prompt": run.prompt,
                "status": run.status,
                "candidates": [
                    {
                        "id": str(candidate.id),
                        "candidate_key": candidate.candidate_key,
                        "candidate_type": candidate.candidate_type,
                        "score": candidate.score,
                        "reason": candidate.reason,
                        "evidence": candidate.evidence,
                    }
                    for candidate in db.scalars(
                        select(RecommendationCandidate).where(RecommendationCandidate.run_id == run.id).order_by(RecommendationCandidate.score.desc())
                    ).all()
                ],
            }
            for run in db.scalars(select(RecommendationRun).where(RecommendationRun.user_id == user.id).order_by(RecommendationRun.created_at)).all()
        ],
        "feedback": [
            {
                "candidate_key": feedback.candidate_key,
                "action": feedback.action,
                "notes": feedback.notes,
            }
            for feedback in db.scalars(select(RecommendationFeedback).where(RecommendationFeedback.user_id == user.id)).all()
        ],
        "tool_calls": [
            {
                "tool_name": call.tool_name,
                "arguments": call.arguments,
                "result_summary": call.result_summary,
            }
            for call in db.scalars(select(ToolCall).where(ToolCall.user_id == user.id)).all()
        ],
        "playlist_actions": [
            {
                "spotify_playlist_id": action.spotify_playlist_id,
                "action": action.action,
                "status": action.status,
                "source_snapshot": action.source_snapshot,
                "result_metadata": action.result_metadata,
            }
            for action in db.scalars(select(SpotifyPlaylistAction).where(SpotifyPlaylistAction.user_id == user.id)).all()
        ],
        "agent_checkpoints": [
            {
                "external_session_id": checkpoint.external_session_id,
                "state": checkpoint.state,
            }
            for checkpoint in db.scalars(select(AgentCheckpoint).where(AgentCheckpoint.user_id == user.id)).all()
        ],
    }


def delete_session(db: Session, user_id: uuid.UUID, session_id: str) -> int:
    query = select(UserSession.id).where(UserSession.user_id == user_id)
    try:
        parsed = uuid.UUID(session_id)
        query = query.where(UserSession.id == parsed)
    except ValueError:
        query = query.where(UserSession.title == session_id)
    ids = [row for row in db.scalars(query).all()]
    if not ids:
        return 0
    db.execute(delete(ToolCall).where(ToolCall.session_id.in_(ids)))
    db.execute(delete(AgentCheckpoint).where(AgentCheckpoint.session_id.in_(ids)))
    db.execute(delete(SessionMessage).where(SessionMessage.session_id.in_(ids)))
    result = db.execute(delete(UserSession).where(UserSession.id.in_(ids)))
    return result.rowcount or 0


def delete_recommendation_history(db: Session, user_id: uuid.UUID) -> int:
    run_ids = select(RecommendationRun.id).where(RecommendationRun.user_id == user_id)
    db.execute(delete(RecommendationFeedback).where(RecommendationFeedback.user_id == user_id))
    db.execute(delete(RecommendationCandidate).where(RecommendationCandidate.run_id.in_(run_ids)))
    result = db.execute(delete(RecommendationRun).where(RecommendationRun.user_id == user_id))
    return result.rowcount or 0


def delete_my_data(db: Session, user_id: uuid.UUID) -> None:
    delete_user_personal_data(db, user_id)


def _track_export(track: SpotifyTrack) -> dict[str, Any]:
    return {
        "id": str(track.id),
        "spotify_id": track.spotify_id,
        "name": track.name,
        "album_name": track.album_name,
        "external_url": track.external_url,
    }


def _artist_export(artist: SpotifyArtist) -> dict[str, Any]:
    return {
        "id": str(artist.id),
        "spotify_id": artist.spotify_id,
        "name": artist.name,
        "genres": artist.genres.get("items", []),
        "external_url": artist.external_url,
    }
