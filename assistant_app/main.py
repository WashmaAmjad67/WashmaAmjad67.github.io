import asyncio
import base64
import json

import httpx
import os
import time
from collections import defaultdict, deque
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import db
from .config import DATA_DIR, IMAGE_MODEL, MODEL, STT_MODEL
from .provider import OllamaProvider, client, get_provider

app = FastAPI(title="Atlas desktop assistant")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])
db.initialize()
static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static), name="static")
(DATA_DIR / "images").mkdir(exist_ok=True)
app.mount("/images", StaticFiles(directory=DATA_DIR / "images"), name="images")
requests = defaultdict(deque)
locks = set()
provider = get_provider()


@app.middleware("http")
async def protect(request: Request, call_next):
    origin = request.headers.get("origin")
    if origin and origin not in ("http://127.0.0.1:8000", "http://localhost:8000"):
        return JSONResponse({"detail": "Untrusted origin."}, status_code=403)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if request.headers.get("x-atlas-client") != "desktop":
            return JSONResponse({"detail": "Missing desktop client header."}, status_code=403)
        key = request.client.host if request.client else "local"
        queue = requests[key]
        while queue and queue[0] < time.monotonic() - 60:
            queue.popleft()
        if len(queue) >= 60:
            return JSONResponse({"detail": "Too many requests. Please wait a minute."}, status_code=429)
        queue.append(time.monotonic())
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/")
def home():
    return FileResponse(static / "index.html")


@app.get("/api/status")
async def status():
    local = isinstance(provider, OllamaProvider)
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b") if local else MODEL
    ready = bool(os.getenv("OPENAI_API_KEY"))
    detail = "OpenAI key configured (access not yet verified)." if ready else "OpenAI key missing."
    if local:
        try:
            async with httpx.AsyncClient(timeout=2) as http:
                result = await http.get(os.getenv("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/tags")
                result.raise_for_status()
                ready = any(item.get("name") == model for item in result.json().get("models", []))
                detail = "Local model installed." if ready else f"Download your model: ollama pull {model}"
        except (httpx.HTTPError, ValueError):
            ready = False
            detail = "Ollama is not responding. Open Ollama, then refresh this page. Notes are available."
    return {
        "ai": ready,
        "provider": "ollama" if local else "openai",
        "model": model,
        "detail": detail,
        "storage": "SQLite on this machine",
    }


@app.get("/api/conversations")
def conversations():
    return db.rows("SELECT * FROM conversations ORDER BY updated_at DESC")


@app.post("/api/conversations")
def create_conversation():
    cid = str(uuid4())
    db.execute(
        "INSERT INTO conversations VALUES (:id,:title,:updated)", id=cid, title="New conversation", updated=db.now()
    )
    return {"id": cid}


def require_conversation(cid):
    if not db.rows("SELECT id FROM conversations WHERE id=:id", id=cid):
        raise HTTPException(404, "Conversation not found.")


@app.get("/api/conversations/{cid}/messages")
def messages(cid: str):
    require_conversation(cid)
    result = db.rows("SELECT * FROM messages WHERE conversation_id=:id ORDER BY created_at", id=cid)
    for row in result:
        row["sources"] = json.loads(row["sources"])
    return result


class Chat(BaseModel):
    text: str = Field(min_length=1, max_length=16000)
    research: bool = False


@app.post("/api/conversations/{cid}/chat")
async def chat(cid: str, body: Chat):
    require_conversation(cid)
    if not isinstance(provider, OllamaProvider):
        client()
    if cid in locks:
        raise HTTPException(409, "This conversation is already generating a reply.")
    locks.add(cid)
    history = messages(cid)
    db.save_message(cid, "user", body.text)
    if not history:
        db.execute("UPDATE conversations SET title=:title WHERE id=:id", id=cid, title=body.text[:70])

    async def events():
        answer, sources = "", []
        try:
            # Explicit, deterministic note commands avoid fictitious tool execution.
            if body.text.lower().strip() in ("save this as a note", "save this as a note."):
                previous = next((m["content"] for m in reversed(history) if m["role"] == "assistant"), None)
                if not previous:
                    yield encode({"type": "error", "text": "There is no assistant answer to save yet."})
                    return
                note_id = db.save_note(previous[:70], previous, ["chat"])
                answer = f"Saved note: {previous[:70]} (ID: {note_id})."
                yield encode({"type": "delta", "text": answer})
            else:
                context = [{"role": m["role"], "content": m["content"]} for m in history[-30:]]
                context.append({"role": "user", "content": body.text})
                async for event in provider.stream(context, body.research):
                    if event["type"] == "delta":
                        answer += event["text"]
                    elif event["type"] == "sources":
                        sources = event["sources"]
                    yield encode(event)
                if body.research and not sources:
                    yield encode(
                        {"type": "status", "text": "No cited sources were returned; this research is unverified."}
                    )
            db.save_message(cid, "assistant", answer, sources)
            yield encode({"type": "done"})
        except asyncio.CancelledError:
            if answer:
                db.save_message(cid, "assistant", answer + "\n\n[Interrupted]", sources)
            raise
        except Exception:
            yield encode(
                {
                    "type": "error",
                    "text": "The model request failed. For local mode, open Ollama and run ollama pull qwen2.5:1.5b. For OpenAI, check key, model access and billing. Research also needs Internet access.",
                }
            )
        finally:
            locks.discard(cid)

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def encode(event):
    return f"data: {json.dumps(event)}\n\n"


class Note(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=50000)
    tags: list[str] = Field(default_factory=list, max_length=20)


@app.get("/api/notes")
def notes(q: str = ""):
    if len(q) > 500:
        raise HTTPException(422, "Search is too long.")
    if q.strip():
        query = " AND ".join('"' + word.replace('"', '""') + '"' for word in q.split())
        result = db.rows(
            "SELECT n.* FROM notes n JOIN notes_fts f ON n.id=f.id WHERE notes_fts MATCH :q ORDER BY n.updated_at DESC LIMIT 100",
            q=query,
        )
    else:
        result = db.rows("SELECT * FROM notes ORDER BY updated_at DESC LIMIT 100")
    for row in result:
        row["tags"] = json.loads(row["tags"])
    return result


@app.post("/api/notes")
def create_note(body: Note):
    return {"id": db.save_note(body.title, body.body, body.tags)}


@app.put("/api/notes/{nid}")
def update_note(nid: str, body: Note):
    require_note(nid)
    db.save_note(body.title, body.body, body.tags, nid)
    return {"id": nid}


def require_note(nid):
    if not db.rows("SELECT id FROM notes WHERE id=:id", id=nid):
        raise HTTPException(404, "Note not found.")


@app.delete("/api/notes/{nid}")
def delete_note(nid: str, confirmed: bool = False):
    require_note(nid)
    if not confirmed:
        raise HTTPException(409, "Confirm deletion first.")
    with db.engine.begin() as conn:
        for table in ("notes", "notes_fts"):
            conn.execute(db.text(f"DELETE FROM {table} WHERE id=:id"), {"id": nid})
    return {"deleted": True}


class SceneRequest(BaseModel):
    request: str = Field(min_length=1, max_length=8000)
    style: str = Field(default="cinematic", max_length=200)
    aspect_ratio: str = Field(default="16:9", pattern=r"^(16:9|1:1|9:16)$")


@app.post("/api/scenes")
async def scene(body: SceneRequest):
    prompt = f"""Return JSON only, with string fields subject, setting, composition, lighting,
style, camera, aspect_ratio, image_prompt, negative_prompt. Build a rich scene from this request:
{body.model_dump_json()}"""
    try:
        if isinstance(provider, OllamaProvider):
            content = await provider.complete([{"role": "user", "content": prompt}], json_mode=True)
        else:
            result = await client().chat.completions.create(
                model=MODEL, messages=[{"role": "user", "content": prompt}], response_format={"type": "json_object"}
            )
            content = result.choices[0].message.content
        data = json.loads(content)
        required = {
            "subject",
            "setting",
            "composition",
            "lighting",
            "style",
            "camera",
            "aspect_ratio",
            "image_prompt",
            "negative_prompt",
        }
        if not required.issubset(data) or not all(isinstance(data[k], str) for k in required):
            raise ValueError("Invalid scene")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Scene generation failed. Check provider configuration.") from None
    sid = str(uuid4())
    db.execute(
        "INSERT INTO scenes VALUES (:id,:request,:result,:created)",
        id=sid,
        request=body.request,
        result=json.dumps(data),
        created=db.now(),
    )
    return {"id": sid, **data}


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)


