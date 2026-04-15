#chatbot.py
from google import genai
from google.genai import types
import os

GEMMA_MODEL = "gemma-4-26b-a4b-it"

client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
)


def build_system_prompt(report_data: dict) -> str:
    predictions   = report_data.get('predictions', [])
    scan_id       = report_data.get('scan_id', 'Unknown')
    date          = report_data.get('date', 'Unknown')
    findings_text = ""

    for pred in predictions:
        findings_text += (
            f"\n- {pred['condition']}: "
            f"{pred['confidence']}% confidence"
        )

    if not findings_text:
        findings_text = "\n- No significant findings detected"

    system_prompt = f"""
You are a medical assistant chatbot for ChestAI, an AI-powered chest X-ray analysis application.

YOUR ROLE:
You help patients understand their chest X-ray analysis report.
You answer questions about the findings in their specific report clearly and compassionately.

PATIENT'S REPORT:
Scan ID: {scan_id}
Date: {date}
Findings: {findings_text}

YOUR STRICT RULES:
1. ONLY discuss findings that appear in THIS report above
2. NEVER make new diagnoses or interpret symptoms the patient describes
3. ALWAYS recommend consulting a qualified doctor for medical decisions
4. Use simple, clear language — avoid complex medical jargon
5. Be calm and reassuring — do not alarm the patient unnecessarily
6. If asked about anything unrelated to this report, say:
   "I can only help with questions about your current chest X-ray report."
7. NEVER claim to be a doctor or provide definitive medical advice
8. If the patient seems distressed, acknowledge their feelings with empathy
   and encourage them to speak with their doctor

TONE:
- Warm, clear and professional
- Empathetic but not alarmist
- Concise answers (2-4 sentences unless more detail is needed)
"""
    return system_prompt.strip()


def format_history(conversation_history: list) -> list:
    formatted = []
    for message in conversation_history:
        formatted.append(
            types.Content(
                role=message['role'],
                parts=[types.Part(text=message['content'])]
            )
        )
    return formatted


def chat(user_message: str, conversation_history: list, report_data: dict) -> tuple:
    system_prompt      = build_system_prompt(report_data)
    formatted_history  = format_history(conversation_history)

    formatted_history.append(
        types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        )
    )

    response = client.models.generate_content(
        model=GEMMA_MODEL,
        contents=formatted_history,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=512,
            temperature=0.4,
        )
    )

    assistant_message = response.text

    conversation_history.append({
        "role":    "user",
        "content": user_message
    })
    conversation_history.append({
        "role":    "model",
        "content": assistant_message
    })

    return assistant_message, conversation_history


def new_conversation() -> list:
    return []


def get_suggested_questions(predictions: list) -> list:
    if not predictions:
        return [
            "What does a normal chest X-ray mean?",
            "When should I get another chest X-ray?",
            "What lifestyle habits keep lungs healthy?"
        ]

    questions = []
    for pred in predictions:
        condition = pred['condition']
        if condition == 'Pleural Effusion':
            questions.append("What is pleural effusion?")
            questions.append("How serious is pleural effusion?")
        elif condition == 'Edema':
            questions.append("What causes pulmonary edema?")
            questions.append("What are the treatment options for edema?")
        elif condition == 'Cardiomegaly':
            questions.append("What does an enlarged heart mean?")
            questions.append("Can cardiomegaly be treated?")
        elif condition == 'No Finding':
            questions.append("What does no finding mean?")
            questions.append("Do I need any follow-up?")

    questions.append("Should I be worried about my results?")
    questions.append("What questions should I ask my doctor?")
    return questions[:5]