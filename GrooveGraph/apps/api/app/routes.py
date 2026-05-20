import uuid
import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.agent_graph import GrooveGraphAgent
from app.config import settings
from app.db import get_db
from app.deletion import disconnect_spotify_user_data
from app.live_music import LivePerformanceService, find_artist_or_404_query
from app.models import (
    OAuthAccount,
    RecommendationCandidate,
    RecommendationRun,
    SourceDocument,
    SpotifyArtist,
    SpotifyTrack,
    User,
    UserFollowedArtist,
    UserSavedTrack,
    UserTopArtist,
    UserTopTrack,
)
from app.neo4j_graph import Neo4jGraphService
from app.rag import (
    RagSearchRequest,
    SourceDocumentInput,
    WeaviateRagStore,
    chunk_document,
    citation_from_chunk,
    persist_source_document,
)
from app.privacy import delete_my_data, delete_recommendation_history, delete_session, privacy_export
from app.recommendation_planner import RecommendationPlannerService, recommendation_payload
from app.security import token_cipher
from app.spotify import (
    SpotifyClient,
    SpotifyError,
    add_tracks_to_spotify_playlist,
    create_discovery_playlist_from_recommendations,
    create_spotify_playlist_from_recommendations,
    get_spotify_account,
    save_spotify_track,
    spotify_playlist_items,
    sync_spotify_library,
)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class StreamChatRequest(BaseModel):
    message: str


class RecommendationRunRequest(BaseModel):
    prompt: str = "recommend music"
    allow_rediscovery: bool = False
    include_concert_boost: bool = True
    limit: int = 20


class RecommendationFeedbackRequest(BaseModel):
    action: str
    notes: str | None = None


class CreateRecommendationPlaylistRequest(BaseModel):
    name: str = "GrooveGraph Recommendations"
    candidate_ids: list[uuid.UUID] | None = None


class SpotifyCreateFromRecommendationsRequest(BaseModel):
    name: str = "GrooveGraph Discovery"
    run_id: uuid.UUID | None = None
    candidate_ids: list[uuid.UUID] | None = None


class SpotifyPlaylistAddRequest(BaseModel):
    track_ids: list[uuid.UUID]
    source_snapshot: dict[str, Any] | None = None


def get_rag_store() -> WeaviateRagStore:
    return WeaviateRagStore()


def get_graph_service() -> Neo4jGraphService:
    service = Neo4jGraphService()
    service.ensure_schema()
    return service


def get_spotify_client() -> SpotifyClient:
    return SpotifyClient()


def get_recommendation_service() -> RecommendationPlannerService:
    return RecommendationPlannerService()


def get_live_service() -> LivePerformanceService:
    return LivePerformanceService(graph_service=get_graph_service())


def get_or_create_current_user(
    db: Annotated[Session, Depends(get_db)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    user_id: Annotated[str | None, Query()] = None,
) -> User:
    resolved_user_id = user_id or x_user_id
    if resolved_user_id:
        user = db.get(User, uuid.UUID(resolved_user_id))
        if user is None:
            raise HTTPException(status_code=404, detail="User not found.")
        return user

    user = db.scalar(select(User).where(User.email == settings.dev_user_email))
    if user is None:
        user = User(email=settings.dev_user_email, display_name="GrooveGraph Listener")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.get("/auth/spotify/login")
def spotify_login(
    user: Annotated[User, Depends(get_or_create_current_user)],
    client: Annotated[SpotifyClient, Depends(get_spotify_client)],
) -> RedirectResponse:
    if not settings.spotify_client_id:
        raise HTTPException(status_code=500, detail="SPOTIFY_CLIENT_ID is not configured.")
    return RedirectResponse(client.authorize_url(state=str(user.id)))


@router.post("/chat")
def chat(
    request: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
) -> dict[str, Any]:
    session_id = request.session_id or str(uuid.uuid4())
    state = GrooveGraphAgent(db).invoke(user, session_id, request.message)
    return {
        "session_id": session_id,
        "run_id": state.get("run_id"),
        "answer": state.get("answer", ""),
        "intent": state.get("intent"),
        "current_entities": state.get("current_entities", []),
        "retrieval_question": state.get("retrieval_question"),
        "used_short_term_memory": state.get("used_short_term_memory", False),
        "citations": state.get("citations", []),
    }


@router.get("/chat/{session_id}")
def chat_history(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
) -> dict[str, Any]:
    return GrooveGraphAgent(db).history(user, session_id)


@router.post("/chat/{session_id}/stream")
def chat_stream(
    session_id: str,
    request: StreamChatRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
) -> StreamingResponse:
    def events():
        for event in GrooveGraphAgent(db).stream(user, session_id, request.message):
            yield f"event: {event['event']}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/rag/index-document")
