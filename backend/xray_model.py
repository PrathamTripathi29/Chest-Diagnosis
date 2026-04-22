import io
from typing import Dict, List, Tuple

import cv2
import numpy as np
import torch
import torchxrayvision as xrv
from PIL import Image
from torchvision import transforms

LABELS = [
    "Cardiomegaly",
    "Edema",
    "Pneumonia",
    "Pleural Effusion",
]

THRESHOLD = 0.4
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_model():
    model = xrv.models.DenseNet(weights="densenet121-res224-all")
    model.to(DEVICE)
    model.eval()
    print(f"Model loaded on {DEVICE}")
    return model


def get_transforms():
    return transforms.Compose([
        xrv.datasets.XRayCenterCrop(),
        xrv.datasets.XRayResizer(224),
    ])


def enhance_xray(image_array: np.ndarray) -> np.ndarray:
    """
    Apply noise removal and contrast enhancement to X-ray.

    image_array: numpy array of shape (H, W) grayscale, values 0-255
    returns:     enhanced numpy array same shape
    """
    # Convert to uint8 for OpenCV processing
    img_uint8 = image_array.astype(np.uint8)

    # Step 1 — Noise removal using Gaussian blur
    # kernel size (3,3) is small — removes noise without blurring edges
    # sigmaX=0 means OpenCV calculates sigma from kernel size
    denoised = cv2.GaussianBlur(img_uint8, (3, 3), sigmaX=0)

    # Step 2 — CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # clipLimit=2.0 prevents over-amplification of noise
    # tileGridSize=(8,8) divides image into 8x8 regions
    # each region gets its own histogram equalization
    # this enhances local contrast without washing out the whole image
    clahe   = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(denoised)

    return enhanced.astype(np.float32)


def _preprocess_image(image_bytes: bytes) -> torch.Tensor:
    # Load image
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_array = np.array(image).astype(np.float32)

    # Convert to grayscale for enhancement
    # weighted average matches human perception of luminance
    gray = (0.299 * image_array[:,:,0] +
            0.587 * image_array[:,:,1] +
            0.114 * image_array[:,:,2])

    # Apply noise removal and contrast enhancement
    enhanced = enhance_xray(gray)

    # Normalize to TorchXRayVision's expected range [-1024, 1024]
    enhanced_normalized = xrv.datasets.normalize(enhanced, maxval=255)

    # Add channel dimension → shape (1, H, W)
    enhanced_normalized = enhanced_normalized[None, ...]

    # Apply center crop and resize
    transform = get_transforms()
    processed = transform(enhanced_normalized)

    # Add batch dimension → shape (1, 1, 224, 224)
    tensor = torch.from_numpy(processed).unsqueeze(0).to(DEVICE).float()
    return tensor


def _extract_target_scores(model, probabilities):
    pathology_to_index = {
        name: idx for idx, name in enumerate(model.pathologies)
    }

    def get(label):
        idx = pathology_to_index.get(label)
        return float(probabilities[idx]) if idx is not None else 0.0

    scores = {}
    scores["Cardiomegaly"]    = get("Cardiomegaly")
    scores["Edema"]           = get("Edema")
    scores["Pneumonia"]       = max([
        get("Pneumonia"), get("Lung_Opacity"),
        get("Infiltration"), get("Consolidation")
    ])
    scores["Pleural Effusion"] = get("Effusion")

    return scores


def predict(model, image_bytes: bytes):
    x = _preprocess_image(image_bytes)

    with torch.no_grad():
        logits       = model(x)
        probabilities = torch.sigmoid(logits).squeeze(0).cpu().numpy()

    target_scores = _extract_target_scores(model, probabilities)

    sorted_items = sorted(
        target_scores.items(), key=lambda x: x[1], reverse=True
    )

    results = []
    top_label, top_score = sorted_items[0]

    THRESHOLDS = {
        "Cardiomegaly":    0.5,
        "Edema":           0.55,
        "Pneumonia":       0.6,
        "Pleural Effusion": 0.55,
    }

    MIN_CONFIDENCE = 0.5
    MIN_MARGIN     = 0.08

    if top_score < MIN_CONFIDENCE:
        return [{
            "condition":   "No Finding",
            "confidence":  round((1 - top_score) * 100, 1),
            "probability": float(1 - top_score),
            "label_index": -1
        }], probabilities

    results.append({
        "condition":   top_label,
        "confidence":  round(top_score * 100, 1),
        "probability": float(top_score),
        "label_index": 0
    })

    for label, score in sorted_items[1:]:
        if len(results) >= 2:
            break
        if score < THRESHOLDS.get(label, 0.5):
            continue
        if abs(score - top_score) < MIN_MARGIN:
            continue
        results.append({
            "condition":   label,
            "confidence":  round(score * 100, 1),
            "probability": float(score),
            "label_index": len(results)
        })

    return results, probabilities