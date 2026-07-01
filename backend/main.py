"""
EcoDev AI — Backend
────────────────────────────────────────────────────────────────────────────
Proxy seguro entre o front-end e as APIs de IA (Anthropic / Gemini).
 
Por que isso existe:
  Antes, o front-end chamava a API de IA DIRETO do navegador, usando a chave
  digitada pelo usuário guardada em sessionStorage. Isso expõe a chave no
  DevTools de qualquer pessoa que abrir a página. Agora o front manda o
  código pra este backend, o backend chama a IA usando a chave do SERVIDOR
  (variável de ambiente) e devolve só o resultado já processado.
 
Como rodar localmente:
  1. pip install -r requirements.txt
  2. copiar .env.example para .env e preencher as chaves
  3. uvicorn main:app --reload --port 8000
"""
import json
import os
import re

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

# ── CONFIG ───────────────────────────────────────────────────────────────
 
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Em produção, troque "*" pela URL real do seu front-end (ex: Vercel/Render)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app = FastAPI(title="EcoDev AI API", version="1.0.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
SYSTEM_PROMPT = """Você é o EcoDev AI, um auditor especializado em código que usa APIs de IA.
Identifique problemas de custo, performance e segurança.
 
Retorne APENAS JSON válido, sem texto antes ou depois, sem backticks:
 
{
  "summary": "resumo em 1 frase",
  "findings": [
    {
      "severity": "critical|warning|info|ok",
      "title": "título curto",
      "description": "explicação em 1-2 frases",
      "line_reference": "linha X-Y ou null",
      "estimated_monthly_waste_usd": 120,
      "problematic_code": "trecho problemático",
      "suggested_fix_code": "versão corrigida",
      "fix_explanation": "por que esta correção economiza dinheiro"
    }
  ]
}
 
Calcule estimated_monthly_waste_usd com base em produção real. 2-5 findings. APENAS JSON."""
 
# ── SCHEMAS ──────────────────────────────────────────────────────────────
 
class AnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20_000)
    filename: str = "codigo.py"
    provider: str = Field(..., pattern="^(anthropic|gemini)$")

class Finding(BaseModel):
    severity: str
    title: str
    description: str
    line_reference: str | None = None
    estimated_monthly_waste_usd: float | None = None
    problematic_code: str | None = None
    suggested_fix_code: str | None = None
    fix_explanation: str | None = None

class AnalyzeResponse(BaseModel):
    summary: str
    findings: list[Finding]

# ── PROVIDER CALLS ───────────────────────────────────────────────────────
 
async def call_anthropix(user_msg: str) -> str:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY não configurada no servidor.")
    
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 2000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": user_msg}],
            },
        )
    
    if res.status_code != 200:
        detail = res.json().get("error", {}).get("message", f"Anthropic HTTP {res.status_code}")
        raise HTTPException(res.status_code, detail)
    
    data = res.json()
    return data["content"][0]["text"].strip()

async def call_gemini(user_msg: str) -> str:
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY não configurada no servidor.")
    
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )

    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post(
            url,
            json={
                "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
                "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.2},
            },
        )
    if res.status_code != 200:
        detail = res.json().get("error", {}).get("message", f"Gemini HTTP {res.status_code}")
        raise HTTPException(res.status_code, detail)
    
    data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def strip_json_fences(raw: str) -> str:
      """Remove ```json ... ``` que os modelos
        às vezes adicionam mesmo pedindo pra não fazer isso."""
      cleaned = re.sub(r"^```(?:json)?\n?","", raw.strip())
      cleaned = re.sub(r"\n?```$", "", cleaned.strip())
      return cleaned.strip()

# ── ROUTES ───────────────────────────────────────────────────────────────
 
@app.get("/")
def health_check():
    return {"status": "ok", "service": "EcoDev AI API"}

@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_code(payload: AnalyzeRequest):
    user_msg = (
        f"Arquivo: {payload.filename}\n\n"
        f"```python\n{payload.code}\n```\n\n"
        "Analise e retorne o JSON de diágnostico."
    )

    if payload.provider == "anthropic":
        raw = await call_anthropic(user_msg)
    else:
        raw = await call_gemini(user_msg)

    cleaned = strip_json_fences(raw)

    try:
        result = json.load(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(
            502,
            "A IA retornou uma resposta em formato inválido. Tente novamente.",
        )
    return AnalyzeResponse(**result)