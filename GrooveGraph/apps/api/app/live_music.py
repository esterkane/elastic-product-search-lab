import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Protocol

import httpx
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import ArtistEvent, Event, RecommendationCandidate, SpotifyArtist, UserFollowedArtist, Venue
from app.neo4j_graph import Neo4jGraphService, RelationshipProvenance
from app.schemas import ConcertEvent, Venue as VenueSchema


@dataclass
class LiveVenue:
    name: str
    city: str | None = None
    region: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    url: str | None = None
    source_id: str | None = None


@dataclass
class LiveEvent:
    source_id: str
    source: str
    title: str
    starts_at: datetime | None
    venue: LiveVenue | None = None
    ticket_url: str | None = None
    source_url: str | None = None
    lineup: list[str] = field(default_factory=list)
    artist_name: str | None = None
    artist_id: str | None = None
    confidence: float = 0.7
    source_status: str = "current"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_current(self) -> bool:
        return self.source_status == "current"


class ConcertConnector(Protocol):
    def artist_events(self, artist_name: str) -> list[LiveEvent]:
        ...


class BandsintownService:
    base_url = "https://rest.bandsintown.com"

    def __init__(self, http_client: httpx.Client | None = None, app_id: str | None = None) -> None:
        self.http = http_client or httpx.Client(timeout=20)
        self.app_id = app_id if app_id is not None else settings.bandsintown_app_id

    def artist_events(self, artist_name: str) -> list[LiveEvent]:
        if not self.app_id:
            return []
        response = self.http.get(
            f"{self.base_url}/artists/{artist_name}/events",
            params={"app_id": self.app_id, "date": "upcoming"},
        )
        response.raise_for_status()
        return [self._normalize_event(item, artist_name=artist_name) for item in response.json()]

    @staticmethod
    def _normalize_event(payload: dict[str, Any], *, artist_name: str) -> LiveEvent:
        venue = payload.get("venue") or {}
        starts_at = _parse_datetime(payload.get("datetime"))
        lineup = [str(item) for item in payload.get("lineup", []) if item]
        return LiveEvent(
            source_id=f"bandsintown:{payload.get('id')}",
            source="bandsintown",
            title=f"{artist_name} at {venue.get('name', 'TBA')}",
            starts_at=starts_at,
            venue=LiveVenue(
                source_id=f"bandsintown:venue:{venue.get('name')}:{venue.get('city')}",
                name=venue.get("name") or "TBA",
                city=venue.get("city"),
                region=venue.get("region"),
                country=venue.get("country"),
                latitude=_float_or_none(venue.get("latitude")),
                longitude=_float_or_none(venue.get("longitude")),
            ),
            ticket_url=payload.get("offers", [{}])[0].get("url") if payload.get("offers") else None,
            source_url=payload.get("url"),
            lineup=lineup or [artist_name],
            artist_name=artist_name,
            confidence=0.86,
            source_status="current",
            metadata={"raw_source": "bandsintown"},
        )