def rag_index_document(
    request: SourceDocumentInput,
    db: Annotated[Session, Depends(get_db)],
    store: Annotated[WeaviateRagStore, Depends(get_rag_store)],
) -> dict[str, Any]:
    chunks = chunk_document(request)
    source = persist_source_document(db, request, chunks)
    store.index_chunks(chunks)
    return {"source_id": source.source_id, "chunks_indexed": len(chunks)}


@router.post("/rag/search")
def rag_search(
    request: RagSearchRequest,
    store: Annotated[WeaviateRagStore, Depends(get_rag_store)],
) -> dict[str, Any]:
    chunks = store.search(request)
    return {
        "items": chunks,
        "citations": [citation_from_chunk(chunk).model_dump() for chunk in chunks],
    }


@router.get("/rag/sources/{source_id}")
def rag_source(source_id: str, db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    source = db.scalar(select(SourceDocument).where(SourceDocument.source_id == source_id))
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found.")
    return {
        "source_id": source.source_id,
        "title": source.title,
        "url": source.url,
        "source_type": source.source_type,
        "metadata": source.source_metadata,
    }


@router.get("/graph/artist/{artist_id}")
def graph_artist(
    artist_id: str,
    service: Annotated[Neo4jGraphService, Depends(get_graph_service)],
) -> dict[str, Any]:
    result = service.find_artist(artist_id)
    service.close()
    if result is None:
        raise HTTPException(status_code=404, detail="Artist not found.")
    return result


@router.get("/graph/connections")
def graph_connections(
    from_: Annotated[str, Query(alias="from")],
    to: str,
    service: Annotated[Neo4jGraphService, Depends(get_graph_service)],
) -> dict[str, Any]:
    result = service.find_shortest_path_between_bands(from_, to)
    service.close()
    if result is None:
        raise HTTPException(status_code=404, detail="No connection path found.")
    return result


@router.get("/graph/side-projects")
def graph_side_projects(
    artist: str,
    service: Annotated[Neo4jGraphService, Depends(get_graph_service)],
) -> dict[str, Any]:
    result = service.find_side_projects(artist)
    service.close()
    return {"items": result}


@router.get("/graph/recommendation-neighborhood")
def graph_recommendation_neighborhood(
    user: Annotated[User, Depends(get_or_create_current_user)],
    service: Annotated[Neo4jGraphService, Depends(get_graph_service)],
    limit: int = 10,
) -> dict[str, Any]:
    result = service.find_unexplored_neighboring_artists(str(user.id), limit=limit)
    service.close()
    return {"items": result}


@router.get("/artists/{artist_id}/concerts")
def artist_concerts(
    artist_id: str,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LivePerformanceService, Depends(get_live_service)],
) -> dict[str, Any]:
    artist = db.scalar(find_artist_or_404_query(artist_id))
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found.")
    try:
        items = service.upcoming_for_artist(db, artist)
    finally:
        if service.graph_service:
            service.graph_service.close()
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/artists/{artist_id}/setlists")
def artist_setlists(
    artist_id: str,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LivePerformanceService, Depends(get_live_service)],
) -> dict[str, Any]:
    artist = db.scalar(find_artist_or_404_query(artist_id))
    if artist is None:
        raise HTTPException(status_code=404, detail="Artist not found.")
    try:
        items = service.setlists_for_artist(db, artist)
    finally:
        if service.graph_service:
            service.graph_service.close()
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/concerts/nearby")
def concerts_nearby(
    city: str,
    db: Annotated[Session, Depends(get_db)],
    service: Annotated[LivePerformanceService, Depends(get_live_service)],
    country: str | None = None,
    radius_km: int = 50,
) -> dict[str, Any]:
    try:
        items = service.nearby(db, city=city, country=country, radius_km=radius_km)
    finally:
        if service.graph_service:
            service.graph_service.close()
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.get("/concerts/recommended")
def concerts_recommended(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    service: Annotated[LivePerformanceService, Depends(get_live_service)],
    limit: int = 20,
) -> dict[str, Any]:
    try:
        items = service.recommended(db, user.id, limit=limit)
    finally:
        if service.graph_service:
            service.graph_service.close()
    return {"items": [item.model_dump(mode="json") for item in items]}


