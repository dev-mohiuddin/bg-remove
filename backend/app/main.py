

import logging
import time

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import settings
from .processor import remove_background

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Background Remover API",
    description="Production-grade background removal powered by IS-Net",
    version="1.0.0",
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


@app.get("/api/health")
async def health_check():
    
    return {"status": "healthy", "model": settings.model_name}


@app.post("/api/remove-bg")
async def remove_bg(file: UploadFile = File(...)):
    

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
            f"Allowed: JPEG, PNG, WebP.",
        )


    image_bytes = await file.read()
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb} MB.",
        )

    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")


    logger.info(
        "Processing image: %s (%d bytes, %s)",
        file.filename,
        len(image_bytes),
        file.content_type,
    )
    start = time.time()

    try:
        result_bytes = remove_background(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Background removal failed")
        raise HTTPException(
            status_code=500,
            detail="Background removal failed. Please try again.",
        )

    elapsed = time.time() - start
    logger.info("Processing complete in %.2fs (%d bytes output)", elapsed, len(result_bytes))

    return Response(
        content=result_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="bg-removed-{file.filename}.png"',
            "X-Processing-Time": f"{elapsed:.2f}s",
        },
    )
