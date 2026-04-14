import torch
import torch.nn.functional as F
import numpy as np
import cv2
from PIL import Image
import io
import base64


class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach().clone()

        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach().clone()

        self.target_layer.register_forward_hook(forward_hook)
        self.target_layer.register_full_backward_hook(backward_hook)

    def generate(self, image_tensor, class_idx):
        self.model.eval()
        image_tensor = image_tensor.clone().requires_grad_(True)
        output = self.model(image_tensor)
        self.model.zero_grad()
        class_score = output[0, class_idx]
        class_score.backward()
        gradients = self.gradients
        activations = self.activations
        weights = gradients.mean(dim=(2, 3), keepdim=True)
        cam = (weights * activations).sum(dim=1, keepdim=True)
        cam = F.relu(cam)
        cam = F.interpolate(
            cam, size=(224, 224),
            mode='bilinear', align_corners=False
        )
        cam = cam.squeeze().cpu().numpy()
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        return cam

    def overlay_on_image(self, original_image_bytes, cam):
        image = Image.open(io.BytesIO(original_image_bytes))
        image = image.convert('RGB')
        image = image.resize((224, 224))
        image_array = np.array(image)
        heatmap = np.uint8(255 * cam)
        heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
        overlay = (0.6 * image_array + 0.4 * heatmap_colored).astype(np.uint8)
        overlay_image = Image.fromarray(overlay)
        buffer = io.BytesIO()
        overlay_image.save(buffer, format='PNG')
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return encoded


def generate_gradcam(model, image_bytes, predictions):
    target_layer = model.features.denseblock4
    gradcam = GradCAM(model, target_layer)
    from model import get_transforms
    transform = get_transforms()
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    image_tensor = transform(image).unsqueeze(0).to(
        next(model.parameters()).device
    )
    heatmaps = {}
    for pred in predictions:
        cam = gradcam.generate(image_tensor, pred['label_index'])
        overlay = gradcam.overlay_on_image(image_bytes, cam)
        heatmaps[pred['condition']] = overlay
    return heatmaps