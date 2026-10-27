import json
import os
import tempfile

os.environ["ASSISTANT_DATA_DIR"] = tempfile.mkdtemp()
os.environ["AI_PROVIDER"] = "ollama"

from fastapi.testclient import TestClient

from assistant_app import main
from assistant_app.provider import valid_sources

client = TestClient(main.app, headers={"X-Atlas-Client": "desktop"})


def test_notes_crud_search_confirmation():
    result = client.post(
        "/api/notes", json={"title": "Orchid plan", "body": "Water the orchid weekly", "tags": ["garden"]}
    )
    assert result.status_code == 200
    nid = result.json()["id"]
    assert client.get("/api/notes?q=orchid").json()[0]["id"] == nid
    assert (
        client.put("/api/notes/" + nid, json={"title": "Cactus", "body": "Dry soil", "tags": ["plant"]}).status_code
        == 200
    )
    assert client.get("/api/notes?q=orchid").json() == []
    assert client.get("/api/notes?q=plant").json()[0]["id"] == nid
    assert client.delete("/api/notes/" + nid).status_code == 409
    assert client.delete("/api/notes/" + nid + "?confirmed=true").json()["deleted"]
    assert client.get("/api/notes?q=plant").json() == []
    assert client.put("/api/notes/" + nid, json={"title": "x", "body": "x"}).status_code == 404


class FakeProvider:
    async def stream(self, messages, research=False):
        assert messages[-1]["content"] == "Hello Atlas"
        yield {"type": "delta", "text": "Hello "}
        yield {"type": "delta", "text": "friend."}
        yield {"type": "sources", "sources": [{"title": "Example", "url": "https://example.com"}]}


def test_stream_persistence_and_save_note(monkeypatch):
    monkeypatch.setattr(main, "provider", FakeProvider())
    monkeypatch.setattr(main, "client", lambda: None)
    cid = client.post("/api/conversations").json()["id"]
    response = client.post(f"/api/conversations/{cid}/chat", json={"text": "Hello Atlas"})
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert events[-1]["type"] == "done"
    history = client.get(f"/api/conversations/{cid}/messages").json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[-1]["content"] == "Hello friend."
    assert history[-1]["sources"][0]["url"] == "https://example.com"
    response = client.post(f"/api/conversations/{cid}/chat", json={"text": "save this as a note"})
    assert "Saved note" in response.text
    assert client.get("/api/notes?q=friend").json()


def test_scene_validation(monkeypatch):
    class SceneProvider(main.OllamaProvider):
        async def complete(self, messages, json_mode=False):
            assert json_mode
            return json.dumps(
                {
                    k: "A cinematic forest"
                    for k in [
                        "subject",
                        "setting",
                        "composition",
                        "lighting",
                        "style",
                        "camera",
                        "aspect_ratio",
                        "image_prompt",
                        "negative_prompt",
                    ]
                }
            )

    monkeypatch.setattr(main, "provider", SceneProvider())
    result = client.post("/api/scenes", json={"request": "forest"})
    assert result.status_code == 200
    assert result.json()["image_prompt"] == "A cinematic forest"
    assert client.post("/api/scenes", json={"request": ""}).status_code == 422
    assert client.post("/api/scenes", json={"request": "forest", "aspect_ratio": "invalid"}).status_code == 422


def test_provider_failure(monkeypatch):
    class BrokenProvider:
        async def stream(self, messages, research=False):
            raise RuntimeError("secret-provider-detail")
            yield

    monkeypatch.setattr(main, "provider", BrokenProvider())
    monkeypatch.setattr(main, "client", lambda: None)
    cid = client.post("/api/conversations").json()["id"]
    response = client.post(f"/api/conversations/{cid}/chat", json={"text": "hello"})
    assert '"type": "error"' in response.text
    assert "secret-provider-detail" not in response.text
    assert len(client.get(f"/api/conversations/{cid}/messages").json()) == 1
    assert cid not in main.locks


def test_security_and_errors():
    assert client.post("/api/notes", json={"title": "", "body": "x"}).status_code == 422
    assert client.get("/api/conversations/not-real/messages").status_code == 404
    assert client.post("/api/conversations", headers={"origin": "https://evil.example"}).status_code == 403
    assert TestClient(main.app).post("/api/conversations").status_code == 403
    assert client.get("/images/assistant.db").status_code == 404
    assert client.post("/api/transcribe", files={"audio": ("empty.webm", b"", "audio/webm")}).status_code == 422
    assert client.post("/api/images", json={"prompt": "forest"}).status_code == 503


def test_citation_policy():
    assert valid_sources(
        [
            {"url": "javascript:alert(1)"},
            {"url": "https://user:password@example.com"},
            {"url": "https://example.com", "title": "Example"},
            {"url": "https://example.com"},
        ]
    ) == [{"url": "https://example.com", "title": "example.com"}]


def test_research_reads_returned_pages(monkeypatch):
    import asyncio

    from assistant_app import research

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "query": {
                    "pages": {
                        "1": {
                            "title": "One",
                            "fullurl": "https://en.wikipedia.org/wiki/One",
                            "extract": "First source text",
                        },
                        "2": {
                            "title": "Two",
                            "fullurl": "https://en.wikipedia.org/wiki/Two",
                            "extract": "Second source text",
                        },
                    }
                }
            }

    async def get(self, url, **kwargs):
        assert url == "https://en.wikipedia.org/w/api.php"
        assert kwargs["params"]["gsrlimit"] == 3
        return Response()

    monkeypatch.setattr(research.httpx.AsyncClient, "get", get)
    result = asyncio.run(research.research("topic"))
    assert len(result) == 2
    assert result[0]["text"] == "First source text"
