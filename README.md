#NOT FINISHED (BARELY WORKING)
#THIS IS ONLY A PLACEHOLDER README
# ⚡ EcoDev AI — Auditoria de Código

A web platform that audits Python codebases for **AI API cost inefficiencies** and **security vulnerabilities**, with a Win95-styled interface for a fast, hands-on diagnostic experience.

---

## 🖥️ About

EcoDev AI scans code that integrates with AI APIs (like OpenAI, Gemini, or Claude) and flags common but costly mistakes — things like missing caching, unnecessary loops calling the API, prompt injection risks, or using an oversized model when a smaller one would do the job. Built with a financial lens: the goal is catching what's silently burning through API budget, not just what's technically "wrong."

---

## ✨ Features

- 📄 Paste in any Python file and get an instant diagnostic
- ⚡ Detects common AI-API cost inefficiencies (no caching, redundant loop calls, oversized models)
- 🔒 Flags security risks like prompt injection via unsanitized input
- 🧪 **Demo/Mock mode** — try the full experience with no API key required
- 🔌 Multi-provider support: Google Gemini, Anthropic Claude (with your own API key)
- ⚡ Quick-load example snippets to see common problem patterns instantly
- 🪟 Full Win95-styled UI — title bars, status bar, panel chrome
- ⌨️ Keyboard shortcut (Ctrl+Enter) to run analysis

---

## 🛠️ Built With

- **Backend:** Python, FastAPI
- **Frontend:** HTML, CSS, JavaScript — Win95-styled UI
- **AI Providers:** Google Gemini, Anthropic Claude (pluggable)

---

## ⚙️ How It Works

1. Paste Python code into the left panel (or load a quick example)
2. Choose a provider — demo mode needs no API key, or plug in your own Gemini/Claude key
3. Click **ANALISAR** (or hit Ctrl+Enter)
4. The right panel returns a diagnostic: critical issues, warnings, and estimated wasted cost, broken down item by item

---

## 🚀 Getting Started

```bash
git clone <your-repo-url>
cd ecodev-ai
```

Backend setup:
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Then open `index.html` in your browser, or serve it via your preferred static file method.

> No API key is required to try it — demo mode runs with simulated results for presentation purposes.

---

## 📫 Contact

Built by Michael — feel free to reach out if you have questions or feedback!
