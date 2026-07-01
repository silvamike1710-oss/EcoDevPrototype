# ⚡ EcoDev AI

> Plataforma de auditoria de código que identifica ineficiências de custo e vulnerabilidades de segurança em projetos que usam APIs de IA (OpenAI, Anthropic, Gemini).

Interface com estética retrô Windows 95, backend em FastAPI e suporte a múltiplos provedores de IA (Anthropic Claude e Google Gemini).

---

## 🖥 Sobre o projeto

Muitos times integram IA generativa em produção (chatbots, pipelines de classificação, extração de dados) sem perceber padrões comuns que geram custo desnecessário ou risco de segurança — por exemplo, chamar a API dentro de um loop, usar um modelo caro pra uma tarefa simples, ou injetar input do usuário direto no prompt sem sanitização.

O **EcoDev AI** recebe um trecho de código Python e devolve um diagnóstico estruturado: quais problemas existem, quanto estão custando por mês (estimativa), e como corrigir — com trecho de código problemático lado a lado com a correção sugerida.

## ✨ Funcionalidades

- 🔍 Análise de código via IA (Anthropic Claude ou Google Gemini)
- 💰 Estimativa de desperdício mensal em USD por problema encontrado
- 🩹 Sugestão de correção com explicação de por que ela economiza dinheiro
- 🎮 Modo demo (resultado mockado, não gasta chamada de API — bom pra recrutador testar sem configurar nada)
- 📋 Exemplos prontos: loop de chamadas à API, ausência de system prompt, prompt injection, uso de modelo caro sem necessidade
- 🖥 Interface com estética Windows 95 (fonte VT323, bordas em bevel, janelas com barra de título)
- 🔒 Chaves de API nunca ficam no navegador — toda chamada passa por um backend próprio

## 🏗 Arquitetura

```
Front-end (HTML/CSS/JS)  →  Backend (FastAPI)  →  Anthropic / Gemini API
        sem chave              chave no .env
```

O front-end nunca fala direto com Anthropic ou Gemini. Ele manda o código pro backend, que guarda as chaves como variável de ambiente no servidor e faz a chamada real — assim a chave de API nunca fica exposta no navegador do usuário.

## 🧱 Stack técnica

**Backend**
- Python 3.11+
- FastAPI
- httpx (chamadas assíncronas às APIs de IA)
- Pydantic (validação de schema)

**Frontend**
- HTML5 / CSS3 (vanilla, sem framework)
- JavaScript (vanilla)
- Fonte VT323 (estética pixel/retrô)

**IA**
- Anthropic Claude (Sonnet)
- Google Gemini (Flash)

## 📁 Estrutura do projeto

```
my-project/
├── backend/
│   ├── main.py           # API FastAPI, proxy seguro pras IAs
│   ├── requirements.txt
│   ├── .env.example
│   └── .gitignore
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── style.css
├── README.md
└── LICENSE
```

## 🚀 Como rodar localmente

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
```

Preencha o `.env` com suas chaves:

```
ANTHROPIC_API_KEY=sk-ant-sua-chave-aqui
GEMINI_API_KEY=AIza-sua-chave-aqui
ALLOWED_ORIGINS=*
```

Suba o servidor:

```bash
uvicorn main:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000` (documentação interativa em `/docs`).

### 2. Frontend

Basta abrir o `frontend/index.html` no navegador, ou servir com:

```bash
cd frontend
python -m http.server 5500
```

> Nenhuma chave de API é necessária pra testar em **modo demo** — o resultado é simulado no próprio front-end.

## 📡 Endpoint principal

`POST /api/analyze`

```json
{
  "code": "...",
  "filename": "openai_handler.py",
  "provider": "anthropic"
}
```

Resposta:

```json
{
  "summary": "Código com 2 problemas críticos — custo estimado de $480/mês",
  "findings": [
    {
      "severity": "critical",
      "title": "API chamada dentro de loop",
      "description": "...",
      "estimated_monthly_waste_usd": 432,
      "problematic_code": "...",
      "suggested_fix_code": "...",
      "fix_explanation": "..."
    }
  ]
}
```

## 🗺 Roadmap

- [ ] Análise de repositório GitHub completo (via Git Trees API + pré-filtro regex)
- [ ] Suporte a mais provedores de IA (Groq)
- [ ] Exportar relatório em Markdown/PDF
- [ ] Histórico de análises anteriores
- [ ] Deploy em produção (Render)

## 📄 Licença

Este projeto está sob a licença MIT — veja o arquivo [LICENSE](./LICENSE) para mais detalhes.

## 👤 Autor

**Michael Silva**
Desenvolvedor Full Stack Python — [Portfólio](https://silvamike1710-oss.github.io/Portfolio)

hello!