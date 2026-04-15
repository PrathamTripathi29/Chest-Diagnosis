import io
import base64

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
import torchxrayvision as xrv


class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, inputs, output):
            if isinstance(output, tuple):
                output = output[0]

            # Clone to avoid inplace autograd issues in TorchXRayVision
            output = output.clone()
            self.activations = output.detach()

            if output.requires_grad:
                output.register_hook(self._save_gradients)

            return output

        self.target_layer.register_forward_hook(forward_hook)

    def _save_gradients(self, grad):
        self.gradients = grad.detach()

    def generate(self, image_tensor, class_idx):
        self.model.eval()
        self.gradients = None
        self.activations = None

        image_tensor = image_tensor.clone().requires_grad_(True)

        output = self.model(image_tensor)
        self.model.zero_grad(set_to_none=True)

        class_score = output[0, class_idx]
        class_score.backward()

        if self.gradients is None or self.activations is None:
            raise RuntimeError("Failed to capture Grad-CAM gradients or activations.")

        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = F.relu(cam)

        cam = F.interpolate(
            cam,
            size=(224, 224),
            mode="bilinear",
            align_corners=False,
        )

        cam = cam.squeeze().cpu().numpy()
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        return cam

    def overlay_on_image(self, original_image_bytes, cam):
        image = Image.open(io.BytesIO(original_image_bytes)).convert("RGB")
        image = image.resize((224, 224))
        image_array = np.array(image)

        heatmap = np.uint8(255 * cam)
        heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

        overlay = (0.6 * image_array + 0.4 * heatmap_colored).astype(np.uint8)

        overlay_image = Image.fromarray(overlay)
        buffer = io.BytesIO()
        overlay_image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")


def _preprocess_image(image_bytes, device):
    from xray_model import get_transforms

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = np.array(image).astype(np.float32)

    image = xrv.datasets.normalize(image, 255)
    image = image.mean(2)[None, ...]

    transform = get_transforms()
    image = transform(image)

    return torch.from_numpy(image).unsqueeze(0).to(device).float()


def generate_gradcam(model, image_bytes, predictions):
    device = next(model.parameters()).device

    target_layer = model.features.norm5
    gradcam = GradCAM(model, target_layer)

    image_tensor = _preprocess_image(image_bytes, device)

    pathology_to_index = {
        name: idx for idx, name in enumerate(model.pathologies)
    }

    heatmaps = {}

    for pred in predictions:
        condition = pred["condition"]

        if condition == "No Finding":
            continue

        # 🔥 FIX 1: Correct label mapping
        if condition == "Pleural Effusion":
            class_idx = pathology_to_index.get("Effusion")

        elif condition == "Pneumonia":
            # 🔥 FIX 2: Use strongest contributing pathology
            candidates = ["Pneumonia", "Lung_Opacity", "Infiltration", "Consolidation"]

            best_label = None
            best_score = -1

            for label in candidates:
                idx = pathology_to_index.get(label)
                if idx is not None:
                    score = model(image_tensor)[0, idx].item()
                    if score > best_score:
                        best_score = score
                        best_label = label

            class_idx = pathology_to_index.get(best_label)

        else:
            class_idx = pathology_to_index.get(condition)

        if class_idx is None:
            continue

        cam = gradcam.generate(image_tensor, class_idx)

        # 🔥 FIX 3: Boost weak heatmaps
        cam = np.power(cam, 0.4)
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)

        heatmaps[condition] = gradcam.overlay_on_image(image_bytes, cam)

    return heatmaps