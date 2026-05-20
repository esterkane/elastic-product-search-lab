from datetime import UTC, date, datetime

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.live_music import (
    BandsintownService,
    LivePerformanceService,
    SetlistFmService,
    TicketmasterService,
    filter_events_by_date,
)
from app.models import ArtistEvent, Base, Event, SpotifyArtist, User, UserFollowedArtist, Venue


def build_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_bandsintown_connector_normalizes_upcoming_events() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["app_id"] == "test-app"
        return httpx.Response(
            200,
            json=[
                {
                    "id": "evt-1",
                    "datetime": "2026-06-01T20:00:00",
                    "url": "https://bandsintown.example/radiohead",
                    "lineup": ["Radiohead", "Openers"],
                    "venue": {
                        "name": "Waldbuhne",
                        "city": "Berlin",
                        "region": "Berlin",
                        "country": "DE",
                        "latitude": "52.516",
                        "longitude": "13.239",
                    },
                    "offers": [{"url": "https://tickets.example/evt-1"}],
                }
            ],
        )

    service = BandsintownService(http_client=httpx.Client(transport=httpx.MockTransport(handler)), app_id="test-app")

    events = service.artist_events("Radiohead")

    assert events[0].source_id == "bandsintown:evt-1"
    assert events[0].source_status == "current"
    assert events[0].venue is not None
    assert events[0].venue.city == "Berlin"
    assert events[0].ticket_url == "https://tickets.example/evt-1"


def test_setlistfm_connector_normalizes_historical_setlists() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "setlist-key"
        return httpx.Response(
            200,
            json={
                "setlist": [
                    {
                        "id": "sl-1",
                        "eventDate": "02-07-1997",
                        "url": "https://setlist.fm/sl-1",
                        "venue": {
                            "id": "venue-1",
                            "name": "Glastonbury Festival",
                            "city": {
                                "name": "Pilton",
                                "state": "Somerset",
                                "country": {"code": "GB"},
                                "coords": {"lat": "51.159", "long": "-2.585"},
                            },
                        },
                        "sets": {"set": [{"song": [{"name": "Paranoid Android"}]}]},
                    }
                ]
            },
        )

    service = SetlistFmService(http_client=httpx.Client(transport=httpx.MockTransport(handler)), api_key="setlist-key")

    events = service.artist_setlists("Radiohead")

    assert events[0].source_id == "setlistfm:sl-1"
    assert events[0].starts_at == datetime(1997, 7, 2, tzinfo=UTC)
    assert events[0].source_status == "historical"
    assert events[0].venue is not None
    assert events[0].venue.country == "GB"


def test_ticketmaster_connector_is_optional_and_normalizes_city_events() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["apikey"] == "tm-key"
        return httpx.Response(
            200,
            json={
                "_embedded": {
                    "events": [
                        {
                            "id": "tm-1",
                            "name": "Pixies",
                            "url": "https://ticketmaster.example/tm-1",
                            "dates": {"start": {"dateTime": "2026-08-01T19:30:00Z"}},
                            "_embedded": {
                                "attractions": [{"name": "Pixies"}],
                                "venues": [
                                    {
                                        "id": "venue-tm",
                                        "name": "Columbiahalle",
                                        "city": {"name": "Berlin"},
                                        "country": {"countryCode": "DE"},
                                    }
                                ],
                            },
                        }
                    ]
                }
            },
        )

    disabled = TicketmasterService(api_key="")
    enabled = TicketmasterService(http_client=httpx.Client(transport=httpx.MockTransport(handler)), api_key="tm-key")

    assert disabled.city_events("Berlin") == []
    assert enabled.city_events("Berlin", country="DE")[0].lineup == ["Pixies"]


def test_date_filtering_keeps_events_inside_window() -> None:
    service = BandsintownService(app_id="")
    early = service._normalize_event(
        {"id": "early", "datetime": "2026-01-01", "venue": {"name": "A"}, "lineup": ["A"]},
        artist_name="A",
    )
    inside = service._normalize_event(
        {"id": "inside", "datetime": "2026-06-01", "venue": {"name": "B"}, "lineup": ["B"]},
        artist_name="B",
    )

    filtered = filter_events_by_date([early, inside], start=date(2026, 5, 1), end=date(2026, 7, 1))

    assert [event.source_id for event in filtered] == ["bandsintown:inside"]


def test_persisted_concert_has_ui_ready_schema() -> None:
    db = build_session()
    artist = SpotifyArtist(spotify_id="spotify:artist:pixies", name="Pixies", genres={})
    db.add(artist)
    db.commit()

    class FakeBandsintown:
        def artist_events(self, artist_name: str):
            return [
                BandsintownService._normalize_event(
                    {
                        "id": "pixies-1",
                        "datetime": "2026-09-10T20:00:00Z",
                        "url": "https://bandsintown.example/pixies-1",
                        "venue": {"name": "Columbiahalle", "city": "Berlin", "country": "DE"},
                        "lineup": ["Pixies"],
                    },
                    artist_name=artist_name,
                )
            ]

    service = LivePerformanceService(bandsintown=FakeBandsintown(), setlistfm=SetlistFmService(api_key=""))

    items = service.upcoming_for_artist(db, artist)

    assert items[0].model_dump(mode="json") == {
        "id": str(db.scalar(select(Event)).id),
        "source_id": "bandsintown:pixies-1",
        "source": "bandsintown",
        "title": "Pixies at Columbiahalle",
        "starts_at": "2026-09-10T20:00:00Z",
        "venue": {
            "id": str(db.scalar(select(Venue)).id),
            "name": "Columbiahalle",
            "city": "Berlin",
            "region": None,
            "country": "DE",
            "latitude": None,
            "longitude": None,
            "url": None,
        },
        "city": "Berlin",
        "country": "DE",
        "ticket_url": None,
        "source_url": "https://bandsintown.example/pixies-1",
        "lineup": ["Pixies"],
        "confidence": 0.86,
        "source_status": "current",
        "artist_id": str(artist.id),
        "artist_name": "Pixies",
    }
    assert db.scalar(select(ArtistEvent)).source_id == "bandsintown:pixies-1"


def test_recommended_prioritizes_followed_artists() -> None:
    db = build_session()
    user = User(email="listener@example.com")
    followed = SpotifyArtist(spotify_id="spotify:artist:radiohead", name="Radiohead", genres={})
    db.add_all([user, followed])
    db.flush()
    db.add(UserFollowedArtist(user_id=user.id, artist_id=followed.id))
    db.commit()

    called: list[str] = []

    class FakeBandsintown:
        def artist_events(self, artist_name: str):
            called.append(artist_name)
            return []

    service = LivePerformanceService(bandsintown=FakeBandsintown(), setlistfm=SetlistFmService(api_key=""))

    assert service.recommended(db, user.id) == []
    assert called == ["Radiohead"]
