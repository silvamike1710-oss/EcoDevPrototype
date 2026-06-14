// ── ECODEV AI — app.js ──────────────────────────────────────────────────

// ── EXAMPLES ────────────────────────────────────────────────────────────

const EXAMPLES = {
  loop: {
    name: 'openai_loop.py',
    code: `import openai

client = openai.OpenAI()

def process_user_messages(messages_list):
    """Processa uma lista de mensagens dos usuários"""
    results = []

    for msg in messages_list:  # pode ter 500+ mensagens
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": msg}
            ],
            max_tokens=200
        )
        results.append(response.choices[0].message.content)

    return results

# chamado em produção a cada 10 minutos
user_messages = get_pending_messages()
output = process_user_messages(user_messages)`
  },

  nosystem: {
    name: 'sentiment_pipeline.py',
    code: `import openai

client = openai.OpenAI()

def classify_sentiment(text):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"Classifique o sentimento: {text}"
            }
        ],
        max_tokens=500,
        temperature=0.7
    )
    return response.choices[0].message.content

# pipeline que processa 10.000 textos por dia
texts = load_texts_from_db()
sentiments = [classify_sentiment(t) for t in texts]`
  },

  injection: {
    name: 'support_bot.py',
    code: `from anthropic import Anthropic

client = Anthropic()

def answer_question(user_question, user_name):
    # Input direto do usuário no prompt — sem sanitização
    prompt = f"""
    Você é um assistente de suporte da empresa.
    O usuário {user_name} perguntou: {user_question}
    Você tem acesso ao banco de dados interno se precisar.
    """

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text`
  },

  model: {
    name: 'invoice_extractor.py',
    code: `import openai

client = openai.OpenAI()

def extract_fields_from_invoice(invoice_text):
    response = client.chat.completions.create(
        model="gpt-4o",  # modelo mais caro
        messages=[
            {
                "role": "system",
                "content": "Você extrai dados estruturados de notas fiscais."
            },
            {
                "role": "user",
                "content": f"Extraia: número, data, valor, CNPJ.\\n\\n{invoice_text}"
            }
        ],
        max_tokens=150,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

# 5.000 notas por dia
for inv in get_invoices_queue():
    data = extract_fields_from_invoice(inv)`
  }
};

function loadExample(key) {
  const ex = EXAMPLES[key];
  if (!ex) return;
  document.getElementById('code').value     = ex.code;
  document.getElementById('filename').value = ex.name;
}

// ── MOCK DATA ────────────────────────────────────────────────────────────

