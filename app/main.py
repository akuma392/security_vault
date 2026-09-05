import uuid
import os
import mimetypes
import aiofiles
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.config import STORAGE_DIR, BASE_DIR
from app.crypto import generate_key, encrypt_data, decrypt_data
from app.database import init_db, save_file_record, get_file_record, increment_download, delete_file_record
from app.janitor import cleanup_loop
import asyncio

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()

app = FastAPI(title="Secure File Vault", lifespan=lifespan)
app.mount("/ui", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/")
def redirect_to_ui():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    max_downloads: int = Form(1),
    expires_in_seconds: int = Form(86400),
    view_mode: str = Form("download"),     # "download" or "view_once"
    view_duration: int = Form(10)          # seconds (5, 10, 30, etc.)
):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    key = generate_key()
    encrypted_blob = encrypt_data(file_bytes, key)

    file_id = str(uuid.uuid4())
    storage_name = f"{file_id}.enc"
    storage_path = STORAGE_DIR / storage_name

    async with aiofiles.open(storage_path, "wb") as f:
        await f.write(encrypted_blob)

    # Force 1-time access if in view-once mode
    actual_max = 1 if view_mode == "view_once" else max_downloads

    save_file_record(
        file_id=file_id,
        original_name=file.filename,
        size=len(file_bytes),
        storage_name=storage_name,
        max_downloads=actual_max,
        expires_in=expires_in_seconds,
        view_mode=view_mode,
        view_duration=view_duration
    )

    return {
        "file_id": file_id,
        "key": key,
        "filename": file.filename,
        "view_mode": view_mode,
        "view_duration": view_duration
    }

@app.get("/api/meta/{file_id}")
def fetch_metadata(file_id: str):
    record = get_file_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File expired, already viewed, or deleted.")
    return {
        "filename": record["original_filename"],
        "size": record["file_size"],
        "downloads_left": record["max_downloads"] - record["download_count"],
        "view_mode": record["view_mode"],
        "view_duration": record["view_duration"]
    }

@app.post("/api/download/{file_id}")
async def access_file(file_id: str, key: str = Form(...)):
    record = get_file_record(file_id)
    if not record:
        raise HTTPException(status_code=404, detail="File has expired or has already been viewed.")

    storage_path = STORAGE_DIR / record["storage_filename"]
    if not storage_path.exists():
        raise HTTPException(status_code=404, detail="Encrypted payload not found on disk.")

    async with aiofiles.open(storage_path, "rb") as f:
        encrypted_bytes = await f.read()

    try:
        decrypted_bytes = decrypt_data(encrypted_bytes, key)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid decryption key or corrupted payload.")

    is_view_once = record["view_mode"] == "view_once"

    # Burn from server immediately if view_once or last download
    if is_view_once or (record["download_count"] + 1 >= record["max_downloads"]):
        try:
            os.remove(storage_path)
        except OSError:
            pass
        delete_file_record(file_id)
    else:
        increment_download(file_id)

    # Detect MIME type (image, text, pdf, etc.)
    mime_type, _ = mimetypes.guess_type(record["original_filename"])
    if not mime_type:
        mime_type = "application/octet-stream"

    headers = {}
    if not is_view_once:
        headers["Content-Disposition"] = f'attachment; filename="{record["original_filename"]}"'

    return Response(content=decrypted_bytes, media_type=mime_type, headers=headers)