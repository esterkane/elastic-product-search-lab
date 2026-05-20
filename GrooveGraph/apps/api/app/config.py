from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "groovegraph-api"
    database_url: str = "postgresql+psycopg://groovegraph:groovegraph@postgres:5432/groovegraph"
    fernet_secret: str = "groovegraph-local-dev-fernet-secret-change-me"
    redis_url: str = "redis://redis:6379/0"
    weaviate_url: str = "http://weaviate:8080"
    reranker_api_key: str | None = None
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "groovegraph-password"
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:8100/auth/spotify/callback"
    spotify_liked_songs_playlist_id: str | None = None
    spotify_liked_songs_playlist_name: str = "Lieblingssongs"
    dev_user_email: str = "listener@groovegraph.local"
    musicbrainz_user_agent: str = "GrooveGraph/0.1.0 (https://localhost; contact@example.com)"
    lastfm_api_key: str | None = None
    tavily_api_key: str | None = None
    brave_search_api_key: str | None = None
    serpapi_api_key: str | None = None
    bandsintown_app_id: str | None = None
    setlistfm_api_key: str | None = None
    ticketmaster_api_key: str | None = None
    otel_exporter_otlp_endpoint: str | None = None
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = 120


settings = Settings()