const MOCK_RESULT = {
  summary: "Código com 2 problemas críticos — custo estimado de $480/mês desnecessário",
  findings: [
    {
      severity: "critical",
      title: "API chamada dentro de loop",
      description: "Cada item da lista dispara uma requisição individual à API. Com 200 msgs a cada 10 minutos, isso gera 28.800 chamadas/dia ao GPT-4o.",
      line_reference: "linha 9-15",
      estimated_monthly_waste_usd: 432,
      problematic_code: `for msg in messages_list:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": msg}],
        max_tokens=200
    )`,
      suggested_fix_code: `# Use batch: agrupe até 20 msgs por requisição
BATCH = 20
for i in range(0, len(messages_list), BATCH):
    batch = messages_list[i:i+BATCH]
    combined = "\\n---\\n".join(
        f"[{j+1}] {m}" for j, m in enumerate(batch)
    )
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 15x mais barato
        messages=[{"role": "user", "content": combined}],
        max_tokens=200 * len(batch)
    )`,
      fix_explanation: "Agrupando 20 mensagens por chamada e usando gpt-4o-mini, você reduz de 28.800 para 1.440 requisições/dia e o custo de ~$432 para ~$9/mês."
    },
    {
      severity: "critical",
      title: "Modelo GPT-4o desnecessário",
      description: "Processamento de mensagens simples não justifica o GPT-4o. O GPT-4o-mini tem desempenho equivalente para classificação e custa 15x menos.",
      line_reference: "linha 11",
      estimated_monthly_waste_usd: 48,
      problematic_code: `model="gpt-4o",`,
      suggested_fix_code: `model="gpt-4o-mini",  # $0.15/1M tokens vs $2.50/1M`,
      fix_explanation: "Para tarefas de classificação, summarização e extração simples, o gpt-4o-mini entrega resultados equivalentes. Trocar o modelo aqui economiza ~$48/mês só neste endpoint."
    },
    {
      severity: "warning",
      title: "Sem system prompt",
      description: "Sem instruções de sistema, o modelo recebe contexto zero e tende a responder de forma mais longa e genérica, consumindo mais tokens na saída.",
      line_reference: "linha 9-16",
      estimated_monthly_waste_usd: null,
      problematic_code: `messages=[
    {"role": "user", "content": msg}
]`,
      suggested_fix_code: `messages=[
    {
        "role": "system",
        "content": "Responda de forma concisa. Máximo 2 frases."
    },
    {"role": "user", "content": msg}
]`,
      fix_explanation: "Um system prompt com instrução de concisão reduz tokens de saída em 40-60%, diminuindo custo e latência."
    },
    {
      severity: "info",
      title: "Sem retry e sem tratamento de erro",
      description: "APIs de IA têm rate limits e timeouts. Sem retry, um erro 429 derruba todo o processamento em silêncio.",
      line_reference: "linha 7-16",
      estimated_monthly_waste_usd: null,
      problematic_code: `response = client.chat.completions.create(...)`,
      suggested_fix_code: `from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=2, max=10))
def call_api(msg):
    return client.chat.completions.create(...)`,
      fix_explanation: "A lib tenacity adiciona retry com backoff exponencial em 2 linhas. Evita falhas silenciosas e perda de dados em produção."
    }
  ]
};

// ── PROVIDER / KEY ───────────────────────────────────────────────────────

function updateProviderHint() {
  const p = document.getElementById('provider').value;
  const hints = {
    mock:      '[ DEMO MODE — sem chave necessária ]',
    gemini:    'Gemini grátis: aistudio.google.com → Get API Key',
    anthropic: 'Anthropic: console.anthropic.com → API Keys'
  };
  const placeholders = {
    mock:      'não necessário no modo demo',
    gemini:    'AIza...',
    anthropic: 'sk-ant-...'
  };
  document.getElementById('keyStatus').textContent = hints[p];
  document.getElementById('keyStatus').style.color = p === 'mock' ? 'var(--warn)' : 'var(--muted)';
  document.getElementById('apiKey').placeholder = placeholders[p];
  document.getElementById('apiKey').disabled    = p === 'mock';
}

function saveKey() {
  const key      = document.getElementById('apiKey').value.trim();
  const provider = document.getElementById('provider').value;
  sessionStorage.setItem('ecodev_provider', provider);
  if (key) {
    sessionStorage.setItem('ecodev_key', key);
    document.getElementById('keyStatus').textContent = '[ CHAVE SALVA NA SESSÃO ]';
    document.getElementById('keyStatus').style.color = 'var(--accent)';
  }
}

window.onload = () => {
  const saved    = sessionStorage.getItem('ecodev_key');
  const provider = sessionStorage.getItem('ecodev_provider') || 'mock';

  document.getElementById('provider').value = provider;

  if (saved) {
    document.getElementById('apiKey').value = saved;
    document.getElementById('keyStatus').textContent = '[ CHAVE CARREGADA ]';
    document.getElementById('keyStatus').style.color = 'var(--accent)';
  }

  updateProviderHint();
  loadExample('loop');
};

// ── SYNTAX HIGHLIGHT ─────────────────────────────────────────────────────

function highlight(code) {
  return code
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/(#[^\n]*)/g, '<span class="hl-comment">$1</span>')
    .replace(/\b(import|from|def|class|return|for|in|if|else|elif|with|as|and|or|not|True|False|None|async|await|range)\b/g,
             '<span class="hl-keyword">$1</span>')
    .replace(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|f"(?:[^"\\]|\\.)*"|f'(?:[^'\\]|\\.)*')/g,
             '<span class="hl-string">$1</span>')
    .replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="hl-num">$1</span>');
}

