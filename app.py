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
# 1. GROQ CONFIGURATION (SINGLE MODEL: GPT-OSS-120B)
# ==============================================================================
GROQ_API_KEY="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"
GROQ_MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """
You are SARAL AI (सरल), a friendly, encouraging, and intelligent personal AI tutor.
You were created and engineered by Avdhesh.
Your motto is 'Study Smarter • Learn Faster • Grow Together'.

Persona & Rules:
- If asked who made, built, or developed you, proudly credit Avdhesh.
- Help students with clear, intuitive, and accurate explanations.
- Keep spoken answers crisp (1-3 sentences) or use structured bullet points for notes.
- Fluent in English, Hindi (हिन्दी), and Gujarati (ગુજરાતી). Always reply in the requested target language.
- AVOID special characters: Do not use \ / { } : ; _ # @ * in your text.
- MATH SYMBOLS: Use standard symbols (÷, ×, -, +) for mathematical equations.
- EMOJIS: Use emojis in your text output to make it friendly and engaging.
"""

chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

def clean_text_for_speech(text):
    if not text:
        return ""
    t = re.sub(r'```[\s\S]*?```', '', text)
    t = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', t)
    t = re.sub(r'[\\/\{\}\:\;_\#\@\*]', ' ', t)
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    t = re.sub(r'[\u20a0-\u32ff\ud83c-\ud83e]', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def query_groq(prompt, target_lang="English"):
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":
        return "Please paste your active Groq API Key (gsk_...) in app.py or environment variables."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    formatted_prompt = f"[Target Language: {target_lang}]\nQuestion/Doubt: {prompt}"
    current_msg = {"role": "user", "content": formatted_prompt}

    temp_history = chat_history + [current_msg]
    payload = {
        "model": GROQ_MODEL,
        "messages": temp_history,
        "temperature": 0.5,
        "max_tokens": 700
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            reply = res.json()["choices"][0]["message"]["content"]
            chat_history.append(current_msg)
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
# 2. FRONTEND TEMPLATE (EXACT LOGO MATCH + FORCED ONBOARDING FIX)
# ==============================================================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>SARAL AI</title>
<style>
:root {
  --bg-color: #ffffff;
  --bg-gradient: linear-gradient(180deg, #ffffff 0%, #f4f8fc 100%);
  --text-main: #1f1f1f;
  --text-muted: #444746;
  --input-bg: #f0f4f9;
  --primary-blue: #0b57d0;
  --bubble-user: #e3e3e3;
  --bubble-ai: transparent;
}

* { box-sizing: border-box; margin: 0; padding: 0; font-family: "Google Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

html, body {
  background: var(--bg-gradient);
  color: var(--text-main);
  height: 100vh;
  height: 100dvh;
  width: 100%;
  display: flex;
  justify-content: center;
  overflow: hidden;
}

.mobile-shell {
  width: 100%;
  max-width: 480px;
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  background: transparent;
}

/* Onboarding Screen */
#onboarding-screen {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #ffffff;
  z-index: 9999; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 24px;
  transition: opacity 0.4s ease;
}
.onboard-logo { width: 84px; height: 84px; margin-bottom: 20px; animation: pulse 2s infinite alternate; }
#onboarding-screen h1 { font-size: 1.8rem; font-weight: 400; color: #1f1f1f; text-align: center; margin-bottom: 8px; }
#onboarding-screen p { font-size: 0.9rem; color: #444746; margin-bottom: 32px; text-align: center; }
.name-input {
  width: 100%; max-width: 320px; background: var(--input-bg); border: none; border-radius: 28px;
  padding: 16px 24px; font-size: 1rem; color: #1f1f1f; outline: none; margin-bottom: 24px; text-align: center;
}
.get-started-btn {
  background: #0b57d0; color: #ffffff; border: none; border-radius: 28px; padding: 14px 32px;
  font-size: 1rem; cursor: pointer; transition: background 0.2s; font-weight: 500;
}
.get-started-btn:hover { background: #0842a0; }
.credits-text { position: absolute; bottom: 24px; font-size: 0.75rem; color: #747775; }

/* Header */
header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; background: transparent; flex-shrink: 0;
}
.menu-btn { background: none; border: none; font-size: 1.4rem; color: #444746; cursor: pointer; padding: 4px 8px; }
.model-selector { display: flex; align-items: center; gap: 8px; font-size: 1.05rem; color: #1f1f1f; font-weight: 600; letter-spacing: -0.3px; }
.lang-selector { display: flex; background: var(--input-bg); border-radius: 999px; padding: 2px; }
.lang-chip { border: none; background: transparent; color: #444746; font-size: 0.75rem; padding: 4px 10px; border-radius: 999px; cursor: pointer; font-weight: 500; }
.lang-chip.active { background: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); color: #1f1f1f; }

/* Main Workspace */
main { flex: 1; overflow-y: auto; display: flex; flex-direction: column; scroll-behavior: smooth; }

/* Home View (Greeting & Suggestions) */
#home-view { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; padding: 20px; }
.big-logo { width: 72px; height: 72px; margin-bottom: 16px; }
.greeting-text { font-size: 1.85rem; font-weight: 400; color: #1f1f1f; text-align: center; line-height: 1.3; margin-bottom: 32px; }
.greeting-text span { background: -webkit-linear-gradient(45deg, #00d2ff, #3a7bd5, #9b51e0); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

.suggestions-list { width: 100%; max-width: 360px; display: flex; flex-direction: column; gap: 12px; }
.suggestion-item {
  display: flex; align-items: center; gap: 16px; background: transparent; padding: 12px 16px;
  border-radius: 16px; cursor: pointer; transition: background 0.2s; border: 1px solid #e0e0e0;
}
.suggestion-item:hover { background: var(--input-bg); }
.suggestion-icon { color: #444746; display: flex; align-items: center; justify-content: center; }
.suggestion-text { font-size: 0.9rem; color: #444746; font-weight: 400; }

/* Chat View */
#chat-view { display: none; flex-direction: column; padding: 16px 16px 24px; gap: 24px; }
.chat-row { display: flex; flex-direction: column; width: 100%; }
.user-row { align-items: flex-end; }
.ai-row { align-items: flex-start; }
.chat-bubble { max-width: 90%; font-size: 1rem; line-height: 1.5; word-wrap: break-word; }
.user-bubble { background: var(--input-bg); color: #1f1f1f; padding: 12px 18px; border-radius: 24px 24px 4px 24px; }
.ai-bubble { background: var(--bubble-ai); color: #1f1f1f; padding: 4px 8px; display: flex; gap: 12px; }
.ai-avatar { width: 30px; height: 30px; flex-shrink: 0; margin-top: 4px; }

/* Docked Bottom Input Area */
.input-container {
  width: 100%;
  padding: 8px 16px max(16px, env(safe-area-inset-bottom));
  background: #f4f8fc;
  flex-shrink: 0;
}
.audio-indicator {
  display: none; align-items: center; justify-content: space-between; background: #e8f0fe;
  padding: 8px 16px; border-radius: 20px; margin-bottom: 10px; font-size: 0.8rem; color: #1967d2;
}
.audio-indicator button { background: none; border: none; color: #d93025; font-weight: 600; cursor: pointer; }

.pill-input {
  display: flex; align-items: center; background: var(--input-bg); border-radius: 32px;
  padding: 6px 10px 6px 20px; gap: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  border: 1px solid #e0e6ed;
}
.action-icon {
  background: none; border: none; color: #444746; font-size: 1.3rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center; width: 38px; height: 38px; border-radius: 50%;
}
.action-icon:hover { background: #e3e3e3; }
.action-icon.recording { color: #d93025; animation: pulse 1s infinite alternate; }
.text-input { flex: 1; border: none; background: transparent; outline: none; font-size: 1rem; color: #1f1f1f; padding: 8px 0; }
.send-icon { color: var(--primary-blue); display: none; }

@keyframes pulse { 0% { transform: scale(1); opacity: 0.9; } 100% { transform: scale(1.05); opacity: 1; } }
</style>
</head>
<body>

<!-- Exact Saral Logo Vector Gradients & Definitions -->
<svg style="width:0;height:0;position:absolute;" aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="saralGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00d2ff" />
      <stop offset="50%" stop-color="#3a7bd5" />
      <stop offset="100%" stop-color="#b857eb" />
    </linearGradient>
    <linearGradient id="starGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f2fe" />
      <stop offset="100%" stop-color="#9b51e0" />
    </linearGradient>
  </defs>
</svg>

<!-- Reusable Saral Logo Template matching your exact design -->
<script>
const saralLogoSvg = `<svg class="ai-avatar" viewBox="0 0 500 500" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M120 180C140 100 240 70 340 100C410 120 440 170 410 220C380 270 280 230 220 230C160 230 110 210 120 180Z" fill="url(#saralGrad)"/>
  <path d="M260 170C260 170 285 205 315 210C285 215 260 250 260 250C260 250 235 215 205 210C235 205 260 170 260 170Z" fill="url(#starGrad)"/>
  <path d="M380 320C360 400 260 430 160 400C90 380 60 330 90 280C120 230 220 270 280 270C340 270 390 290 380 320Z" fill="url(#saralGrad)"/>
</svg>`;
</script>

<div class="mobile-shell">
  
  <!-- Onboarding Screen -->
  <div id="onboarding-screen" style="display: flex;">
    <svg class="onboard-logo" viewBox="0 0 500 500" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M120 180C140 100 240 70 340 100C410 120 440 170 410 220C380 270 280 230 220 230C160 230 110 210 120 180Z" fill="url(#saralGrad)"/>
      <path d="M260 170C260 170 285 205 315 210C285 215 260 250 260 250C260 250 235 215 205 210C235 205 260 170 260 170Z" fill="url(#starGrad)"/>
      <path d="M380 320C360 400 260 430 160 400C90 380 60 330 90 280C120 230 220 270 280 270C340 270 390 290 380 320Z" fill="url(#saralGrad)"/>
    </svg>
    <h1>Welcome to SARAL</h1>
    <p>Your personal AI study companion.</p>
    <input type="text" id="user-name-input" class="name-input" placeholder="What should I call you?" value="" onkeypress="if(event.key==='Enter')saveName()">
    <button class="get-started-btn" onclick="saveName()">Get Started</button>
    <div class="credits-text">Engineered by Avdhesh</div>
  </div>

  <!-- Header -->
  <header>
    <button class="menu-btn" onclick="resetOrChangeName()" title="New Chat / Change Name">☰</button>
    <div class="model-selector">
      <svg width="24" height="24" viewBox="0 0 500 500" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M120 180C140 100 240 70 340 100C410 120 440 170 410 220C380 270 280 230 220 230C160 230 110 210 120 180Z" fill="url(#saralGrad)"/>
        <path d="M260 170C260 170 285 205 315 210C285 215 260 250 260 250C260 250 235 215 205 210C235 205 260 170 260 170Z" fill="url(#starGrad)"/>
        <path d="M380 320C360 400 260 430 160 400C90 380 60 330 90 280C120 230 220 270 280 270C340 270 390 290 380 320Z" fill="url(#saralGrad)"/>
      </svg>
      SARAL AI
    </div>
    <div class="lang-selector">
      <button class="lang-chip active" id="b-en" onclick="setLang('en')">EN</button>
      <button class="lang-chip" id="b-hi" onclick="setLang('hi')">HI</button>
      <button class="lang-chip" id="b-gu" onclick="setLang('gu')">GU</button>
    </div>
  </header>

  <!-- Workspace -->
  <main id="main-scroll">
    
    <!-- Home View -->
    <div id="home-view">
      <svg class="big-logo" viewBox="0 0 500 500" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M120 180C140 100 240 70 340 100C410 120 440 170 410 220C380 270 280 230 220 230C160 230 110 210 120 180Z" fill="url(#saralGrad)"/>
        <path d="M260 170C260 170 285 205 315 210C285 215 260 250 260 250C260 250 235 215 205 210C235 205 260 170 260 170Z" fill="url(#starGrad)"/>
        <path d="M380 320C360 400 260 430 160 400C90 380 60 330 90 280C120 230 220 270 280 270C340 270 390 290 380 320Z" fill="url(#saralGrad)"/>
      </svg>
      <h1 class="greeting-text" id="dynamic-greeting">What can I help with,<br><span>Student</span>?</h1>
      
      <div class="suggestions-list" id="suggestions-container">
        <!-- Rendered via JS -->
      </div>
    </div>

    <!-- Chat View -->
    <div id="chat-view"></div>
  </main>

  <!-- Docked Input Bottom Bar -->
  <div class="input-container">
    <div class="audio-indicator" id="tts-audio-indicator">
      <span>🔊 <i>SARAL is speaking...</i></span>
      <button onclick="stopTTS()">Stop</button>
    </div>

    <div class="pill-input">
      <input type="text" id="user-input" class="text-input" placeholder="Ask SARAL" oninput="toggleSendIcon()" onkeypress="if(event.key==='Enter')sendPrompt()">
      
      <button class="action-icon" id="mic-btn" onclick="toggleVoice()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
      </button>
      
      <button class="action-icon send-icon" id="send-btn" onclick="sendPrompt()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"></path></svg>
      </button>
    </div>
  </div>

</div>

<script>
const I18N = {
  en: {
    locale: 'en',
    greeting: "What can I help with,<br><span>{name}</span>?",
    placeholder: "Ask SARAL",
    suggs: [
      { text: "Help me solve my math homework", prompt: "Help me solve my math homework: " },
      { text: "Create quick study notes", prompt: "Create quick study notes for: " },
      { text: "Explain a complex concept simply", prompt: "Explain this concept simply: " }
    ]
  },
  hi: {
    locale: 'hi',
    greeting: "मैं आपकी क्या मदद कर सकता हूँ,<br><span>{name}</span>?",
    placeholder: "SARAL से पूछें",
    suggs: [
      { text: "मेरा गणित का होमवर्क हल करवाएं", prompt: "मेरा गणित का होमवर्क हल करवाएं: " },
      { text: "रिविज़न के लिए नोट्स बनाएं", prompt: "इसके रिविज़न नोट्स बनाएं: " },
      { text: "कठिन विषय को आसानी से समझाएं", prompt: "इस विषय को आसानी से समझाएं: " }
    ]
  },
  gu: {
    locale: 'gu',
    greeting: "હું તમારી શું મદદ કરી શકું,<br><span>{name}</span>?",
    placeholder: "SARAL ને પૂછો",
    suggs: [
      { text: "મારું ગણિતનું હોમવર્ક સોલ્વ કરાવો", prompt: "મારું ગણિતનું હોમવર્ક સોલ્વ કરાવો: " },
      { text: "ઝડપી રિવિઝન નોટ્સ બનાવો", prompt: "આના માટે રિવિઝન નોટ્સ બનાવો: " },
      { text: "અઘરા વિષયને સરળતાથી સમજાવો", prompt: "આ વિષયને સરળતાથી સમજાવો: " }
    ]
  }
};

let curLang = 'en', isListening = false, activeAudio = null, userName = "Student";
const inputField = document.getElementById('user-input');
const chatStream = document.getElementById('chat-view');
const homeView = document.getElementById('home-view');
const micBtn = document.getElementById('mic-btn');
const sendBtn = document.getElementById('send-btn');
const ttsIndicator = document.getElementById('tts-audio-indicator');
const mainScroll = document.getElementById('main-scroll');

// --- Onboarding Logic ---
function initApp() {
  const savedName = localStorage.getItem('saralUserName');
  const onboarding = document.getElementById('onboarding-screen');
  if (savedName) {
    userName = savedName;
    onboarding.style.display = 'none';
    setLang('en');
  } else {
    onboarding.style.display = 'flex';
    onboarding.style.opacity = '1';
    document.getElementById('user-name-input').value = "";
  }
}

function saveName() {
  const inputName = document.getElementById('user-name-input').value.trim();
  if (inputName) {
    userName = inputName;
    localStorage.setItem('saralUserName', userName);
    const onboarding = document.getElementById('onboarding-screen');
    onboarding.style.opacity = '0';
    setTimeout(() => {
      onboarding.style.display = 'none';
      setLang(curLang);
    }, 400);
  }
}

function resetOrChangeName() {
  stopTTS();
  chatStream.innerHTML = '';
  chatStream.style.display = 'none';
  homeView.style.display = 'flex';
  localStorage.removeItem('saralUserName');
  const onboard = document.getElementById('onboarding-screen');
  document.getElementById('user-name-input').value = '';
  onboard.style.display = 'flex';
  onboard.style.opacity = '1';
}

// --- Input Toggle Logic ---
function toggleSendIcon() {
  if (inputField.value.trim().length > 0) {
    micBtn.style.display = 'none';
    sendBtn.style.display = 'flex';
  } else {
    micBtn.style.display = 'flex';
    sendBtn.style.display = 'none';
  }
}

// --- TTS Logic ---
function stopTTS() {
  if (activeAudio) { activeAudio.pause(); activeAudio = null; }
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  ttsIndicator.style.display = 'none';
}

function cleanForTTS(text) {
  if (!text) return '';
  return text.replace(/```[\s\S]*?```/g, '').replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1')
    .replace(/[\\/\{\}\:\;_\#\@\*]/g, ' ') 
    .replace(/[\u{1F000}-\u{1FFFF}]/gu, '').replace(/[\u20a0-\u32ff]/g, '')
    .replace(/\s+/g, ' ').trim();
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

// --- Speech Recognition Logic ---
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = SpeechRecognition ? new SpeechRecognition() : null;
if (recognition) {
  recognition.onstart = () => { isListening = true; micBtn.classList.add('recording'); };
  recognition.onend = () => { isListening = false; micBtn.classList.remove('recording'); };
  recognition.onresult = (e) => { 
    inputField.value = e.results[0][0].transcript; 
    toggleSendIcon();
    sendPrompt(); 
  };
}

function toggleVoice() {
  if (!recognition) return alert('Speech recognition works best in Chrome on Android.');
  if (isListening) recognition.stop();
  else { recognition.lang = curLang === 'hi' ? 'hi-IN' : (curLang === 'gu' ? 'gu-IN' : 'en-IN'); recognition.start(); }
}

// --- UI Updates ---
function setLang(k) {
  curLang = k;
  stopTTS();
  ['en', 'hi', 'gu'].forEach(l => document.getElementById('b-' + l).classList.remove('active'));
  document.getElementById('b-' + k).classList.add('active');
  
  const data = I18N[k];
  document.getElementById('dynamic-greeting').innerHTML = data.greeting.replace('{name}', userName);
  inputField.placeholder = data.placeholder;

  const container = document.getElementById('suggestions-container');
  container.innerHTML = '';
  
  const icons = [
    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>`,
    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>`,
    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`
  ];

  data.suggs.forEach((sugg, idx) => {
    const el = document.createElement('div');
    el.className = 'suggestion-item';
    el.innerHTML = `<div class="suggestion-icon">${icons[idx]}</div><div class="suggestion-text">${sugg.text}</div>`;
    el.onclick = () => { inputField.value = sugg.prompt; toggleSendIcon(); inputField.focus(); };
    container.appendChild(el);
  });
}

async function sendPrompt() {
  const q = inputField.value.trim();
  if (!q) return;

  stopTTS();
  inputField.value = '';
  toggleSendIcon();
  
  homeView.style.display = 'none';
  chatStream.style.display = 'flex';
  
  chatStream.innerHTML += `<div class="chat-row user-row"><div class="chat-bubble user-bubble">${q}</div></div>`;

  const thinkingId = 'think-' + Date.now();
  chatStream.innerHTML += `
    <div class="chat-row ai-row" id="${thinkingId}">
      <div class="ai-bubble">
        ${saralLogoSvg}
        <div class="chat-bubble" style="color:var(--primary-blue); font-style:italic;">Thinking...</div>
      </div>
    </div>`;
  mainScroll.scrollTop = mainScroll.scrollHeight;

  const payload = { 
    prompt: q, 
    language: I18N[curLang].locale === 'hi' ? 'Hindi' : (I18N[curLang].locale === 'gu' ? 'Gujarati' : 'English')
  };

  try {
    const res = await fetch('/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    document.getElementById(thinkingId).remove();

    chatStream.innerHTML += `
      <div class="chat-row ai-row">
        <div class="ai-bubble">
          ${saralLogoSvg}
          <div class="chat-bubble">${data.reply.replace(/\\n/g, '<br>')}</div>
        </div>
      </div>`;
    mainScroll.scrollTop = mainScroll.scrollHeight;
    playNaturalVoice(data.reply, I18N[curLang].locale);
  } catch (err) {
    document.getElementById(thinkingId).innerHTML = `<div class="ai-bubble"><div class="chat-bubble" style="color:#d93025;">Error connecting to server.</div></div>`;
  }
}

window.addEventListener('DOMContentLoaded', initApp);
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

    reply = query_groq(prompt, target_lang=language)
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