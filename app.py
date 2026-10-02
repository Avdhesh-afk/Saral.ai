import os
import io
import re
import requests
from flask import Flask, request, jsonify, render_template_string, send_file

# Check for gTTS (Natural Voice)
try:
    from gtts import gTTS
    USE_NATURAL_AUDIO = True
except ImportError:
    USE_NATURAL_AUDIO = False

# ==============================================================================
# 1. GROQ CONFIGURATION (DUAL-MODEL ROUTING)
# ==============================================================================
GROQ_API_KEY = "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"

# Primary model for text, Vision model for image inputs
GROQ_TEXT_MODEL = "openai/gpt-oss-120b"
GROQ_VISION_MODEL = "llama-3.2-11b-vision-preview"

SYSTEM_PROMPT = """
You are SARAL AI (सरल), a friendly, encouraging, and intelligent personal AI tutor.
You were created and engineered by Avdhesh and his friend.
Your motto is 'Study Smarter • Learn Faster • Grow Together'.

Persona & Rules:
- If asked who made, built, or developed you, proudly credit Avdhesh and his friend.
- Help students with clear, intuitive, and accurate explanations. If an image is provided, analyze it thoroughly to help the student.
- Keep spoken answers crisp (1-3 sentences) or use structured bullet points for notes.
- Fluent in English, Hindi (हिन्दी), and Gujarati (ગુજરાતી). Always reply in the requested target language.

FORMATTING STRICT RULES:
- AVOID special characters: Do not use \ / { } : ; _ # @ * in your text.
- MATH SYMBOLS: Use standard symbols (÷, ×, -, +) for mathematical equations.
- EMOJIS: You are highly encouraged to use emojis in your text output to make it friendly and engaging.
"""

# Global conversation history
chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

def clean_text_for_speech(text):
    """
    Strips specified special characters and emojis so TTS sounds human, 
    but safely keeps math symbols (+, -, ×, ÷) so they are read aloud.
    """
    if not text:
        return ""
    # Remove code blocks and markdown links
    t = re.sub(r'```[\s\S]*?```', '', text)
    t = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', t)
    
    # Remove requested special characters: \ / { } : ; _ # @ *
    t = re.sub(r'[\\/\{\}\:\;_\#\@\*]', ' ', t)
    
    # Remove emojis (so the TTS doesn't read them out loud mechanically)
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    t = re.sub(r'[\u20a0-\u32ff\ud83c-\ud83e]', '', t)
    
    # Clean up extra spaces
    return re.sub(r'\s+', ' ', t).strip()

