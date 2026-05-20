import httpx

from app.external_metadata import CandidateNormalizer, LastFmService, MusicBrainzService


def test_musicbrainz_search_lookup_and_relationship_normalization() -> None:
    seen_headers: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.append(request.headers["User-Agent"])
        if request.url.path.endswith("/artist/mbid-radiohead"):
            return httpx.Response(
                200,
                json={
                    "id": "mbid-radiohead",
                    "name": "Radiohead",
                    "type": "Group",
                    "aliases": [{"name": "On A Friday"}],
                    "relations": [
                        {
                            "type": "member of band",
                            "artist": {"id": "mbid-thom", "name": "Thom Yorke"},
                        },
                        {
                            "type": "collaboration",
                            "artist": {"id": "mbid-smile", "name": "The Smile"},
                        },
                        {
                            "target-type": "url",
                            "url": {"resource": "https://radiohead.com"},
                        },
                    ],
                },
            )
        return httpx.Response(
            200,
            json={"artists": [{"id": "mbid-radiohead", "name": "Radiohead", "type": "Group"}]},
        )

    service = MusicBrainzService(http_client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)

    search = service.search_artist_by_name("Radiohead")
    lookup = service.lookup_artist_by_mbid("mbid-radiohead")
    relationships = service.fetch_artist_relationships("mbid-radiohead")

    assert search[0]["mbid"] == "mbid-radiohead"
    assert lookup["aliases"] == ["On A Friday"]
    assert relationships["members"] == [{"mbid": "mbid-thom", "name": "Thom Yorke", "type": "member of band"}]
    assert relationships["collaborations"] == [{"mbid": "mbid-smile", "name": "The Smile", "type": "collaboration"}]
    assert relationships["urls"] == ["https://radiohead.com"]
    assert all("GrooveGraph" in header for header in seen_headers)


def test_lastfm_normalizes_similar_artists_tracks_and_tags() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        method = request.url.params["method"]
        if method == "artist.getSimilar":
            return httpx.Response(
                200,
                json={"similarartists": {"artist": [{"name": "Pixies", "mbid": "pixies-mbid", "match": "0.93"}]}},
            )
        if method == "track.getSimilar":
            return httpx.Response(
                200,
                json={
                    "similartracks": {
                        "track": [{"name": "Debaser", "artist": {"name": "Pixies"}, "match": "0.88"}]
                    }
                },
            )
        return httpx.Response(200, json={"similartags": {"tag": [{"name": "alt-rock"}]}})

    service = LastFmService(http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    artists = service.artist_get_similar("Radiohead")
    tracks = service.track_get_similar("Radiohead", "Airbag")
    tags = service.tag_get_similar("alternative")

    assert artists[0].name == "Pixies"
    assert artists[0].confidence == 0.93
    assert tracks[0].name == "Debaser"
    assert tracks[0].artist_name == "Pixies"
    assert tags[0].reason == "Last.fm tag similarity from alternative"


def test_candidate_normalizer_merges_duplicates() -> None:
    normalizer = CandidateNormalizer()
    first = normalizer.from_lastfm_artist({"name": "Pixies", "match": "0.6"}, seed={"kind": "artist", "name": "A"})
    second = normalizer.from_lastfm_artist({"name": "pixies", "match": "0.9"}, seed={"kind": "artist", "name": "B"})

    merged = normalizer.merge_duplicates([first, second])

    assert len(merged) == 1
    assert merged[0].confidence == 0.9
    assert len(merged[0].seed_references) == 2
