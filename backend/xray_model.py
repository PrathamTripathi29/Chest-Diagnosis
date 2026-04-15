# model.py
import io
from typing import Dict, List, Tuple

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
    """
    Loads the built-in TorchXRayVision pretrained DenseNet.
    """
    model = xrv.models.DenseNet(weights="densenet121-res224-all")
    model.to(DEVICE)
    model.eval()
    print(f"Built-in XRV model loaded on {DEVICE}")
    return model


def get_transforms():
    """
    TorchXRayVision preprocessing pipeline for chest X-rays.
    """
    return transforms.Compose(
        [
            xrv.datasets.XRayCenterCrop(),
            xrv.datasets.XRayResizer(224),
        ]
    )


def _preprocess_image(image_bytes: bytes) -> torch.Tensor:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = np.array(image).astype(np.float32)

    # Normalize the same way TorchXRayVision examples do
    image = xrv.datasets.normalize(image, 255)

    # Convert RGB -> single channel, then apply crop/resizing
    image = image.mean(2)[None, ...]

    transform = get_transforms()
    image = transform(image)

    tensor = torch.from_numpy(image).unsqueeze(0).to(DEVICE).float()
    return tensor


def _extract_target_scores(model, probabilities):
    pathology_to_index = {
        name: idx for idx, name in enumerate(model.pathologies)
    }

    def get(label):
        idx = pathology_to_index.get(label)
        return float(probabilities[idx]) if idx is not None else 0.0

    scores = {}

    # Direct mappings
    scores["Cardiomegaly"] = get("Cardiomegaly")
    scores["Edema"] = get("Edema")

    # 🔥 Smart Pneumonia mapping
    pneumonia_related = [
        get("Pneumonia"),
        get("Lung_Opacity"),
        get("Infiltration"),
        get("Consolidation"),
    ]
    scores["Pneumonia"] = max(pneumonia_related)

    # 🔥 Effusion mapping
    scores["Pleural Effusion"] = get("Effusion")

    return scores

def predict(model, image_bytes: bytes) -> Tuple[List[dict], np.ndarray]:
    """
    Returns:
      - filtered prediction list for only the 4 target ailments
      - raw probability vector from the model
    """
    tensor = _preprocess_image(image_bytes)

    with torch.no_grad():
        logits = model(tensor)
        probabilities = torch.sigmoid(logits).squeeze(0).detach().cpu().numpy()

    target_scores = _extract_target_scores(model, probabilities)

    results = []
    for i, label in enumerate(LABELS):
        prob_value = target_scores[label]
        if prob_value >= THRESHOLD:
            results.append(
                {
                    "condition": label,
                    "confidence": round(prob_value * 100, 1),
                    "probability": prob_value,
                    "label_index": i,
                }
            )

    results.sort(key=lambda x: x["confidence"], reverse=True)

    # Fallback so the frontend/report code does not break when nothing crosses the threshold
    if not results:
        best_prob = max(target_scores.values()) if target_scores else 0.0
        results = [
            {
                "condition": "No Finding",
                "confidence": round((1.0 - best_prob) * 100, 1),
                "probability": float(1.0 - best_prob),
                "label_index": -1,
            }
        ]

    return results, probabilities