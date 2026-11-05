"""FaceAttend anti-spoofing API for the public attendance website."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent
MODEL_ROOT = ROOT / "Silent-Face-Anti-Spoofing"
if not MODEL_ROOT.exists():
    raise RuntimeError("The anti-spoofing model was not installed into this deployment.")

sys.path.insert(0, str(MODEL_ROOT))
from src.anti_spoof_predict import AntiSpoofPredict  # noqa: E402
from src.generate_patches import CropImage  # noqa: E402
from src.utility import parse_model_name  # noqa: E402

app = FastAPI(title="FaceAttend liveness service")
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "LIVENESS_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=os.getenv("LIVENESS_CORS_ORIGIN_REGEX", "").strip() or None,
    allow_methods=["POST"],
    allow_headers=["*"],
)

models = MODEL_ROOT / "resources" / "anti_spoof_models"
predictor = AntiSpoofPredict(0)
cropper = CropImage()


@app.get("/")
def root():
    """Small status response for opening the Vercel deployment URL directly."""
    return {
        "service": "FaceAttend liveness API",
        "ready": models.is_dir(),
        "health": "/health",
        "liveness": "/liveness",
    }


@app.get("/health")
def health():
    return {"ready": models.is_dir()}


@app.post("/liveness")
async def liveness(image: UploadFile = File(...)):
    """Return live=False for a photo/screen or when no usable face is found."""
    raw = await image.read()
    frame = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="The uploaded frame is not an image.")
    if not models.is_dir():
        raise HTTPException(status_code=503, detail="Anti-spoof model files are unavailable.")

    try:
        bbox = predictor.get_bbox(frame)
        prediction = np.zeros((1, 3))
        model_count = 0
        for model_name in models.iterdir():
            if not model_name.is_file():
                continue
            height, width, _, scale = parse_model_name(model_name.name)
            patch = cropper.crop(
                org_img=frame,
                bbox=bbox,
                scale=scale,
                out_w=width,
                out_h=height,
                crop=scale is not None,
            )
            prediction += predictor.predict(patch, str(model_name))
            model_count += 1
        if not model_count:
            raise RuntimeError("No anti-spoof model files were found.")
    except Exception as error:
        raise HTTPException(status_code=422, detail="Could not verify a live face.") from error

    label = int(np.argmax(prediction))
    score = float(prediction[0][label] / model_count)
    return {"live": label == 1, "score": round(score, 3)}
