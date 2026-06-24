"""
FastAPI application — AI Background Remover API.

Endpoints:
  GET  /api/health              — health check
  POST /api/remove-bg           — async submit, returns task_id
  POST /api/remove-bg-sync      — legacy synchronous (kept for compatibility)
  POST /api/extract-mask        — async submit mask-only extraction
  GET  /api/task/{task_id}      — poll task status (JSON)
  GET  /api/task/{task_id}/events — SSE stream of progress events
  GET  /api/task/{task_id}/result — download the RGBA PNG result
  GET  /api/task/{task_id}/mask  — download the alpha mask PNG
  POST /api/composite           — client-side mask + original -> server composite
"""

import asyncio
import json
import logging
import time

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse

from .config import settings
from .processor import process_image
from .tasks import store, submit_task, submit_mask_task

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Background Remover API",
    description="Production-grade background removal powered by BiRefNet + ViTMatte",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/jpg",
}
MAX_FILE_SIZE = settings.max_file_size_mb * 1024 * 1024


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    from .models import birefnet
    return {
        "status": "healthy",
        "model": "BiRefNet" if birefnet.is_available() else settings.model_name,
        "vitmatte": settings.use_vitmatte,
    }


# ---------------------------------------------------------------------------
# Async submit + SSE streaming
# ---------------------------------------------------------------------------

@app.post("/api/remove-bg")
async def remove_bg_async(file: UploadFile = File(...)):
    """Submit a background-removal job. Returns a task_id immediately."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}.")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {settings.max_file_size_mb} MB.")

    task = submit_task(image_bytes, file.filename or "image.png")
    logger.info("Submitted task %s for %s (%d bytes)", task.id, file.filename, len(image_bytes))
    return {"task_id": task.id, "status": "pending"}


@app.post("/api/extract-mask")
async def extract_mask(file: UploadFile = File(...)):
    """Submit a mask-only extraction job (for the frontend touch-up tool)."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}.")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {settings.max_file_size_mb} MB.")

    task = submit_mask_task(image_bytes)
    return {"task_id": task.id, "status": "pending"}


@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """Poll task status."""
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {
        "task_id": task.id,
        "status": task.status.value,
        "stage": task.stage,
        "progress": task.progress,
        "error": task.error,
    }


@app.get("/api/task/{task_id}/events")
async def task_events(task_id: str):
    """Server-Sent Events stream for real-time progress updates."""
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    async def event_generator():
        while True:
            t = store.get(task_id)
            if t is None:
                yield f"event: error\ndata: {json.dumps({'error': 'Task lost'})}\n\n"
                break

            events = t.drain_events()
            for evt in events:
                yield f"data: {json.dumps(evt)}\n\n"

            if t.status.value in ("done", "error"):
                final = {
                    "stage": t.stage,
                    "progress": t.progress,
                    "status": t.status.value,
                    "error": t.error,
                }
                yield f"event: complete\ndata: {json.dumps(final)}\n\n"
                break

            await asyncio.sleep(0.15)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/task/{task_id}/result")
async def get_task_result(task_id: str):
    """Download the RGBA PNG result once the task is done."""
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    if task.status.value != "done":
        raise HTTPException(status_code=409, detail=f"Task not ready: {task.status.value}")
    if task.result is None:
        raise HTTPException(status_code=500, detail="Result missing.")

    return Response(
        content=task.result,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="bg-removed.png"'},
    )


@app.get("/api/task/{task_id}/mask")
async def get_task_mask(task_id: str):
    """Download the alpha mask PNG."""
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    if task.status.value != "done":
        raise HTTPException(status_code=409, detail=f"Task not ready: {task.status.value}")
    if task.mask_result is None:
        raise HTTPException(status_code=404, detail="No mask for this task.")
    return Response(content=task.mask_result, media_type="image/png")


# ---------------------------------------------------------------------------
# Client-side composite: apply an edited mask to the original image
# ---------------------------------------------------------------------------

@app.post("/api/composite")
async def composite_endpoint(
    file: UploadFile = File(...),
    mask: UploadFile = File(...),
):
    """
    Composite an original image with a user-edited alpha mask.
    Used after the Magic Brush tool modifies the mask on the frontend.
    """
    import io as _io
    import numpy as _np
    from PIL import Image as _Image

    image_bytes = await file.read()
    mask_bytes = await mask.read()

    try:
        image = _Image.open(_io.BytesIO(image_bytes)).convert("RGBA")
        mask_img = _Image.open(_io.BytesIO(mask_bytes)).convert("L")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image/mask: {exc}")

    if mask_img.size != image.size:
        mask_img = mask_img.resize(image.size, _Image.BILINEAR)

    image.putalpha(mask_img)
    buf = _io.BytesIO()
    image.save(buf, format="PNG", optimize=False, compress_level=1)
    return Response(content=buf.getvalue(), media_type="image/png")


# ---------------------------------------------------------------------------
# Legacy synchronous endpoint (kept for backward compatibility)
# ---------------------------------------------------------------------------

@app.post("/api/remove-bg-sync")
async def remove_bg_sync(file: UploadFile = File(...)):
    """Synchronous background removal (blocking). Kept for compatibility."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}.")

    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {settings.max_file_size_mb} MB.")

    start = time.time()
    try:
        result_bytes = process_image(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Background removal failed")
        raise HTTPException(status_code=500, detail="Background removal failed.")

    elapsed = time.time() - start
    return Response(
        content=result_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="bg-removed.png"',
            "X-Processing-Time": f"{elapsed:.2f}s",
        },
    )