@router.post("/recommendations/run")
def recommendations_run(
    request: RecommendationRunRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    service: Annotated[RecommendationPlannerService, Depends(get_recommendation_service)],
) -> dict[str, Any]:
    run, candidates = service.run(
        db,
        user,
        request.prompt,
        allow_rediscovery=request.allow_rediscovery,
        include_concert_boost=request.include_concert_boost,
        limit=request.limit,
    )
    return {
        "run_id": str(run.id),
        "status": run.status,
        "items": [recommendation_payload(candidate) for candidate in candidates],
    }


@router.get("/recommendations/latest")
def recommendations_latest(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    service: Annotated[RecommendationPlannerService, Depends(get_recommendation_service)],
) -> dict[str, Any]:
    run, candidates = service.latest(db, user)
    if run is None:
        return {"run_id": None, "status": "empty", "items": []}
    return {
        "run_id": str(run.id),
        "status": run.status,
        "items": [recommendation_payload(candidate) for candidate in candidates],
    }


@router.post("/recommendations/{id}/feedback")
def recommendations_feedback(
    id: uuid.UUID,
    request: RecommendationFeedbackRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    service: Annotated[RecommendationPlannerService, Depends(get_recommendation_service)],
) -> dict[str, Any]:
    try:
        feedback = service.record_feedback(db, user, id, request.action, notes=request.notes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok", "feedback_id": str(feedback.id), "action": feedback.action}


@router.post("/recommendations/{id}/create-playlist")
def recommendations_create_playlist(
    id: uuid.UUID,
    request: CreateRecommendationPlaylistRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    client: Annotated[SpotifyClient, Depends(get_spotify_client)],
) -> dict[str, Any]:
    run = db.get(RecommendationRun, id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="Recommendation run not found.")
    candidate_query = select(RecommendationCandidate).where(RecommendationCandidate.run_id == run.id)
    if request.candidate_ids:
        candidate_query = candidate_query.where(RecommendationCandidate.id.in_(request.candidate_ids))
    candidates = db.scalars(candidate_query).all()
    track_ids = [candidate.track_id for candidate in candidates if candidate.track_id]
    try:
        result = create_spotify_playlist_from_recommendations(
            db,
            user,
            client,
            name=request.name,
            candidate_ids=track_ids,
        )
    except SpotifyError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail={"message": str(exc), "payload": exc.payload}) from exc
    return {"status": "ok", **result}