// ── RENDER ───────────────────────────────────────────────────────────────

function renderFindings(findings) {
  const body = document.getElementById('resultsBody');
  body.innerHTML = '';

  const totalSaved = findings
    .filter(f => f.estimated_monthly_waste_usd)
    .reduce((a, b) => a + (b.estimated_monthly_waste_usd || 0), 0);

  const criticals = findings.filter(f => f.severity === 'critical').length;
  const warnings  = findings.filter(f => f.severity === 'warning').length;

  // update statusbar
  document.getElementById('statCrit').textContent  = `CRITICOS: ${criticals}`;
  document.getElementById('statWarn').textContent  = `AVISOS: ${warnings}`;
  document.getElementById('statCost').textContent  = `DESPERD: $${totalSaved}`;
  document.getElementById('statCount').textContent = `ITENS: ${findings.length}`;

  document.getElementById('statCrit').className  = 'statusbar-cell' + (criticals > 0 ? ' danger-cell' : '');
  document.getElementById('statWarn').className  = 'statusbar-cell' + (warnings > 0  ? ' warn-cell'   : '');
  document.getElementById('statCost').className  = 'statusbar-cell' + (totalSaved > 0 ? ' danger-cell' : '');

  // summary bar
  const summaryEl = document.createElement('div');
  summaryEl.className = 'summary-bar';
  summaryEl.innerHTML = `
    <div class="summary-item">
      <div class="summary-value" style="color:var(--danger)">${criticals}</div>
      <div class="summary-label">Críticos</div>
    </div>
    <div class="summary-item">
      <div class="summary-value" style="color:var(--warn)">${warnings}</div>
      <div class="summary-label">Avisos</div>
    </div>
    <div class="summary-item">
      <div class="summary-value" style="color:var(--accent)">$${totalSaved}</div>
      <div class="summary-label">Desperd./mês</div>
    </div>
    <div class="summary-item">
      <div class="summary-value" style="color:var(--muted)">${findings.length}</div>
      <div class="summary-label">Ocorrências</div>
    </div>
  `;
  body.appendChild(summaryEl);

  findings.forEach((f, i) => {
    const sevClass  = { critical:'sev-critical', warning:'sev-warning', info:'sev-info', ok:'sev-ok' }[f.severity] || 'sev-info';
    const costClass = f.severity === 'critical' ? 'danger' : f.severity === 'warning' ? 'warn' : 'ok';
    const hasCode   = f.problematic_code || f.suggested_fix_code;

    const el = document.createElement('div');
    el.className = 'finding';
    el.innerHTML = `
      <div class="finding-header">
        <div class="severity-dot ${sevClass}"></div>
        <div style="flex:1">
          <div class="finding-title">${f.title}</div>
          <div class="finding-desc">${f.description}</div>
        </div>
        <div class="finding-meta">
          ${f.estimated_monthly_waste_usd != null
            ? `<div class="cost-badge ${costClass}">-$${f.estimated_monthly_waste_usd}/mês</div>`
            : ''}
          ${f.line_reference ? `<div class="line-tag">${f.line_reference}</div>` : ''}
        </div>
      </div>
      ${hasCode ? `
      <div class="code-section">
        <div class="code-tabs">
          ${f.problematic_code  ? `<div class="code-tab active"  onclick="switchTab(this,'bad-${i}')">PROBLEMA</div>`  : ''}
          ${f.suggested_fix_code ? `<div class="code-tab"         onclick="switchTab(this,'fix-${i}')">CORREÇÃO</div>` : ''}
        </div>
        ${f.problematic_code   ? `<pre id="bad-${i}" class="tab-content">${highlight(f.problematic_code)}</pre>`                          : ''}
        ${f.suggested_fix_code ? `<pre id="fix-${i}" class="tab-content" style="display:none">${highlight(f.suggested_fix_code)}</pre>`   : ''}
      </div>` : ''}
      ${f.fix_explanation ? `
      <div class="fix-section">
        <div class="fix-label">&gt; COMO CORRIGIR</div>
        <div class="fix-text">${f.fix_explanation}</div>
      </div>` : ''}
    `;
    body.appendChild(el);
  });
}

