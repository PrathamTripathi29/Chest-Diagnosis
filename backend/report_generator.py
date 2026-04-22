import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor
import io

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Global variables — loaded once at startup
_processor = None
_model     = None


def load_report_model():
    """
    Downloads and loads the CXR report generation model.
    Called once at startup alongside the classification model.
    """
    global _processor, _model
    print("Loading report generation model...")
    _processor = BlipProcessor.from_pretrained("nathansutton/generate-cxr")
    _model     = BlipForConditionalGeneration.from_pretrained(
        "nathansutton/generate-cxr"
    ).to(DEVICE)
    _model.eval()
    print("Report generation model ready!")


def generate_radiology_report(image_bytes: bytes, predictions: list) -> str:
    """
    Generates a radiology-style report from the X-ray image.

    image_bytes:  raw image bytes
    predictions:  list of detected conditions from classification model
    returns:      report text string
    """
    global _processor, _model

    if _processor is None or _model is None:
        return "Report generation model not loaded."

    # Build clinical indication from predictions
    # This tells the model what to focus on
    if predictions and predictions[0]['condition'] != 'No Finding':
        conditions = [p['condition'] for p in predictions
                      if p['condition'] != 'No Finding']
        indication = f"evaluate for {', '.join(conditions)}"
    else:
        indication = "routine chest X-ray evaluation"

    # Load and prepare image
    image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

    # Process inputs — model expects image + indication text
    inputs = _processor(
        images=image,
        text=f"indication: {indication}",
        return_tensors="pt"
    ).to(DEVICE)

    # Generate report
    with torch.no_grad():
        output = _model.generate(
            **inputs,
            max_length=512,
            num_beams=4,         # beam search for better quality
            early_stopping=True,
            no_repeat_ngram_size=3  # prevents repetition
        )

    report_text = _processor.decode(output[0], skip_special_tokens=True)

    # Clean up the output — remove the indication prefix if echoed back
    if "indication:" in report_text.lower():
        report_text = report_text.split("indication:")[-1].strip()

    return report_text