@router.post("/spotify/playlists/create-from-recommendations")
def spotify_create_playlist_from_recommendations(
    request: SpotifyCreateFromRecommendationsRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    client: Annotated[SpotifyClient, Depends(get_spotify_client)],
) -> dict[str, Any]:
    try:
        result = create_discovery_playlist_from_recommendations(
            db,
            user,
            client,
            name=request.name,
            run_id=request.run_id,
            candidate_ids=request.candidate_ids,
        )
    except SpotifyError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail={"message": str(exc), "payload": exc.payload}) from exc
    return {"status": "ok", **result}


@router.post("/spotify/playlists/{playlist_id}/add")
def spotify_playlist_add(
    playlist_id: str,
    request: SpotifyPlaylistAddRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    client: Annotated[SpotifyClient, Depends(get_spotify_client)],
) -> dict[str, Any]:
    try:
        result = add_tracks_to_spotify_playlist(
            db,
            user,
            client,
            playlist_id=playlist_id,
            track_ids=request.track_ids,
            source_snapshot=request.source_snapshot,
        )
    except SpotifyError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail={"message": str(exc), "payload": exc.payload}) from exc
    return {"status": "ok", **result}


@router.post("/spotify/tracks/{track_id}/save")
def spotify_track_save(
    track_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    client: Annotated[SpotifyClient, Depends(get_spotify_client)],
) -> dict[str, Any]:
    try:
        return save_spotify_track(db, user, client, track_id=track_id)
    except SpotifyError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail={"message": str(exc), "payload": exc.payload}) from exc


@router.get("/spotify/playlists/{playlist_id}/items")
def spotify_playlist_get_items(
    playlist_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    client: Annotated[SpotifyClient, Depends(get_spotify_client)],
) -> dict[str, Any]:
    try:
        return spotify_playlist_items(db, user, client, playlist_id=playlist_id)
    except SpotifyError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail={"message": str(exc), "payload": exc.payload}) from exc


@router.get("/auth/spotify/callback")
def spotify_callback(
    code: str,
    state: str,
    db: Annotated[Session, Depends(get_db)],
    client: Annotated[SpotifyClient, Depends(get_spotify_client)],
) -> dict[str, str]:
    user = db.get(User, uuid.UUID(state))
    if user is None:
        raise HTTPException(status_code=404, detail="OAuth state user was not found.")

    try:
        tokens = client.exchange_code(code)
        profile = client.http.get(
            "https://api.spotify.com/v1/me",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
        )
        profile_payload = SpotifyClient._json_or_error(profile)
    except SpotifyError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail={"message": str(exc), "payload": exc.payload}) from exc

    provider_account_id = profile_payload["id"]
    account = db.scalar(
        select(OAuthAccount).where(
            OAuthAccount.provider == "spotify",
            OAuthAccount.provider_account_id == provider_account_id,
        )
    )
    if account is None:
        account = OAuthAccount(provider="spotify", provider_account_id=provider_account_id, user_id=user.id)
        db.add(account)

    user.display_name = profile_payload.get("display_name") or user.display_name
    if profile_payload.get("email"):
        user.email = profile_payload["email"]
    account.user_id = user.id
    account.encrypted_access_token = token_cipher.encrypt(tokens.access_token)
    account.encrypted_refresh_token = token_cipher.encrypt(tokens.refresh_token)
    account.scopes = tokens.scope
    account.expires_at = tokens.expires_at
    db.commit()

    return {"status": "connected", "provider": "spotify"}


@router.post("/auth/spotify/disconnect")
def spotify_disconnect(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
) -> dict[str, Any]:
    deleted = disconnect_spotify_user_data(db, user.id)
    db.commit()
    return {"status": "disconnected", "deleted": deleted}


@router.get("/privacy/export")
def export_privacy_data(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
) -> JSONResponse:
    return JSONResponse(
        privacy_export(db, user),
        headers={"Content-Disposition": 'attachment; filename="groovegraph-privacy-export.json"'},
    )


@router.post("/privacy/delete-my-data")
def privacy_delete_my_data(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
) -> dict[str, Any]:
    user_id = user.id
    delete_my_data(db, user_id)
    db.commit()
    return {"status": "deleted", "user_id": str(user_id)}


