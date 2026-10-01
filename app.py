import os
import requests
from flask import Flask, request, jsonify, render_template_string

# ==============================================================================
# 1. GROQ CONFIGURATION (LOCKED TO openai/gpt-oss-120b)
# ==============================================================================
# Paste your Groq API key (gsk_...) here:
GROQ_API_KEY = "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"

# Model permanently set to openai/gpt-oss-120b
GROQ_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """
You are सरल (Saral), a friendly, encouraging, and intelligent AI study assistant and personal tutor.
You were created and developed by Avdhesh and his friend.
Your motto: 'Study Smarter • Learn Faster • Grow Together'.

Rules:
- If asked who built, created, or designed you, always proudly state you were made by Avdhesh and his friend.
- Help students with clear, simple, and accurate explanations.
- Keep voice explanations crisp (1-3 sentences) or use structured bullet points for study notes.
- You are fluent in English, Hindi (हिन्दी), and Gujarati (ગુજરાતી).
- Always reply in the requested target language.
"""

chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

def query_groq(prompt, target_lang="English"):
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":
        return "Please paste your active Groq API Key (gsk_...) on line 10."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    formatted_prompt = f"[Target Language: {target_lang}]\nQuestion/Doubt: {prompt}"
    chat_history.append({"role": "user", "content": formatted_prompt})

    payload = {
        "model": GROQ_MODEL,
        "messages": chat_history,
        "temperature": 0.5,
        "max_tokens": 700
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            reply = res.json()["choices"][0]["message"]["content"]
            chat_history.append({"role": "assistant", "content": reply})
            return reply
        else:
            err = res.json().get("error", {}).get("message", res.text)
            return f"Groq Error ({res.status_code}): {err}"
    except Exception as e:
        return f"Request Error: {str(e)}"

app = Flask(__name__)

# ==============================================================================
# 2. FRONTEND DASHBOARD (TRILINGUAL + NATURAL TTS + AVDHESH & FRIEND)
# ==============================================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>सरल (SARAL) - By Avdhesh & Friend</title>
<style>
:root {
  --bg: #080c16; --card: #0f172a; --border: #1e2c4f;
  --blue: #2563eb; --cyan: #38bdf8; --text: #f8fafc; --muted: #94a3b8;
}
* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; padding: 12px; }

