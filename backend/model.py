import torch
import torch.nn as nn
from torchvision import transforms, models
from PIL import Image
import numpy as np
import io

LABELS = [
    'No Finding',
    'Cardiomegaly',
    'Edema',
    'Pneumonia',
    'Pleural Effusion'
]

THRESHOLD = 0.4

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


class ChestXRayModel(nn.Module):
    def __init__(self, num_classes=len(LABELS)):
        super().__init__()
        base = models.densenet121(weights=None)
        self.features = base.features
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(1024, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)


def get_transforms():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])


def load_model(model_path: str):
    model = ChestXRayModel()
    state_dict = torch.load(model_path, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()
    print(f"Model loaded on {DEVICE}")
    return model


def predict(model, image_bytes: bytes):
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    transform = get_transforms()
    tensor = transform(image).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        logits = model(tensor)
        probabilities = torch.sigmoid(logits).squeeze()

    results = []
    for i, (label, prob) in enumerate(zip(LABELS, probabilities)):
        prob_value = prob.item()
        if prob_value > THRESHOLD:
            results.append({
                'condition': label,
                'confidence': round(prob_value * 100, 1),
                'probability': prob_value,
                'label_index': i
            })

    results.sort(key=lambda x: x['confidence'], reverse=True)
    return results, probabilities.detach().cpu().numpy()