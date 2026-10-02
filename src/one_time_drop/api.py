from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from .store import DropStore

load_dotenv()
MAX_BYTES = int(os.getenv("DROP_MAX_BYTES", "10485760"))
TTL_SECONDS = int(os.getenv("DROP_TTL_SECONDS", "600"))
DATA_DIR = Path(os.getenv("DROP_DATA_DIR", "./data"))


def _remove_file(path: Path) -> None:
    path.unlink(missing_ok=True)


def create_app(store: DropStore | None = None) -> FastAPI:
    drop_store = store or DropStore(DATA_DIR)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        drop_store.prune_expired()
        yield

    app = FastAPI(title="One-Time File Drop", version="1.0.0", lifespan=lifespan)

    @app.get("/health", tags=["service"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/drops", status_code=201, tags=["files"])
    async def upload(request: Request, file: UploadFile = File(...)) -> dict[str, object]:
        safe_name = (file.filename or "download.bin").replace("\\", "/").split("/")[-1].strip() or "download.bin"
        token = secrets.token_urlsafe(32)
        destination = drop_store.data_dir / f"{token}.blob"
        written = 0
        try:
            with destination.open("wb") as output:
                while chunk := await file.read(64 * 1024):
                    written += len(chunk)
                    if written > MAX_BYTES:
                        raise HTTPException(status_code=413, detail=f"file exceeds {MAX_BYTES} byte limit")
                    output.write(chunk)
            drop = drop_store.create(token, destination, safe_name, TTL_SECONDS)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await file.close()
        return {"token": drop.token, "filename": drop.filename, "size_bytes": written,
                "expires_at": drop.expires_at, "download_url": str(request.url_for("download", token=drop.token))}

    @app.get("/d/{token}", name="download", tags=["files"])
    def download(token: str) -> FileResponse:
        drop = drop_store.consume(token)
        if drop is None:
            raise HTTPException(status_code=404, detail="link is invalid, expired, or already used")
        return FileResponse(drop.path, filename=drop.filename,
                            background=BackgroundTask(_remove_file, drop.path))

    return app


app = create_app()