def query_groq(prompt, target_lang="English", image_base64=None):
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":
        return "Please paste your active Groq API Key (gsk_...) in app.py or environment variables."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    formatted_prompt = f"[Target Language: {target_lang}]\nQuestion/Doubt: {prompt}"
    
    # Route to Vision model if an image is attached, otherwise use the standard model
    if image_base64:
        active_model = GROQ_VISION_MODEL
        current_msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": formatted_prompt},
                {"type": "image_url", "image_url": {"url": image_base64}}
            ]
        }
    else:
        active_model = GROQ_TEXT_MODEL
        current_msg = {"role": "user", "content": formatted_prompt}

    # Construct temporary payload history
    temp_history = chat_history + [current_msg]

    payload = {
        "model": active_model,
        "messages": temp_history,
        "temperature": 0.5,
        "max_tokens": 700
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            reply = res.json()["choices"][0]["message"]["content"]
            
            # Save strictly TEXT to persistent history to avoid compatibility issues with the text model
            chat_history.append({"role": "user", "content": formatted_prompt + " [Image Attached]" if image_base64 else formatted_prompt})
            chat_history.append({"role": "assistant", "content": reply})
            
            return reply
        else:
            try:
                err = res.json().get("error", {}).get("message", res.text)
            except Exception:
                err = res.text
            return f"Groq Error ({res.status_code}): {err}"
    except Exception as e:
        return f"Request Error: {str(e)}"

app = Flask(__name__)

# ==============================================================================
# 2. FRONTEND TEMPLATE (WITH IMAGE UPLOAD UI)
# ==============================================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>SARAL AI - Let's make learning simple</title>
<style>
:root {
  --primary: #0077c8;
  --primary-gradient: linear-gradient(135deg, #0284c7 0%, #0070f3 100%);
  --sky-gradient: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
  --bg-app: #f4f8fc;
  --card-bg: #ffffff;
  --text-dark: #0f172a;
  --text-muted: #64748b;
  --bubble-bg: #e2f1fc;
  --bubble-user: #0284c7;
  --border-light: #e2e8f0;
}

* { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, sans-serif; }
body { background: #e2e8f0; display: flex; justify-content: center; min-height: 100vh; }

.mobile-shell {
  width: 100%;
  max-width: 440px;
  background: var(--bg-app);
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0,0,0,0.12);
  position: relative;
  overflow-x: hidden;
}

header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px 10px; background: var(--bg-app);
}

.brand-wrap { display: flex; align-items: center; gap: 8px; text-decoration: none; }
.logo-icon { width: 32px; height: 32px; }
.brand-text { font-size: 1.28rem; font-weight: 800; letter-spacing: -0.5px; color: #0b2545; display: flex; align-items: center; gap: 4px; }
.brand-text span { color: #0084ff; font-weight: 700; }

.header-right { display: flex; align-items: center; gap: 12px; }
.lang-selector { display: flex; background: #e2e8f0; border-radius: 999px; padding: 2px; }
.lang-chip { border: none; background: transparent; color: #64748b; font-size: 0.72rem; font-weight: 700; padding: 4px 8px; border-radius: 999px; cursor: pointer; }
.lang-chip.active { background: #0284c7; color: #fff; }

.hero-content { padding: 10px 20px 14px; }
.hero-content h1 { font-size: 1.45rem; font-weight: 800; color: #0f172a; }
.hero-content p { font-size: 0.88rem; color: var(--text-muted); margin-top: 2px; }
.dev-pill { display: inline-block; margin-top: 6px; background: #e0f2fe; color: #0369a1; font-size: 0.72rem; font-weight: 600; padding: 3px 10px; border-radius: 999px; }

.tutor-card {
  margin: 0 16px 14px; background: var(--card-bg); border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0, 119, 200, 0.08); border: 1px solid #e0f2fe;
  overflow: hidden; display: flex; flex-direction: column;
}

.tutor-header {
  background: linear-gradient(90deg, #0284c7 0%, #0099ff 100%);
  padding: 10px 16px; color: #fff; font-size: 0.95rem; font-weight: 700;
  display: flex; justify-content: space-between; align-items: center;
}
.tutor-close { background: none; border: none; color: #fff; font-size: 1.1rem; cursor: pointer; opacity: 0.8; }

.tutor-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; max-height: 270px; overflow-y: auto; }
.chat-row { display: flex; gap: 10px; align-items: flex-start; }
.chat-bubble { background: var(--bubble-bg); color: #0f172a; padding: 10px 14px; border-radius: 16px 16px 16px 4px; font-size: 0.87rem; line-height: 1.45; max-width: 86%; word-wrap: break-word; }
.chat-bubble img { max-width: 100%; border-radius: 8px; margin-top: 6px; }
.user-row { justify-content: flex-end; }
.user-bubble { background: var(--bubble-user); color: #fff; border-radius: 16px 16px 4px 16px; }

.audio-playing-indicator {
  display: none; align-items: center; justify-content: space-between;
  background: #f0fdf4; border: 1px solid #bbf7d0; padding: 5px 12px;
  border-radius: 10px; font-size: 0.75rem; color: #166534;
}
.audio-playing-indicator button { background: #ef4444; border: none; color: #fff; font-size: 0.7rem; padding: 2px 7px; border-radius: 4px; cursor: pointer; }

.quick-links-label { font-size: 0.76rem; font-weight: 600; color: #64748b; margin-top: 4px; }
.quick-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.tag-pill { background: #f1f5f9; color: #334155; padding: 6px 12px; border-radius: 999px; font-size: 0.77rem; font-weight: 600; cursor: pointer; border: 1px solid #e2e8f0; }

.tutor-footer { padding: 10px 14px 14px; border-top: 1px solid #f1f5f9; display: flex; flex-direction: column; gap: 8px; }
.image-preview-container { display: none; position: relative; align-self: flex-start; }
.image-preview-container img { max-height: 60px; border-radius: 8px; border: 1px solid #cbd5e1; }
.image-preview-container button { position: absolute; top: -6px; right: -6px; background: #ef4444; color: #fff; border: none; border-radius: 50%; width: 18px; height: 18px; font-size: 0.6rem; cursor: pointer; display: grid; place-items: center; }

.input-field-wrapper { display: flex; align-items: center; background: #f8fafc; border: 1.5px solid #cbd5e1; border-radius: 14px; padding: 4px 6px 4px 6px; gap: 6px; }
.topic-input { flex: 1; border: none; background: transparent; outline: none; font-size: 0.88rem; color: #0f172a; }
.icon-btn-ui { background: none; border: none; cursor: pointer; font-size: 1.1rem; color: #64748b; display: grid; place-items: center; padding: 4px; }
.icon-btn-ui.active { color: #ef4444; animation: pulse 1s infinite alternate; }
.ask-btn { background: #0284c7; color: #fff; border: none; border-radius: 10px; padding: 8px 12px; font-size: 0.76rem; font-weight: 800; cursor: pointer; }

.dashboard-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; padding: 0 16px 20px; }
.info-card { background: var(--card-bg); border-radius: 16px; padding: 12px 14px; border: 1px solid var(--border-light); display: flex; flex-direction: column; justify-content: space-between; }
.info-title { font-size: 0.75rem; font-weight: 800; color: #334155; display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.topic-item { background: #f8fafc; padding: 6px 10px; border-radius: 10px; font-size: 0.74rem; font-weight: 600; color: #0284c7; display: flex; justify-content: space-between; align-items: center; margin-top: 6px; cursor: pointer; }
.chart-sub { font-size: 0.65rem; color: var(--text-muted); }
.chart-bars { display: flex; align-items: flex-end; height: 48px; gap: 4px; margin-top: 6px; }
.bar { flex: 1; background: #38bdf8; border-radius: 3px 3px 0 0; }

.bottom-nav { margin-top: auto; background: #ffffff; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-around; padding: 10px 0 14px; }
.nav-item { display: flex; flex-direction: column; align-items: center; gap: 3px; font-size: 0.68rem; font-weight: 600; color: #94a3b8; cursor: pointer; }
.nav-item.active { color: #0284c7; }
.nav-icon { width: 22px; height: 22px; }

@keyframes pulse { 0% { transform: scale(1); } 100% { transform: scale(1.2); } }
</style>
</head>
<body>

<div class="mobile-shell">
  <header>
    <a href="#" class="brand-wrap">
      <svg class="logo-icon" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs><linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#0284c7"/><stop offset="50%" stop-color="#0066cc"/><stop offset="100%" stop-color="#38bdf8"/></linearGradient></defs>
        <path d="M72 32C68 20 54 16 42 18C28 20 20 32 24 46C28 60 52 56 64 64C74 70 72 82 60 84C46 86 34 78 30 68" stroke="url(#blueGrad)" stroke-width="14" stroke-linecap="round"/>
        <path d="M42 34C50 34 60 40 60 48" stroke="#ffffff" stroke-width="4" stroke-linecap="round"/>
        <circle cx="62" cy="48" r="5" fill="#38bdf8"/><circle cx="34" cy="54" r="5" fill="#0284c7"/>
      </svg>
      <div class="brand-text">SARAL <span>AI</span></div>
    </a>
    <div class="header-right">
      <div class="lang-selector">
        <button class="lang-chip active" id="b-en" onclick="setLang('en')">EN</button>
        <button class="lang-chip" id="b-hi" onclick="setLang('hi')">हिन्दी</button>
        <button class="lang-chip" id="b-gu" onclick="setLang('gu')">ગુજ</button>
      </div>
    </div>
  </header>

  <div class="hero-content">
    <h1 id="hero-title">Welcome, Alex!</h1>
    <p id="hero-subtitle">Let's make learning simple.</p>
    <div class="dev-pill">✨ Engineered by Avdhesh & Friend</div>
  </div>

  <div class="tutor-card">
    <div class="tutor-header">
      <span>AI Tutor</span>
      <button class="tutor-close" onclick="resetChat()">✕</button>
    </div>

    <div class="tutor-body" id="chat-stream">
      <div class="chat-row">
        <svg width="24" height="24" viewBox="0 0 100 100" fill="none"><path d="M72 32C68 20 54 16 42 18C28 20 20 32 24 46C28 60 52 56 64 64C74 70 72 82 60 84C46 86 34 78 30 68" stroke="#0284c7" stroke-width="18" stroke-linecap="round"/></svg>
        <div class="chat-bubble" id="welcome-msg">Hello Alex! What can I simplify for you today? 🎓</div>
      </div>
    </div>

    <div style="padding: 0 14px 6px;">
      <div class="audio-playing-indicator" id="tts-audio-indicator">
        <span>🔊 <i>SARAL is speaking naturally...</i></span>
        <button onclick="stopTTS()">Stop ⏹️</button>
      </div>
    </div>

    <div style="padding: 0 16px 8px;">
      <div class="quick-links-label" id="quick-label">Quick links for you:</div>
      <div class="quick-tags" id="quick-tags-container"></div>
    </div>

    <div class="tutor-footer">
      <div class="image-preview-container" id="img-preview-box">
        <img id="img-preview" src="">
        <button onclick="clearImage()">✖</button>
      </div>
      
      <div class="input-field-wrapper">
        <button class="icon-btn-ui" onclick="document.getElementById('image-upload').click()" title="Attach Image">📷</button>
        <input type="file" id="image-upload" accept="image/*" style="display: none;" onchange="handleImage(event)">
        
        <button class="icon-btn-ui" id="mic-btn" onclick="toggleVoice()" title="Tap to Speak">🎤</button>
        
        <input type="text" id="user-input" class="topic-input" placeholder="Type a topic or concept..." onkeypress="if(event.key==='Enter')sendPrompt()">
        <button class="ask-btn" onclick="sendPrompt()">ASK</button>
      </div>
    </div>
  </div>

  <div class="dashboard-grid">
    <div class="info-card">
      <div>
        <div class="info-title"><span>RECOMMENDED</span><span>›</span></div>
        <div class="topic-item" onclick="quickAsk('Explain Quantum Entanglement in simple terms: ')"><span>Quantum Entanglement</span><span>›</span></div>
        <div class="topic-item" onclick="quickAsk('Summarize the History of Art: ')"><span>History of Art</span><span>›</span></div>
      </div>
    </div>
    <div class="info-card">
      <div class="info-title"><span>PROGRESS & GOALS</span></div>
      <div class="chart-sub">Weekly learning hours</div>
      <div class="chart-bars">
        <div class="bar" style="height: 40%;"></div>
        <div class="bar" style="height: 65%;"></div>
        <div class="bar" style="height: 35%;"></div>
        <div class="bar" style="height: 85%;"></div>
        <div class="bar" style="height: 55%;"></div>
      </div>
    </div>
  </div>

  <nav class="bottom-nav">
    <div class="nav-item active">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path></svg>
      <span>Dashboard</span>
    </div>
    <div class="nav-item">
      <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="10" rx="2"></rect></svg>
      <span>AI Tutor</span>
    </div>
  </nav>
</div>

<script>
const I18N = {
  en: {
    locale: 'en', title: 'Welcome, Alex!', subtitle: "Let's make learning simple.",
    greeting: "Hello Alex! What can I simplify for you today? 🎓", placeholder: "Type or attach an image...",
    quick: "Quick links for you:", tags: ["Calculus", "Quantum Mechanics", "Data Structures", "Who made you?"]
  },
  hi: {
    locale: 'hi', title: 'नमस्ते, Alex!', subtitle: 'पढ़ाई को बनाते हैं बेहद आसान।',
    greeting: 'नमस्ते Alex! आज मैं आपके लिए क्या आसान बना सकता हूँ? 🎓', placeholder: 'प्रश्न लिखें या फोटो अपलोड करें...',
    quick: 'आपके लिए त्वरित लिंक्स:', tags: ["कैलकुलस", "क्वांटम भौतिकी", "डाटा स्ट्रक्चर्स", "निर्माता कौन हैं?"]
  },
  gu: {
    locale: 'gu', title: 'નમસ્તે, Alex!', subtitle: 'ચાલો ભણતરને એકદમ સરળ બનાવીએ.',
    greeting: 'નમસ્તે Alex! આજે હું તમારા માટે શું સરળ બનાવી શકું? 🎓', placeholder: 'પ્રશ્ન લખો અથવા ફોટો અપલોડ કરો...',
    quick: 'તમારા માટે ઝડપી લિંક્સ:', tags: ["કલનશાસ્ત્ર", "ક્વોન્ટમ ફિઝિક્સ", "ડેટા સ્ટ્રક્ચર", "તમને કોણે બનાવ્યું?"]
  }
};

let curLang = 'en', isListening = false, activeAudio = null, currentImageBase64 = null;
const inputField = document.getElementById('user-input');
const chatStream = document.getElementById('chat-stream');
const micBtn = document.getElementById('mic-btn');
const ttsIndicator = document.getElementById('tts-audio-indicator');

function handleImage(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {
    currentImageBase64 = e.target.result;
    document.getElementById('img-preview').src = currentImageBase64;
    document.getElementById('img-preview-box').style.display = 'block';
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  currentImageBase64 = null;
  document.getElementById('img-preview-box').style.display = 'none';
  document.getElementById('img-preview').src = '';
  document.getElementById('image-upload').value = '';
}

function stopTTS() {
  if (activeAudio) { activeAudio.pause(); activeAudio = null; }
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  ttsIndicator.style.display = 'none';
}

// Ensure JS TTS strips special characters and emojis, but retains math operators
function cleanForTTS(text) {
  if (!text) return '';
  return text
    .replace(/```[\\s\\S]*?```/g, '')
    .replace(/\\[([^\]]+)\\]\\([^\\)]+\\)/g, '$1')
    .replace(/[\\/\\{\\}\\:\\;_\\#\\@\\*]/g, ' ') 
    .replace(/[\\u{1F000}-\\u{1FFFF}]/gu, '')
    .replace(/[\\u20a0-\\u32ff]/g, '')
    .replace(/\\s+/g, ' ')
    .trim();
}

function playNaturalVoice(text, langCode) {
  stopTTS();
  ttsIndicator.style.display = 'flex';
  fetch('/tts', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ text: text, lang: langCode })
  })
  .then(resp => {
    if (resp.headers.get("content-type")?.includes("audio")) return resp.blob();
    throw new Error("Fallback browser voice");
  })
  .then(blob => {
    const audioUrl = URL.createObjectURL(blob);
    activeAudio = new Audio(audioUrl);
    activeAudio.onended = () => { ttsIndicator.style.display = 'none'; };
    activeAudio.play();
  })
  .catch(() => {
    if ('speechSynthesis' in window) {
      const clean = cleanForTTS(text);
      const u = new SpeechSynthesisUtterance(clean);
      u.lang = langCode === 'hi' ? 'hi-IN' : (langCode === 'gu' ? 'gu-IN' : 'en-IN');
      u.rate = 0.95;
      u.onend = () => { ttsIndicator.style.display = 'none'; };
      window.speechSynthesis.speak(u);
    } else {
      ttsIndicator.style.display = 'none';
    }
  });
}

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = SpeechRecognition ? new SpeechRecognition() : null;
if (recognition) {
  recognition.onstart = () => { isListening = true; micBtn.classList.add('active'); };
  recognition.onend = () => { isListening = false; micBtn.classList.remove('active'); };
  recognition.onresult = (e) => { inputField.value = e.results[0][0].transcript; sendPrompt(); };
}

function toggleVoice() {
  if (!recognition) return alert('Speech recognition works best in Chrome on Android.');
  if (isListening) recognition.stop();
  else { recognition.lang = curLang === 'hi' ? 'hi-IN' : (curLang === 'gu' ? 'gu-IN' : 'en-IN'); recognition.start(); }
}

function setLang(k) {
  curLang = k;
  stopTTS();
  ['en', 'hi', 'gu'].forEach(l => document.getElementById('b-' + l).classList.toggle('active', l === k));
  const data = I18N[k];
  document.getElementById('hero-title').innerText = data.title;
  document.getElementById('hero-subtitle').innerText = data.subtitle;
  document.getElementById('welcome-msg').innerText = data.greeting;
  document.getElementById('quick-label').innerText = data.quick;
  inputField.placeholder = data.placeholder;

  const container = document.getElementById('quick-tags-container');
  container.innerHTML = '';
  data.tags.forEach(tag => {
    const pill = document.createElement('div');
    pill.className = 'tag-pill'; pill.innerText = tag;
    pill.onclick = () => { inputField.value = tag.includes('?') ? tag : `Explain ${tag} simply: `; inputField.focus(); };
    container.appendChild(pill);
  });
}

function quickAsk(text) { inputField.value = text; inputField.focus(); }
function resetChat() {
  stopTTS(); clearImage();
  chatStream.innerHTML = `<div class="chat-row"><svg width="24" height="24" viewBox="0 0 100 100" fill="none"><path d="M72 32C68 20 54 16 42 18C28 20 20 32 24 46C28 60 52 56 64 64C74 70 72 82 60 84C46 86 34 78 30 68" stroke="#0284c7" stroke-width="18" stroke-linecap="round"/></svg><div class="chat-bubble">${I18N[curLang].greeting}</div></div>`;
}

async function sendPrompt() {
  const q = inputField.value.trim();
  const imageAttached = currentImageBase64; 

  if (!q && !imageAttached) return;

  stopTTS();
  inputField.value = '';
  
  let userBubbleHtml = `<div class="chat-bubble user-bubble">${q}`;
  if (imageAttached) {
    userBubbleHtml += `<br><img src="${imageAttached}">`;
  }
  userBubbleHtml += `</div>`;

  chatStream.innerHTML += `<div class="chat-row user-row">${userBubbleHtml}</div>`;

  const thinkingId = 'think-' + Date.now();
  chatStream.innerHTML += `<div class="chat-row" id="${thinkingId}"><div class="chat-bubble" style="color:var(--primary); font-style:italic;">SARAL is simplifying...</div></div>`;
  chatStream.scrollTop = chatStream.scrollHeight;

  const payload = { 
    prompt: q || "Please explain this image.", 
    language: I18N[curLang].locale === 'hi' ? 'Hindi' : (I18N[curLang].locale === 'gu' ? 'Gujarati' : 'English')
  };
  if (imageAttached) payload.image = imageAttached;
  
  clearImage(); 

  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    const elem = document.getElementById(thinkingId);
    if (elem) elem.remove();

    chatStream.innerHTML += `<div class="chat-row"><svg width="24" height="24" viewBox="0 0 100 100" fill="none"><path d="M72 32C68 20 54 16 42 18C28 20 20 32 24 46C28 60 52 56 64 64C74 70 72 82 60 84C46 86 34 78 30 68" stroke="#0284c7" stroke-width="18" stroke-linecap="round"/></svg><div class="chat-bubble">${data.reply.replace(/\\n/g, '<br>')}</div></div>`;
    chatStream.scrollTop = chatStream.scrollHeight;
    playNaturalVoice(data.reply, I18N[curLang].locale);
  } catch (err) {
    const elem = document.getElementById(thinkingId);
    if (elem) elem.innerHTML = `<div class="chat-bubble" style="color:#ef4444;">Error connecting to server.</div>`;
  }
}

window.addEventListener('DOMContentLoaded', () => setLang('en'));
</script>
</body>
</html>"""

# ==============================================================================
# 3. ROUTES & SERVING
# ==============================================================================
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(force=True, silent=True) or {}
    prompt = data.get('prompt', '')
    language = data.get('language', 'English')
    image = data.get('image', None)
    
    reply = query_groq(prompt, target_lang=language, image_base64=image)
    return jsonify({'reply': reply})

@app.route('/tts', methods=['POST'])
def tts():
    if not USE_NATURAL_AUDIO:
        return jsonify({'error': 'gTTS not installed'}), 400

    data = request.get_json(force=True, silent=True) or {}
    raw_text = data.get('text', '')
    lang = data.get('lang', 'en')

    clean_text = clean_text_for_speech(raw_text)
    if not clean_text:
        return jsonify({'error': 'No text provided'}), 400

    sentences = re.split(r'[.!?।]\s*', clean_text)
    short_text = ". ".join([s for s in sentences if s][:3]) + "."

    try:
        tts_obj = gTTS(text=short_text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts_obj.write_to_fp(fp)
        fp.seek(0)
        return send_file(fp, mimetype='audio/mpeg')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)