class SetlistFmService:
    base_url = "https://api.setlist.fm/rest/1.0"

    def __init__(self, http_client: httpx.Client | None = None, api_key: str | None = None) -> None:
        self.http = http_client or httpx.Client(timeout=20)
        self.api_key = api_key if api_key is not None else settings.setlistfm_api_key

    def artist_events(self, artist_name: str) -> list[LiveEvent]:
        return self.artist_setlists(artist_name)

    def artist_setlists(self, artist_name: str, page: int = 1) -> list[LiveEvent]:
        if not self.api_key:
            return []
        response = self.http.get(
            f"{self.base_url}/search/setlists",
            params={"artistName": artist_name, "p": page},
            headers={"x-api-key": self.api_key, "Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
        return [self._normalize_setlist(item, artist_name=artist_name) for item in payload.get("setlist", [])]

    @staticmethod
    def _normalize_setlist(payload: dict[str, Any], *, artist_name: str) -> LiveEvent:
        venue_payload = payload.get("venue") or {}
        city_payload = venue_payload.get("city") or {}
        country_payload = city_payload.get("country") or {}
        event_date = _parse_setlist_date(payload.get("eventDate"))
        venue_name = venue_payload.get("name") or "Unknown venue"
        return LiveEvent(
            source_id=f"setlistfm:{payload.get('id')}",
            source="setlistfm",
            title=f"{artist_name} at {venue_name}",
            starts_at=event_date,
            venue=LiveVenue(
                source_id=f"setlistfm:venue:{venue_payload.get('id') or venue_name}",
                name=venue_name,
                city=city_payload.get("name"),
                region=city_payload.get("state"),
                country=country_payload.get("code") or country_payload.get("name"),
                latitude=_float_or_none(city_payload.get("coords", {}).get("lat")),
                longitude=_float_or_none(city_payload.get("coords", {}).get("long")),
                url=venue_payload.get("url"),
            ),
            source_url=payload.get("url"),
            lineup=[artist_name],
            artist_name=artist_name,
            confidence=0.78,
            source_status="historical",
            metadata={"raw_source": "setlistfm", "set_count": len(payload.get("sets", {}).get("set", []))},
        )


class TicketmasterService:
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json"

    def __init__(self, http_client: httpx.Client | None = None, api_key: str | None = None) -> None:
        self.http = http_client or httpx.Client(timeout=20)
        self.api_key = api_key if api_key is not None else settings.ticketmaster_api_key

    def city_events(self, city: str, country: str | None = None, radius_km: int = 50) -> list[LiveEvent]:
        if not self.api_key:
            return []
        params: dict[str, Any] = {
            "apikey": self.api_key,
            "city": city,
            "radius": radius_km,
            "unit": "km",
            "classificationName": "music",
        }
        if country:
            params["countryCode"] = country
        response = self.http.get(self.base_url, params=params)
        response.raise_for_status()
        events = response.json().get("_embedded", {}).get("events", [])
        return [self._normalize_event(item) for item in events]

    @staticmethod
    def _normalize_event(payload: dict[str, Any]) -> LiveEvent:
        venue_payload = (payload.get("_embedded", {}).get("venues") or [{}])[0]
        dates = payload.get("dates", {}).get("start", {})
        starts_at = _parse_datetime(dates.get("dateTime") or dates.get("localDate"))
        attractions = payload.get("_embedded", {}).get("attractions") or []
        lineup = [item.get("name") for item in attractions if item.get("name")]
        return LiveEvent(
            source_id=f"ticketmaster:{payload.get('id')}",
            source="ticketmaster",
            title=payload.get("name") or "Untitled concert",
            starts_at=starts_at,
            venue=LiveVenue(
                source_id=f"ticketmaster:venue:{venue_payload.get('id')}",
                name=venue_payload.get("name") or "TBA",
                city=venue_payload.get("city", {}).get("name"),
                region=venue_payload.get("state", {}).get("name"),
                country=venue_payload.get("country", {}).get("countryCode"),
                latitude=_float_or_none(venue_payload.get("location", {}).get("latitude")),
                longitude=_float_or_none(venue_payload.get("location", {}).get("longitude")),
                url=venue_payload.get("url"),
            ),
            ticket_url=payload.get("url"),
            source_url=payload.get("url"),
            lineup=lineup,
            artist_name=lineup[0] if lineup else None,
            confidence=0.82,
            source_status="current",
            metadata={"raw_source": "ticketmaster"},
        )


class LivePerformanceService:
    def __init__(
        self,
        bandsintown: BandsintownService | None = None,
        setlistfm: SetlistFmService | None = None,
        ticketmaster: TicketmasterService | None = None,
        graph_service: Neo4jGraphService | None = None,
    ) -> None:
        self.bandsintown = bandsintown or BandsintownService()
        self.setlistfm = setlistfm or SetlistFmService()
        self.ticketmaster = ticketmaster or TicketmasterService()
        self.graph_service = graph_service

    def upcoming_for_artist(self, db: Session, artist: SpotifyArtist) -> list[ConcertEvent]:
        events = self.bandsintown.artist_events(artist.name)
        persisted = [self.persist_event(db, event, artist=artist) for event in events]
        db.commit()
        return [to_concert_schema(event, artist=artist) for event in persisted]

    def setlists_for_artist(self, db: Session, artist: SpotifyArtist) -> list[ConcertEvent]:
        events = self.setlistfm.artist_setlists(artist.name)
        persisted = [self.persist_event(db, event, artist=artist) for event in events]
        db.commit()
        return [to_concert_schema(event, artist=artist) for event in persisted]

    def nearby(self, db: Session, *, city: str, country: str | None = None, radius_km: int = 50) -> list[ConcertEvent]:
        external = self.ticketmaster.city_events(city, country=country, radius_km=radius_km)
        for event in external:
            self.persist_event(db, event)
        db.commit()

        query = _event_query().where(func.lower(Event.city) == city.lower(), Event.is_current.is_(True))
        if country:
            query = query.where(func.lower(Event.country) == country.lower())
        return [to_concert_schema(event) for event in db.scalars(query.order_by(Event.starts_at.asc().nulls_last())).all()]

    def recommended(self, db: Session, user_id: uuid.UUID, limit: int = 20) -> list[ConcertEvent]:
        artists = db.scalars(
            select(SpotifyArtist)
            .join(UserFollowedArtist, UserFollowedArtist.artist_id == SpotifyArtist.id)
            .where(UserFollowedArtist.user_id == user_id)
            .order_by(SpotifyArtist.name)
            .limit(10)
        ).all()
        candidate_artists = db.scalars(
            select(SpotifyArtist)
            .join(RecommendationCandidate, RecommendationCandidate.artist_id == SpotifyArtist.id)
            .where(RecommendationCandidate.artist_id.is_not(None))
            .order_by(RecommendationCandidate.score.desc())
            .limit(10)
        ).all()

        seen = {artist.id for artist in artists}
        seeds = [*artists, *[artist for artist in candidate_artists if artist.id not in seen]]
        items: list[ConcertEvent] = []
        for artist in seeds:
            current = self.upcoming_for_artist(db, artist)
            items.extend(current)
            if len(items) >= limit:
                break
        return sorted(items, key=lambda item: item.starts_at or datetime.max.replace(tzinfo=UTC))[:limit]

    def persist_event(self, db: Session, live_event: LiveEvent, artist: SpotifyArtist | None = None) -> Event:
        venue = self._upsert_venue(db, live_event.venue) if live_event.venue else None
        event = db.scalar(select(Event).where(Event.source_id == live_event.source_id))
        if event is None:
            event = Event(source_id=live_event.source_id, source=live_event.source, title=live_event.title)
            db.add(event)
        event.starts_at = live_event.starts_at
        event.venue_id = venue.id if venue else None
        event.city = live_event.venue.city if live_event.venue else None
        event.region = live_event.venue.region if live_event.venue else None
        event.country = live_event.venue.country if live_event.venue else None
        event.ticket_url = live_event.ticket_url
        event.source_url = live_event.source_url
        event.lineup = {"items": live_event.lineup}
        event.source_metadata = live_event.metadata
        event.is_current = live_event.is_current
        event.confidence = live_event.confidence
        db.flush()

        if artist:
            link = db.scalar(
                select(ArtistEvent).where(ArtistEvent.artist_id == artist.id, ArtistEvent.event_id == event.id)
            )
            if link is None:
                db.add(ArtistEvent(artist_id=artist.id, event_id=event.id, source_id=event.source_id, confidence=event.confidence))
            self._upsert_graph(artist, event, venue)
        return event

    def _upsert_venue(self, db: Session, live_venue: LiveVenue | None) -> Venue | None:
        if live_venue is None:
            return None
        venue = None
        if live_venue.source_id:
            venue = db.scalar(select(Venue).where(Venue.source_id == live_venue.source_id))
        if venue is None:
            venue = db.scalar(
                select(Venue).where(
                    Venue.name == live_venue.name,
                    Venue.city == live_venue.city,
                    Venue.country == live_venue.country,
                )
            )
        if venue is None:
            venue = Venue(name=live_venue.name)
            db.add(venue)
        venue.source_id = live_venue.source_id or venue.source_id
        venue.city = live_venue.city
        venue.region = live_venue.region
        venue.country = live_venue.country
        venue.latitude = live_venue.latitude
        venue.longitude = live_venue.longitude
        venue.url = live_venue.url
        db.flush()
        return venue

    def _upsert_graph(self, artist: SpotifyArtist, event: Event, venue: Venue | None) -> None:
        if self.graph_service is None:
            return
        self.graph_service.ensure_schema()
        self.graph_service.upsert_artist(str(artist.id), name=artist.name, spotify_id=artist.spotify_id)
        self.graph_service.upsert_event(str(event.id), name=event.title, source_id=event.source_id, starts_at=event.starts_at.isoformat() if event.starts_at else None)
        provenance = RelationshipProvenance(
            source_id=event.source_id,
            confidence=event.confidence,
            evidence_text=f"{artist.name} performed at {event.title}.",
        )
        self.graph_service.upsert_relationship("Artist", str(artist.id), "PERFORMED_AT", "Event", str(event.id), provenance)
        if venue:
            self.graph_service.upsert_venue(str(venue.id), name=venue.name, city=venue.city, country=venue.country)
            self.graph_service.upsert_relationship(
                "Event",
                str(event.id),
                "AT_VENUE",
                "Venue",
                str(venue.id),
                RelationshipProvenance(
                    source_id=event.source_id,
                    confidence=event.confidence,
                    evidence_text=f"{event.title} is listed at {venue.name}.",
                ),
            )


def find_artist_or_404_query(artist_id: str) -> Select[tuple[SpotifyArtist]]:
    try:
        parsed = uuid.UUID(artist_id)
        return select(SpotifyArtist).where(SpotifyArtist.id == parsed)
    except ValueError:
        return select(SpotifyArtist).where(or_(SpotifyArtist.spotify_id == artist_id, func.lower(SpotifyArtist.name) == artist_id.lower()))


def filter_events_by_date(events: list[LiveEvent], *, start: date | None = None, end: date | None = None) -> list[LiveEvent]:
    filtered = []
    for event in events:
        if event.starts_at is None:
            continue
        event_date = event.starts_at.date()
        if start and event_date < start:
            continue
        if end and event_date > end:
            continue
        filtered.append(event)
    return filtered


def to_concert_schema(event: Event, artist: SpotifyArtist | None = None) -> ConcertEvent:
    venue = None
    if event.venue:
        venue = VenueSchema(
            id=event.venue.id,
            name=event.venue.name,
            city=event.venue.city,
            region=event.venue.region,
            country=event.venue.country,
            latitude=event.venue.latitude,
            longitude=event.venue.longitude,
            url=event.venue.url,
        )
    return ConcertEvent(
        id=str(event.id),
        source_id=event.source_id,
        source=event.source,
        title=event.title,
        starts_at=event.starts_at,
        venue=venue,
        city=event.city,
        country=event.country,
        ticket_url=event.ticket_url,
        source_url=event.source_url,
        lineup=event.lineup.get("items", []) if event.lineup else [],
        confidence=event.confidence,
        source_status="current" if event.is_current else "historical",
        artist_id=str(artist.id) if artist else None,
        artist_name=artist.name if artist else None,
    )


def _event_query() -> Select[tuple[Event]]:
    return select(Event)


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(value)
        except ValueError:
            return None
        return datetime.combine(parsed_date, datetime.min.time(), tzinfo=UTC)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _parse_setlist_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%d-%m-%Y")
    except ValueError:
        return _parse_datetime(value)
    return parsed.replace(tzinfo=UTC)


def _float_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