@router.delete("/sessions/{session_id}")
def privacy_delete_session(
    session_id: str,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
) -> dict[str, Any]:
    deleted = delete_session(db, user.id, session_id)
    db.commit()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"status": "deleted", "deleted_sessions": deleted}


@router.delete("/recommendations/history")
def privacy_delete_recommendations(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
) -> dict[str, Any]:
    deleted = delete_recommendation_history(db, user.id)
    db.commit()
    return {"status": "deleted", "deleted_runs": deleted}


@router.get("/me/spotify/status")
def spotify_status(user: Annotated[User, Depends(get_or_create_current_user)], db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    account = get_spotify_account(db, user.id)
    return {
        "connected": account is not None,
        "scopes": account.scopes.split(" ") if account and account.scopes else [],
        "expires_at": account.expires_at.isoformat() if account and account.expires_at else None,
    }


@router.post("/sync/spotify")
def sync_spotify(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_or_create_current_user)],
    client: Annotated[SpotifyClient, Depends(get_spotify_client)],
) -> dict[str, Any]:
    try:
        counts = sync_spotify_library(db, user, client)
    except SpotifyError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail={"message": str(exc), "payload": exc.payload}) from exc
    return {"status": "ok", "counts": counts}


@router.get("/me/music-profile")
def music_profile(user: Annotated[User, Depends(get_or_create_current_user)], db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    saved_tracks = db.scalar(select(func.count()).select_from(UserSavedTrack).where(UserSavedTrack.user_id == user.id)) or 0
    followed_artists = (
        db.scalar(select(func.count()).select_from(UserFollowedArtist).where(UserFollowedArtist.user_id == user.id)) or 0
    )
    top_tracks = db.scalar(select(func.count()).select_from(UserTopTrack).where(UserTopTrack.user_id == user.id)) or 0
    top_artists = db.scalar(select(func.count()).select_from(UserTopArtist).where(UserTopArtist.user_id == user.id)) or 0
    return {
        "user_id": str(user.id),
        "saved_tracks": saved_tracks,
        "followed_artists": followed_artists,
        "top_tracks": top_tracks,
        "top_artists": top_artists,
        "generated_at": datetime.now(UTC).isoformat(),
    }


@router.get("/me/tracks")
def my_tracks(user: Annotated[User, Depends(get_or_create_current_user)], db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    rows = db.execute(
        select(SpotifyTrack)
        .join(UserSavedTrack, UserSavedTrack.track_id == SpotifyTrack.id)
        .where(UserSavedTrack.user_id == user.id)
        .order_by(SpotifyTrack.name)
    ).scalars()
    return {"items": [_track_payload(track) for track in rows]}


@router.get("/me/artists")
def my_artists(user: Annotated[User, Depends(get_or_create_current_user)], db: Annotated[Session, Depends(get_db)]) -> dict[str, Any]:
    rows = db.execute(
        select(SpotifyArtist)
        .join(UserFollowedArtist, UserFollowedArtist.artist_id == SpotifyArtist.id)
        .where(UserFollowedArtist.user_id == user.id)
        .order_by(SpotifyArtist.name)
    ).scalars()
    return {"items": [_artist_payload(artist) for artist in rows]}


def _track_payload(track: SpotifyTrack) -> dict[str, Any]:
    return {
        "id": str(track.id),
        "spotify_id": track.spotify_id,
        "name": track.name,
        "album_name": track.album_name,
        "duration_ms": track.duration_ms,
        "preview_url": track.preview_url,
        "external_url": track.external_url,
    }


def _artist_payload(artist: SpotifyArtist) -> dict[str, Any]:
    return {
        "id": str(artist.id),
        "spotify_id": artist.spotify_id,
        "name": artist.name,
        "genres": artist.genres.get("items", []),
        "external_url": artist.external_url,
    }
