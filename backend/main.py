# main.py
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
import jwt
import bcrypt
import os
import json
import asyncio
from datetime import datetime, timedelta
from supabase import create_client, Client
from contextlib import asynccontextmanager

from xray_model import load_model, predict, LABELS
from gradcam import generate_gradcam
from report import build_report
from chatbot import chat, new_conversation, get_suggested_questions

SECRET_KEY = os.environ.get("SECRET_KEY", "changethisinsecretkey123")
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

model = None


def _load_model_sync():
    global model
    print("Loading built-in TorchXRayVision model in background...")
    model = load_model()
    print("Model ready!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _load_model_sync)
    yield


app = FastAPI(title="ChestAI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://chest-diagnosis.vercel.app",
        "https://chest-diagnosis-2ewu5jz0f-pratham-tripathis-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: list
    report_data: dict


class AuthResponse(BaseModel):
    token: str
    user_id: str
    name: str
    email: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    return decode_token(credentials.credentials)["user_id"]


@app.get("/")
async def root():
    return {
        "status": "ChestAI API is running",
        "model_loaded": model is not None,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "database": supabase is not None,
    }


@app.post("/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    if not supabase:
        raise HTTPException(500, "Database not configured")

    existing = supabase.table("users").select("id").eq("email", request.email).execute()
    if existing.data:
        raise HTTPException(400, "Email already registered")

    hashed = hash_password(request.password)
    result = supabase.table("users").insert(
        {
            "email": request.email,
            "password": hashed,
            "name": request.name,
        }
    ).execute()

    user_id = result.data[0]["id"]
    return AuthResponse(
        token=create_token(user_id),
        user_id=user_id,
        name=request.name,
        email=request.email,
    )


@app.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    if not supabase:
        raise HTTPException(500, "Database not configured")

    result = supabase.table("users").select("*").eq("email", request.email).execute()
    if not result.data:
        raise HTTPException(401, "Invalid email or password")

    user = result.data[0]
    if not verify_password(request.password, user["password"]):
        raise HTTPException(401, "Invalid email or password")

    return AuthResponse(
        token=create_token(user["id"]),
        user_id=user["id"],
        name=user["name"],
        email=user["email"],
    )


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    if model is None:
        raise HTTPException(
            503,
            "Model is still loading. Please wait 30 seconds and try again.",
        )

    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(400, "Only JPEG and PNG images accepted")

    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Maximum 10MB")

    image_bytes = await file.read()

    predictions, _ = predict(model, image_bytes)

    has_real_findings = any(p["condition"] != "No Finding" for p in predictions)
    heatmaps = generate_gradcam(model, image_bytes, predictions) if has_real_findings else {}

    pdf_bytes, scan_id = build_report(predictions, heatmaps)

    image_url = report_url = None
    if supabase:
        image_path = f"{user_id}/{scan_id}/xray.jpg"
        report_path = f"{user_id}/{scan_id}/report.pdf"

        supabase.storage.from_("scans").upload(
            image_path, image_bytes, {"content-type": "image/jpeg"}
        )
        supabase.storage.from_("scans").upload(
            report_path, pdf_bytes, {"content-type": "application/pdf"}
        )

        image_url = supabase.storage.from_("scans").get_public_url(image_path)
        report_url = supabase.storage.from_("scans").get_public_url(report_path)

        supabase.table("scans").insert(
            {
                "user_id": user_id,
                "scan_id": scan_id,
                "predictions": json.dumps(predictions),
                "image_url": image_url,
                "report_url": report_url,
                "created_at": datetime.utcnow().isoformat(),
            }
        ).execute()

    return {
        "scan_id": scan_id,
        "predictions": predictions,
        "heatmaps": heatmaps,
        "suggested_questions": get_suggested_questions(predictions),
        "report_url": report_url,
        "has_findings": has_real_findings,
    }


@app.get("/report/{scan_id}")
async def get_report(
    scan_id: str,
    user_id: str = Depends(get_current_user),
):
    if not supabase:
        raise HTTPException(500, "Storage not configured")

    result = supabase.table("scans").select("*").eq(
        "scan_id", scan_id
    ).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(404, "Report not found")

    pdf_bytes = supabase.storage.from_("scans").download(
        f"{user_id}/{scan_id}/report.pdf"
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ChestAI_{scan_id}.pdf"
        },
    )


@app.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    response_text, updated_history = chat(
        request.message,
        request.conversation_history,
        request.report_data,
    )
    return {
        "response": response_text,
        "conversation_history": updated_history,
    }


@app.get("/history")
async def get_history(user_id: str = Depends(get_current_user)):
    if not supabase:
        return {"scans": []}

    result = supabase.table("scans").select(
        "scan_id, predictions, image_url, report_url, created_at"
    ).eq("user_id", user_id).order("created_at", desc=True).execute()

    return {
        "scans": [
            {
                **row,
                "predictions": json.loads(row["predictions"]),
            }
            for row in result.data
        ]
    }