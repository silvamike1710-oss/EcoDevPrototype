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

import asyncio
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
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # opcional — sem ele, rate limit é 60 req/hora

# Em produção, troque "*" pela URL real do seu front-end (ex: Vercel/Render)
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app = FastAPI(title="EcoDev AI API", version="1.0.0")

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

SYSTEM_PROMPT_REPO = """Você é o EcoDev AI, um auditor especializado em código que usa APIs de IA.
Você vai receber vários arquivos de um repositório, cada um marcado com "### arquivo: <caminho>".
Identifique problemas de custo, performance e segurança EM QUALQUER um dos arquivos.

Retorne APENAS JSON válido, sem texto antes ou depois, sem backticks:

{
  "summary": "resumo em 1 frase cobrindo o repositório inteiro",
  "findings": [
    {
      "severity": "critical|warning|info|ok",
      "title": "título curto",
      "description": "explicação em 1-2 frases",
      "file": "caminho/do/arquivo.py",
      "line_reference": "linha X-Y ou null",
      "estimated_monthly_waste_usd": 120,
      "problematic_code": "trecho problemático",
      "suggested_fix_code": "versão corrigida",
      "fix_explanation": "por que esta correção economiza dinheiro"
    }
  ]
}

Sempre preencha "file" com o caminho do arquivo onde o problema está. Priorize os problemas mais caros/graves.
Máximo 8 findings no total. APENAS JSON."""


# ── SCHEMAS ──────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20_000)
    filename: str = "codigo.py"
    provider: str = Field(..., pattern="^(anthropic|gemini)$")


class AnalyzeRepoRequest(BaseModel):
    repo_url: str = Field(..., min_length=1)
    provider: str = Field(..., pattern="^(anthropic|gemini)$")


class Finding(BaseModel):
    severity: str
    title: str
    description: str
    file: str | None = None
    line_reference: str | None = None
    estimated_monthly_waste_usd: float | None = None
    problematic_code: str | None = None
    suggested_fix_code: str | None = None
    fix_explanation: str | None = None


class AnalyzeResponse(BaseModel):
    summary: str
    findings: list[Finding]
    files_analyzed: list[str] = []


# ── PROVIDER CALLS ───────────────────────────────────────────────────────

async def call_anthropic(user_msg: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(500, "ANTHROPIC_API_KEY não configurada no servidor.")

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 3000,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_msg}],
            },
        )

    if res.status_code != 200:
        detail = res.json().get("error", {}).get("message", f"Anthropic HTTP {res.status_code}")
        raise HTTPException(res.status_code, detail)

    data = res.json()
    return data["content"][0]["text"].strip()


async def call_gemini(user_msg: str, system_prompt: str = SYSTEM_PROMPT) -> str:
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY não configurada no servidor.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(
            url,
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
                "generationConfig": {"maxOutputTokens": 3000, "temperature": 0.2},
            },
        )

    if res.status_code != 200:
        detail = res.json().get("error", {}).get("message", f"Gemini HTTP {res.status_code}")
        raise HTTPException(res.status_code, detail)

    data = res.json()
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def strip_json_fences(raw: str) -> str:
    """Remove ```json ... ``` que os modelos às vezes adicionam mesmo pedindo pra não fazer isso."""
    cleaned = re.sub(r"^```(?:json)?\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned.strip())
    return cleaned.strip()


# ── GITHUB INTEGRATION ───────────────────────────────────────────────────

MAX_FILES_TO_FETCH = 40     # não busca conteúdo de mais que isso, pra não estourar rate limit
MAX_FILES_TO_ANALYZE = 12   # depois do pré-filtro, manda no máximo isso pra IA
MAX_TOTAL_CHARS = 40_000    # teto de caracteres combinados mandados pro modelo

# Pré-filtro: só vale a pena gastar tokens de IA em arquivos que de fato
# tocam em alguma API de IA. Isso evita mandar o repositório inteiro pro
# modelo (caro e lento) quando só 2 de 80 arquivos usam IA de verdade.
AI_USAGE_PATTERN = re.compile(
    r"\b(openai|anthropic|google\.generativeai|genai|langchain|"
    r"OPENAI_API_KEY|ANTHROPIC_API_KEY|GEMINI_API_KEY|"
    r"chat\.completions|messages\.create|generateContent)\b",
    re.IGNORECASE,
)


def _github_headers() -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def parse_github_url(repo_url: str) -> tuple[str, str]:
    """Aceita 'https://github.com/owner/repo', 'github.com/owner/repo' ou 'owner/repo'."""
    cleaned = repo_url.strip().rstrip("/")
    cleaned = re.sub(r"^https?://(www\.)?github\.com/", "", cleaned)
    cleaned = cleaned.removesuffix(".git")
    parts = cleaned.split("/")
    if len(parts) < 2:
        raise HTTPException(400, "URL de repositório inválida. Use o formato owner/repo.")
    return parts[0], parts[1]


async def fetch_repo_tree(owner: str, repo: str) -> tuple[list[str], str]:
    """Retorna (lista de caminhos .py, branch padrão) usando a Git Trees API."""
    async with httpx.AsyncClient(timeout=30, headers=_github_headers()) as client:
        repo_res = await client.get(f"https://api.github.com/repos/{owner}/{repo}")
        if repo_res.status_code == 404:
            raise HTTPException(404, f"Repositório '{owner}/{repo}' não encontrado ou privado.")
        if repo_res.status_code == 403 and repo_res.json().get("message", "").startswith("API rate limit"):
            raise HTTPException(
                429,
                "Rate limit do GitHub excedido (60 req/hora sem token). "
                "Configure GITHUB_TOKEN no .env pra subir esse limite pra 5.000 req/hora.",
            )
        if repo_res.status_code != 200:
            raise HTTPException(repo_res.status_code, "Erro ao acessar o GitHub.")

        default_branch = repo_res.json()["default_branch"]

        tree_res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}",
            params={"recursive": "1"},
        )
        if tree_res.status_code == 403 and tree_res.json().get("message", "").startswith("API rate limit"):
            raise HTTPException(
                429,
                "Rate limit do GitHub excedido (60 req/hora sem token). "
                "Configure GITHUB_TOKEN no .env pra subir esse limite pra 5.000 req/hora.",
            )
        if tree_res.status_code != 200:
            raise HTTPException(tree_res.status_code, "Erro ao ler a árvore de arquivos do repositório.")

        tree = tree_res.json().get("tree", [])

    py_paths = [
        item["path"] for item in tree
        if item.get("type") == "blob" and item["path"].endswith(".py")
    ]
    return py_paths[:MAX_FILES_TO_FETCH], default_branch