header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 14px; background: #090f1d; border: 1px solid var(--border);
  border-radius: 14px; gap: 10px; flex-wrap: wrap;
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand h1 { font-size: 1.3rem; letter-spacing: 1px; color: var(--text); }
.dev-pill {
  background: rgba(37,99,235,0.18); border: 1px solid rgba(56,189,248,0.4);
  padding: 4px 10px; border-radius: 999px; font-size: 0.75rem; color: #7dd3fc;
}
.lang-picker { display: flex; background: var(--card); border: 1px solid var(--border); border-radius: 999px; padding: 3px; gap: 3px; }
.lang-btn {
  background: none; border: none; color: var(--muted); padding: 4px 10px;
  border-radius: 999px; font-size: 0.75rem; cursor: pointer; font-weight: 600;
}
.lang-btn.active { background: var(--blue); color: #fff; }

.hero { text-align: center; margin: 16px 0 10px; }
.hero h2 { font-size: 1.5rem; }
.hero p { font-size: 0.85rem; color: var(--muted); margin-top: 4px; }
.robot { font-size: 3.2rem; text-align: center; margin: 4px 0; }

.input-box {
  background: var(--card); border: 1px solid var(--border);
  border-radius: 18px; padding: 10px 14px; margin-bottom: 12px;
}
.input-row { display: flex; align-items: center; gap: 10px; }
.mic-btn {
  width: 40px; height: 40px; border-radius: 50%; background: #1e293b;
  border: 1px solid #334155; color: var(--cyan); font-size: 1.1rem;
  cursor: pointer; display: grid; place-items: center;
}
.mic-btn.active { background: #ef4444; color: #fff; }
input { flex: 1; background: none; border: none; outline: none; color: #fff; font-size: 0.95rem; }
.send-btn {
  width: 40px; height: 40px; border-radius: 50%; background: var(--blue);
  color: #fff; border: none; font-size: 1rem; cursor: pointer;
}
.chips { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.chip {
  background: #162038; border: 1px solid var(--border); border-radius: 999px;
  padding: 4px 10px; font-size: 0.75rem; color: var(--muted); cursor: pointer;
}
.chip:hover { color: #fff; border-color: var(--cyan); }

.res-card {
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  padding: 14px; min-height: 90px; max-height: 260px; overflow-y: auto;
  font-size: 0.9rem; line-height: 1.5;
}
.audio-ctrl {
  display: none; justify-content: space-between; align-items: center;
  background: #1e293b; padding: 6px 12px; border-radius: 0 0 14px 14px;
  font-size: 0.75rem; color: var(--cyan); margin-top: -6px;
}
.stop-btn { background: #ef4444; border: none; color: #fff; padding: 3px 8px; border-radius: 6px; cursor: pointer; }

.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-top: 14px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 12px; cursor: pointer; font-size: 0.8rem; }
.card b { display: block; margin-bottom: 2px; color: #fff; }

footer { margin-top: auto; padding-top: 16px; text-align: center; font-size: 0.75rem; color: var(--muted); }
</style>
</head>
<body>

<header>
  <div class="brand">
    <span style="font-size:1.6rem;">🎓</span>
    <div>
      <h1>सरल SARAL</h1>
      <div style="font-size:0.65rem; color:var(--muted);">{{ active_model }} ⚡</div>
    </div>
  </div>
  <div class="dev-pill">✨ Built by <b>Avdhesh & Friend</b></div>
  <div class="lang-picker">
    <button class="lang-btn active" id="b-en" onclick="setLang('en')">EN</button>
    <button class="lang-btn" id="b-hi" onclick="setLang('hi')">हिन्दी</button>
    <button class="lang-btn" id="b-gu" onclick="setLang('gu')">ગુજરાતી</button>
  </div>
</header>

<div class="hero">
  <div class="robot">🤖</div>
  <h2 id="hero-t">Hello! 👋</h2>
  <p id="hero-s">Your personal AI tutor engineered by Avdhesh & Friend.</p>
</div>

<div class="input-box">
  <div class="input-row">
    <button class="mic-btn" id="mic-b" onclick="toggleVoice()">🎤</button>
    <input type="text" id="usr-in" placeholder="Ask a doubt or tap mic..." onkeypress="if(event.key==='Enter')sendPrompt()">
    <button class="send-btn" onclick="sendPrompt()">➔</button>
  </div>
  <div class="chips" id="chip-box"></div>
</div>

<div class="res-card" id="res-box">
  <span style="color:var(--muted);" id="stat-txt">सरल तैयार है (Saral is ready). Ask anything!</span>
</div>
<div class="audio-ctrl" id="aud-ctrl">
  <span>🔊 <i>सरल बोल रहा है...</i></span>
  <button class="stop-btn" onclick="stopSpeech()">Stop ⏹️</button>
</div>

<div class="grid" id="grid-box"></div>

<footer>सरल (SARAL) • Engineered by Avdhesh & Friend for learners everywhere</footer>

<script>
const I18N = {
  en: {
    locale:'en-IN', name:'English', title:'Hello! 👋', sub:'AI Study Buddy by Avdhesh & Friend.',
    holder:'Ask a doubt or tap mic...', ready:'Saral is ready! Ask your question.',
    chips:[{l:'🎙️ Speak',a:()=>toggleVoice()},{l:'💡 Explain Concept',p:'Explain simply: '},{l:'👨‍💻 Creators',p:'Who made you?'}],
    cards:[{t:'Homework',s:'Step-by-step',p:'Solve homework: '},{t:'Math Solver',s:'With formulas',p:'Solve math: '},{t:'Notes',s:'Revision points',p:'Summarize: '}]
  },
  hi: {
    locale:'hi-IN', name:'Hindi', title:'नमस्ते! 🙏', sub:'अवधेश और उनके मित्र द्वारा निर्मित AI ट्यूटर।',
    holder:'प्रश्न लिखें या बोलकर पूछें...', ready:'सरल तैयार है! अपना प्रश्न पूछें।',
    chips:[{l:'🎙️ बोलें',a:()=>toggleVoice()},{l:'💡 आसान व्याख्या',p:'सरल शब्दों में समझाइए: '},{l:'👨‍💻 निर्माता कौन हैं?',p:'आपको किसने बनाया है?'}],
    cards:[{t:'होमवर्क सहायता',s:'चरणबद्ध हल',p:'होमवर्क हल करें: '},{t:'गणित हल',s:'पूरे सूत्र सहित',p:'गणित प्रश्न हल करें: '},{t:'संक्षिप्त नोट्स',p:'नोट्स बनाएं: '}]
  },
  gu: {
    locale:'gu-IN', name:'Gujarati', title:'નમસ્તે! 🙏', sub:'અવધેશ અને મિત્ર દ્વારા નિર્મિત AI સ્ટડી મિત્ર.',
    holder:'પ્રશ્ન લખો અથવા બોલીને પૂછો...', ready:'સરલ તૈયાર છે! તમારો પ્રશ્ન પૂછો.',
    chips:[{l:'🎙️ બોલો',a:()=>toggleVoice()},{l:'💡 સરળ સમજૂતી',p:'સરળતાથી સમજાવો: '},{l:'👨‍💻 નિર્માતા કોણ છે?',p:'તમને કોણે બનાવ્યું છે?'}],
    cards:[{t:'લેસનમાં મદદ',s:'પગલે-પગલે ઉકેલ',p:'હોમવર્ક ઉકેલો: '},{t:'ગણિત સોલ્વ',s:'સૂત્રો સાથે',p:'આ દાખલો ગણો: '},{t:'રિવિઝન નોટ્સ',p:'મુખ્ય મુદ્દાઓ આપો: '}]
  }
};

let curLang = 'en', isListening = false, voices = [];
const inp = document.getElementById('usr-in'), res = document.getElementById('res-box'),
      stat = document.getElementById('stat-txt'), mic = document.getElementById('mic-b'),
      aud = document.getElementById('aud-ctrl');

function loadVoices(){ if('speechSynthesis' in window) voices = window.speechSynthesis.getVoices(); }
if('speechSynthesis' in window){ loadVoices(); window.speechSynthesis.onvoiceschanged = loadVoices; }

function cleanTTS(t){
  return t.replace(/```[\\s\\S]*?```/g,'').replace(/[*_#`>-]/g,' ')
          .replace(/[\\u{1F600}-\\u{1F64F}\\u{1F300}-\\u{1F5FF}\\u{1F680}-\\u{1F6FF}]/gu,'').trim();
}

function getVoice(loc){
  const p = loc.split('-')[0].toLowerCase();
  if(p==='gu') return voices.find(v=>v.lang.toLowerCase().includes('gu')) || voices.find(v=>v.lang.toLowerCase().includes('hi'));
  if(p==='hi') return voices.find(v=>v.lang.toLowerCase().includes('hi'));
  return voices.find(v=>v.lang.toLowerCase().includes('en-in')) || voices.find(v=>v.lang.toLowerCase().startsWith('en'));
}

function stopSpeech(){
  if('speechSynthesis' in window){ window.speechSynthesis.cancel(); aud.style.display='none'; }
}

function speak(text, loc){
  if(!('speechSynthesis' in window)) return;
  stopSpeech();
  const c = cleanTTS(text);
  if(!c) return;
  const u = new SpeechSynthesisUtterance(c);
  u.lang = loc;
  u.rate = loc.startsWith('en') ? 1.0 : 0.95;
  const v = getVoice(loc);
  if(v) u.voice = v;
  aud.style.display = 'flex';
  u.onend = () => aud.style.display='none';
  u.onerror = () => aud.style.display='none';
  window.speechSynthesis.speak(u);
}

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let rec = SR ? new SR() : null;
if(rec){
  rec.onstart = () => { isListening = true; mic.classList.add('active'); stat.innerText = 'Listening...'; };
  rec.onend = () => { isListening = false; mic.classList.remove('active'); };
  rec.onresult = (e) => { inp.value = e.results[0][0].transcript; sendPrompt(); };
}

function toggleVoice(){
  if(!rec) return alert('Please use Google Chrome for voice features.');
  if(isListening){ rec.stop(); } else { rec.lang = I18N[curLang].locale; rec.start(); }
}

function setLang(k){
  curLang = k;
  stopSpeech();
  ['en','hi','gu'].forEach(l=>document.getElementById('b-'+l).classList.toggle('active', l===k));
  const d = I18N[k];
  document.getElementById('hero-t').innerText = d.title;
  document.getElementById('hero-s').innerText = d.sub;
  inp.placeholder = d.holder;
  stat.innerText = d.ready;
  if(rec) rec.lang = d.locale;

  const cb = document.getElementById('chip-box'); cb.innerHTML = '';
  d.chips.forEach(c => {
    const el = document.createElement('div'); el.className = 'chip'; el.innerText = c.l;
    el.onclick = c.a ? c.a : () => { inp.value = c.p; inp.focus(); };
    cb.appendChild(el);
  });

  const gb = document.getElementById('grid-box'); gb.innerHTML = '';
  d.cards.forEach(c => {
    const el = document.createElement('div'); el.className = 'card';
    el.innerHTML = `<b>${c.t}</b><span style="color:var(--muted)">${c.s||''}</span>`;
    el.onclick = () => { inp.value = c.p; inp.focus(); };
    gb.appendChild(el);
  });
}

async function sendPrompt(){
  const q = inp.value.trim();
  if(!q) return;
  stopSpeech();
  const d = I18N[curLang];
  res.innerHTML = `<b>You:</b> ${q}<br><br><span style="color:var(--cyan)">सरल सोच रहा है...</span>`;
  inp.value = '';
  try {
    const r = await fetch('/ask', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({prompt:q, language:d.name})
    });
    const data = await r.json();
    res.innerHTML = `<b>You:</b> ${q}<br><br><b style="color:var(--cyan)">सरल:</b> ${data.reply.replace(/\\n/g,'<br>')}`;
    speak(data.reply, d.locale);
  } catch(e) {
    res.innerHTML = '<span style="color:red">Server Error. Please try again.</span>';
  }
}

window.addEventListener('DOMContentLoaded', () => setLang('en'));
</script>
</body>
</html>"""

# ==============================================================================
# 3. ROUTES & ENTRY POINT
# ==============================================================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, active_model=GROQ_MODEL)

@app.route('/ask', methods=['POST'])
def ask():
    data = request.json or {}
    reply = query_groq(data.get('prompt', ''), target_lang=data.get('language', 'English'))
    return jsonify({'reply': reply})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