function switchTab(tab, targetId) {
  const section = tab.closest('.code-section');
  section.querySelectorAll('.code-tab').forEach(t => t.classList.remove('active'));
  section.querySelectorAll('.tab-content').forEach(t => t.style.display = 'none');
  tab.classList.add('active');
  document.getElementById(targetId).style.display = 'block';
}

// ── API CALLS ────────────────────────────────────────────────────────────

const SYSTEM_PROMPT = `Você é o EcoDev AI, um auditor especializado em código que usa APIs de IA.
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

Calcule estimated_monthly_waste_usd com base em produção real. 2-5 findings. APENAS JSON.`;

async function callAnthropic(apiKey, userMsg) {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true'
    },
    body: JSON.stringify({
      model: 'claude-sonnet-4-6',
      max_tokens: 2000,
      system: SYSTEM_PROMPT,
      messages: [{ role: 'user', content: userMsg }]
    })
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || `Anthropic HTTP ${res.status}`);
  }
  const data = await res.json();
  return data.content[0].text.trim();
}

async function callGemini(apiKey, userMsg) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
      contents: [{ role: 'user', parts: [{ text: userMsg }] }],
      generationConfig: { maxOutputTokens: 2000, temperature: 0.2 }
    })
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.error?.message || `Gemini HTTP ${res.status}`);
  }
  const data = await res.json();
  return data.candidates[0].content.parts[0].text.trim();
}

// ── MAIN ANALYZE ─────────────────────────────────────────────────────────

async function analyzeCode() {
  const code     = document.getElementById('code').value.trim();
  const filename = document.getElementById('filename').value.trim();
  const provider = document.getElementById('provider').value
                   || sessionStorage.getItem('ecodev_provider') || 'mock';
  const apiKey   = document.getElementById('apiKey').value.trim()
                   || sessionStorage.getItem('ecodev_key');

  if (!code) return alert('Cole um código para analisar.');
  if (provider !== 'mock' && !apiKey) return alert('Insira sua chave de API.');

  const btn    = document.getElementById('analyzeBtn');
  const loader = document.getElementById('loader');
  const body   = document.getElementById('resultsBody');
  const banner = document.getElementById('mockBanner');

  btn.disabled = true;
  document.getElementById('btnText').textContent = 'AGUARDE...';
  loader.classList.add('visible');
  body.innerHTML = '';
  banner.classList.remove('visible');

  const userMsg = `Arquivo: ${filename || 'código.py'}\n\n\`\`\`python\n${code}\n\`\`\`\n\nAnalise e retorne o JSON de diagnóstico.`;

  try {
    let result;

    if (provider === 'mock') {
      // simulate a short delay so it feels real
      await new Promise(r => setTimeout(r, 900));
      result = MOCK_RESULT;
      banner.classList.add('visible');
    } else {
      let raw;
      if (provider === 'anthropic') {
        raw = await callAnthropic(apiKey, userMsg);
      } else {
        raw = await callGemini(apiKey, userMsg);
      }
      const clean = raw.replace(/^```(?:json)?\n?/, '').replace(/\n?```$/, '').trim();
      result = JSON.parse(clean);
    }

    loader.classList.remove('visible');
    renderFindings(result.findings || []);

  } catch (err) {
    loader.classList.remove('visible');
    body.innerHTML = `
      <div class="empty">
        <div class="empty-icon">⚠</div>
        <h3>ERRO NA ANÁLISE</h3>
        <p style="color:var(--danger);font-family:var(--mono);font-size:12px;">${err.message}</p>
      </div>`;
  } finally {
    btn.disabled = false;
    document.getElementById('btnText').textContent = '⚡ ANALISAR';
  }
}

// Ctrl+Enter shortcut
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') analyzeCode();
});