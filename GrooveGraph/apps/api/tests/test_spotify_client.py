from datetime import UTC, datetime, timedelta

import httpx
import pytest

from app.models import OAuthAccount
from app.security import token_cipher
from app.spotify import RestrictedSpotifyEndpointError, SpotifyClient


def make_account(access_token: str = "access-token", refresh_token: str = "refresh-token") -> OAuthAccount:
    return OAuthAccount(
        user_id="00000000-0000-0000-0000-000000000001",
        provider="spotify",
        provider_account_id="spotify-user",
        encrypted_access_token=token_cipher.encrypt(access_token),
        encrypted_refresh_token=token_cipher.encrypt(refresh_token),
        scopes="user-library-read",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


def test_pagination_follows_next_urls() -> None:
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        if "offset=2" in str(request.url):
            return httpx.Response(200, json={"items": [{"id": "track-3"}], "next": None})
        return httpx.Response(
            200,
            json={
                "items": [{"id": "track-1"}, {"id": "track-2"}],
                "next": "https://api.spotify.com/v1/me/tracks?offset=2",
            },
        )

    client = SpotifyClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    items = list(client.paginate(make_account(), "/me/tracks", params={"limit": 2}))

    assert [item["id"] for item in items] == ["track-1", "track-2", "track-3"]
    assert len(seen_urls) == 2


def test_expired_token_refreshes_before_request() -> None:
    bearer_tokens: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://accounts.spotify.com/api/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "fresh-token",
                    "refresh_token": "fresh-refresh-token",
                    "expires_in": 3600,
                    "scope": "user-library-read",
                },
            )

        bearer_tokens.append(request.headers["Authorization"])
        return httpx.Response(200, json={"items": [], "next": None})

    account = make_account("expired-token", "refresh-token")
    account.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    client = SpotifyClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    client.get(account, "/me/tracks")

    assert bearer_tokens == ["Bearer fresh-token"]
    assert token_cipher.decrypt(account.encrypted_access_token) == "fresh-token"
    assert token_cipher.decrypt(account.encrypted_refresh_token) == "fresh-refresh-token"


def test_restricted_endpoints_are_not_called() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    client = SpotifyClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(RestrictedSpotifyEndpointError):
        client.get(make_account(), "/recommendations")

    with pytest.raises(RestrictedSpotifyEndpointError):
        client.get(make_account(), "/audio-features")

    with pytest.raises(RestrictedSpotifyEndpointError):
        client.get(make_account(), "/artists/abc/related-artists")

    with pytest.raises(RestrictedSpotifyEndpointError):
        client.get(make_account(), "/audio-analysis/abc")

    assert calls == 0