@app.post("/api/images")
async def image(body: ImageRequest):
    if isinstance(provider, OllamaProvider):
        raise HTTPException(
            503, "Local image generation is not configured. Copy the scene prompt into your image tool."
        )
    try:
        result = await client().images.generate(model=IMAGE_MODEL, prompt=body.prompt, size="1024x1024")
        encoded = result.data[0].b64_json
        if not encoded:
            raise ValueError("Missing image")
        name = f"image-{uuid4()}.png"
        (DATA_DIR / "images" / name).write_bytes(base64.b64decode(encoded, validate=True))
        return {"url": f"/images/{name}"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Image generation failed. Check model access and billing.") from None


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    data = await audio.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, "Recording must be under 20 MB.")
    if not data:
        raise HTTPException(422, "Recording is empty.")
    try:
        if isinstance(provider, OllamaProvider):
            return {"text": await asyncio.to_thread(local_transcribe, data)}
        result = await client().audio.transcriptions.create(
            model=STT_MODEL, file=(audio.filename or "recording.webm", data, audio.content_type)
        )
        return {"text": result.text}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Transcription failed. Check audio format and provider access.") from None


def local_transcribe(data):
    import tempfile

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise HTTPException(503, "Install local voice support: python -m pip install faster-whisper") from None
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as file:
        path = file.name
        file.write(data)
    try:
        model = WhisperModel(os.getenv("LOCAL_STT_MODEL", "base"), device="cpu", compute_type="int8")
        segments, _ = model.transcribe(path)
        return " ".join(segment.text.strip() for segment in segments)
    finally:
        os.unlink(path)
