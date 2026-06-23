# AI Background Remover

Production-ready AI-powered background removal web application with pixel-perfect cutouts preserving fine details like hair and transparent fabrics.

## Tech Stack

| Layer      | Technology                         |
| ---------- | ---------------------------------- |
| Frontend   | Next.js 16 (App Router), Tailwind CSS v4 |
| Backend    | Python FastAPI, rembg (IS-Net)     |
| AI Model   | isnet-general-use (ONNX)           |
| Deployment | Vercel (frontend), Modal.com (backend GPU) |

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
BG_REMOVER_MODEL_NAME=isnet-general-use
BG_REMOVER_MAX_FILE_SIZE_MB=20
```

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
modal deploy modal_deploy.py
```

## Project Structure

```
bg-remover/
├── frontend/               # Next.js App Router
│   ├── src/
│   │   ├── app/            # Pages and layout
│   │   ├── components/     # UI components
│   │   └── lib/            # API client, ad helpers
│   └── ...config files
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI routes
│   │   ├── processor.py    # rembg processing
│   │   └── config.py       # Environment config
│   ├── Dockerfile          # GPU container
│   ├── modal_deploy.py     # Serverless deployment
│   └── requirements.txt
└── README.md
```

## License

MIT
