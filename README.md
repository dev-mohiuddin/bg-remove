# AI Background Remover

Production-ready AI-powered background removal web application with pixel-perfect cutouts preserving fine details like hair and transparent fabrics.

## Tech Stack

| Layer      | Technology                         |
| ---------- | ---------------------------------- |
| Frontend   | Next.js 16 (App Router), Tailwind CSS v4 |
| Backend    | Python FastAPI, async task queue, SSE streaming |
| AI Model   | BiRefNet (SOTA segmentation) + ViTMatte (alpha matting) |
| Fallback   | rembg IS-Net (if BiRefNet ONNX unavailable) |
| Deployment | Vercel (frontend), Modal.com (backend GPU) |

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                    │
│  Upload → POST /api/remove-bg → SSE progress stream      │
│  → Download RGBA PNG → Magic Brush touch-up (Canvas)     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Backend (FastAPI)                      │
│                                                          │
│  POST /api/remove-bg      → submit async task            │
│  GET  /api/task/{id}/events → SSE progress stream        │
│  GET  /api/task/{id}/result → download RGBA PNG          │
│  POST /api/extract-mask   → extract alpha mask only      │
│  POST /api/composite      → apply edited mask → PNG      │
│                                                          │
│  Pipeline:                                               │
│    1. Preprocess (upscale small images)                  │
│    2. BiRefNet segmentation (tiled for 4K)               │
│    3. ViTMatte / closed-form alpha matting               │
│    4. Edge refinement (guided filter + morphology)       │
│    5. Composite → RGBA PNG                               │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Backend

```bash
cd backend
pip install -r requirements.txt

# Download BiRefNet ONNX model (recommended)
python download_models.py

uvicorn app.main:app --reload
# → http://localhost:8000
```

### Backend (GPU — for CPU-only local dev, swap `onnxruntime-gpu` for `onnxruntime`)

```bash
pip install onnxruntime  # instead of onnxruntime-gpu
```

## Environment Variables

### Frontend (`.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_ADSTERRA_SOCIAL_BAR_ID=YOUR_SOCIAL_BAR_ID
NEXT_PUBLIC_ADSTERRA_DIRECT_LINK_URL=YOUR_DIRECT_LINK_URL
```

### Backend

```env
BG_REMOVER_CORS_ORIGINS='["http://localhost:3000"]'
BG_REMOVER_MAX_FILE_SIZE_MB=25
BG_REMOVER_TILE_SIZE=1024
BG_REMOVER_TILE_OVERLAP=128
BG_REMOVER_USE_VITMATTE=true
BG_REMOVER_BIREFNET_ONNX_PATH=/path/to/birefnet.onnx
BG_REMOVER_VITMATTE_ONNX_PATH=/path/to/vitmatte.onnx
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET  | `/api/health` | Health check + model info |
| POST | `/api/remove-bg` | Submit async bg-removal job → `{task_id}` |
| POST | `/api/remove-bg-sync` | Legacy synchronous (blocking) |
| POST | `/api/extract-mask` | Submit mask-only extraction → `{task_id}` |
| GET  | `/api/task/{id}` | Poll task status (JSON) |
| GET  | `/api/task/{id}/events` | SSE stream of progress events |
| GET  | `/api/task/{id}/result` | Download RGBA PNG result |
| GET  | `/api/task/{id}/mask` | Download alpha mask PNG |
| POST | `/api/composite` | Composite original + edited mask → PNG |

## Deployment

### Frontend → Vercel

```bash
cd frontend
npx vercel --prod
```

### Backend → Modal.com

```bash
cd backend
pip install modal

# Upload BiRefNet ONNX to Modal volume
modal volume put birefnet-models birefnet.onnx /path/to/birefnet.onnx

modal deploy modal_deploy.py
```

## Project Structure

```
bg-remover/
├── frontend/
│   ├── src/
│   │   ├── app/            # Pages and layout
│   │   ├── components/     # UI components (Upload, Slider, MagicBrush, etc.)
│   │   └── lib/            # API client (async+SSE), ad helpers
│   └── ...config files
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI routes (async + SSE)
│   │   ├── processor.py    # Full pipeline (BiRefNet → matting → composite)
│   │   ├── matting.py      # Alpha matting (ViTMatte + closed-form)
│   │   ├── tiling.py       # Tiled inference for 4K images
│   │   ├── tasks.py        # Async task manager
│   │   ├── config.py       # Environment config
│   │   └── models/
│   │       └── birefnet.py # BiRefNet ONNX wrapper
│   ├── models/             # ONNX model files
│   ├── download_models.py  # Model download/export utility
│   ├── Dockerfile          # GPU container
│   ├── modal_deploy.py     # Serverless deployment
│   └── requirements.txt
└── README.md
```

## License

MIT