async def fetch_file_content(owner: str, repo: str, branch: str, path: str, client: httpx.AsyncClient) -> str | None:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    try:
        res = await client.get(url, timeout=15)
        if res.status_code == 200:
            return res.text
    except httpx.HTTPError:
        pass
    return None


async def collect_relevant_files(owner: str, repo: str) -> tuple[list[tuple[str, str]], int]:
    """Busca conteúdo dos arquivos .py e aplica o pré-filtro regex de uso de IA.

    Retorna (lista de (caminho, conteúdo) já filtrada e truncada, total de arquivos .py encontrados).
    """
    py_paths, branch = await fetch_repo_tree(owner, repo)
    if not py_paths:
        return [], 0

    async with httpx.AsyncClient() as client:
        contents = await asyncio.gather(
            *[fetch_file_content(owner, repo, branch, path, client) for path in py_paths]
        )

    relevant = [
        (path, content)
        for path, content in zip(py_paths, contents)
        if content and AI_USAGE_PATTERN.search(content)
    ]

    # limita quantidade e tamanho total pra manter o custo/latência da chamada de IA sob controle
    relevant = relevant[:MAX_FILES_TO_ANALYZE]
    trimmed: list[tuple[str, str]] = []
    total_chars = 0
    for path, content in relevant:
        remaining = MAX_TOTAL_CHARS - total_chars
        if remaining <= 0:
            break
        snippet = content[:remaining]
        trimmed.append((path, snippet))
        total_chars += len(snippet)

    return trimmed, len(py_paths)


# ── ROUTES ───────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "ok", "service": "EcoDev AI API"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_code(payload: AnalyzeRequest):
    user_msg = (
        f"Arquivo: {payload.filename}\n\n"
        f"```python\n{payload.code}\n```\n\n"
        "Analise e retorne o JSON de diagnóstico."
    )

    if payload.provider == "anthropic":
        raw = await call_anthropic(user_msg)
    else:
        raw = await call_gemini(user_msg)

    cleaned = strip_json_fences(raw)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(
            502,
            "A IA retornou uma resposta em formato inválido. Tente novamente.",
        )

    result.setdefault("files_analyzed", [payload.filename])
    return AnalyzeResponse(**result)


@app.post("/api/analyze-repo", response_model=AnalyzeResponse)
async def analyze_repo(payload: AnalyzeRepoRequest):
    owner, repo = parse_github_url(payload.repo_url)

    files, total_py_files = await collect_relevant_files(owner, repo)

    if total_py_files == 0:
        raise HTTPException(404, "Nenhum arquivo .py encontrado neste repositório.")

    if not files:
        return AnalyzeResponse(
            summary=f"Nenhum uso de API de IA detectado nos {total_py_files} arquivos .py deste repositório.",
            findings=[],
            files_analyzed=[],
        )

    files_block = "\n\n".join(
        f"### arquivo: {path}\n```python\n{content}\n```" for path, content in files
    )
    user_msg = (
        f"Repositório: {owner}/{repo}\n"
        f"Arquivos filtrados por uso de API de IA ({len(files)} de {total_py_files} arquivos .py):\n\n"
        f"{files_block}\n\n"
        "Analise todos os arquivos e retorne o JSON de diagnóstico consolidado."
    )

    if payload.provider == "anthropic":
        raw = await call_anthropic(user_msg, system_prompt=SYSTEM_PROMPT_REPO)
    else:
        raw = await call_gemini(user_msg, system_prompt=SYSTEM_PROMPT_REPO)

    cleaned = strip_json_fences(raw)

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        raise HTTPException(
            502,
            "A IA retornou uma resposta em formato inválido. Tente novamente.",
        )

    result.setdefault("files_analyzed", [path for path, _ in files])
    return AnalyzeResponse(**result)