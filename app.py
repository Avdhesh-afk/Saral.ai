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
# 1. GROQ CONFIGURATION (LOCKED TO openai/gpt-oss-120b)
# ==============================================================================
# अपनी असली Groq API Key (gsk_...) नीचे डबल कोट्स के अंदर पेस्ट करें:
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "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")

# Primary text model locked to openai/gpt-oss-120b
GROQ_TEXT_MODEL = "openai/gpt-oss-120b"

def get_active_vision_model():
    """Dynamically finds the currently supported Vision model for image uploads."""
    if not GROQ_API_KEY or GROQ_API_KEY == "PASTE_YOUR_API_KEY_HERE":
        return "llama-3.2-90b-vision-instruct"
        
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY.strip()}"}
    safe_vision_models = [
        "llama-3.2-90b-vision-instruct",
        "llama-3.2-11b-vision-instruct"
    ]
    try:
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            active_ids = [m["id"] for m in res.json().get("data", [])]
            for candidate in safe_vision_models:
                if candidate in active_ids:
                    return candidate
    except Exception:
        pass
    return "llama-3.2-90b-vision-instruct"

GROQ_VISION_MODEL = get_active_vision_model()

SYSTEM_PROMPT = """
You are KomiX, an advanced, creative, and intuitive AI-powered anime and manga creation studio.
You were created and engineered by Avdhesh.
Your motto is 'Draw Worlds • Script Stories • Code Reality'.

Persona & Rules:
- If asked who made, built, or developed you, proudly credit Avdhesh.
- Help creators with manga panel breakdowns, anime plotting, script structuring, and creative visual prompts.
- Keep spoken answers crisp (1-3 sentences) or use structured bullet points for production notes.
- Fluent in English, Hindi (हिन्दी), and Gujarati (ગુજરાતી). Always reply in the requested target language.
- AVOID special characters: Do not use \\ / { } : ; _ # @ * in your text.
- EMOJIS: Use emojis in your text output to make it creative, artistic, and engaging.
"""

chat_history = [{"role": "system", "content": SYSTEM_PROMPT}]

def clean_text_for_speech(text):
    if not text: return ""
    t = re.sub(r'```[\s\S]*?```', '', text)
    t = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', t)
    t = re.sub(r'[\\/\{\}\:\;_\#\@\*]', ' ', t)
    t = re.sub(r'[\U00010000-\U0010ffff]', '', t)
    t = re.sub(r'[\u20a0-\u32ff\ud83c-\ud83e]', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def query_groq(prompt, target_lang="English", image_base64=None):
    if not GROQ_API_KEY or GROQ_API_KEY == "PASTE_YOUR_API_KEY_HERE":
        return "Please paste your active Groq API Key (gsk_...) in app.py at line 18."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    formatted_prompt = f"[Target Language: {target_lang}]\nCreative Request: {prompt}"
    
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

    temp_history = chat_history + [current_msg]
    payload = {"model": active_model, "messages": temp_history, "temperature": 0.7, "max_tokens": 800}

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            reply = res.json()["choices"][0]["message"]["content"]
            chat_history.append({"role": "user", "content": formatted_prompt + " [Image Attached]" if image_base64 else formatted_prompt})
            chat_history.append({"role": "assistant", "content": reply})
            return reply
        else:
            try: err = res.json().get("error", {}).get("message", res.text)
            except: err = res.text
            return f"Groq Error ({res.status_code}): {err}"
    except Exception as e:
        return f"Request Error: {str(e)}"

app = Flask(__name__)

# ==============================================================================
# 2. FRONTEND TEMPLATE (WITH HTML5 CANVAS EXPORT ENGINE)
# ==============================================================================
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>KomiX</title>
<style>
:root {
  --bg-color: #0c0f17;
  --bg-gradient: linear-gradient(180deg, #0c0f17 0%, #161b26 100%);
  --text-main: #f3f4f6;
  --text-muted: #9ca3af;
  --input-bg: #1f2937;
  --primary-accent: #8b5cf6;
  --bubble-user: #374151;
  --bubble-ai: transparent;
}

* { box-sizing: border-box; margin: 0; padding: 0; font-family: "Google Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
body { background: var(--bg-gradient); color: var(--text-main); height: 100vh; display: flex; justify-content: center; overflow: hidden; }

.mobile-shell {
  width: 100%; max-width: 480px; height: 100%; display: flex; flex-direction: column; position: relative; background: transparent;
}

/* Onboarding Screen */
#onboarding-screen {
  position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: #0c0f17;
  z-index: 9999; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 24px;
  transition: opacity 0.4s ease;
}
.onboard-logo { width: 72px; height: 72px; margin-bottom: 24px; animation: pulse 2s infinite alternate; }
#onboarding-screen h1 { font-size: 1.8rem; font-weight: 500; color: #f3f4f6; text-align: center; margin-bottom: 8px; }
#onboarding-screen p { font-size: 0.9rem; color: var(--text-muted); margin-bottom: 32px; text-align: center; }
.name-input {
  width: 100%; max-width: 320px; background: var(--input-bg); border: 1px solid #374151; border-radius: 28px;
  padding: 16px 24px; font-size: 1rem; color: #f3f4f6; outline: none; margin-bottom: 24px; text-align: center;
}
.get-started-btn {
  background: linear-gradient(135deg, #8b5cf6, #ec4899); color: #ffffff; border: none; border-radius: 28px; padding: 14px 32px;
  font-size: 1rem; cursor: pointer; transition: opacity 0.2s; font-weight: 600;
}
.get-started-btn:hover { opacity: 0.9; }
.credits-text { position: absolute; bottom: 24px; font-size: 0.75rem; color: #6b7280; }

/* Header */
header { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: transparent; border-bottom: 1px solid rgba(255,255,255,0.05); }
.menu-btn { background: none; border: none; font-size: 1.4rem; color: var(--text-muted); cursor: pointer; }
.model-selector { display: flex; align-items: center; gap: 8px; font-size: 1.1rem; color: #f3f4f6; font-weight: 700; letter-spacing: -0.3px; }
.lang-selector { display: flex; background: var(--input-bg); border-radius: 999px; padding: 2px; border: 1px solid #374151; }
.lang-chip { border: none; background: transparent; color: var(--text-muted); font-size: 0.75rem; padding: 4px 10px; border-radius: 999px; cursor: pointer; font-weight: 600; }
.lang-chip.active { background: #8b5cf6; color: #ffffff; box-shadow: 0 1px 3px rgba(0,0,0,0.2); }

/* Workspace Tabs Switcher */
.workspace-tabs { display: flex; background: var(--input-bg); border-radius: 12px; padding: 4px; margin: 12px 16px 4px 16px; border: 1px solid #374151; }
.tab-btn { flex: 1; background: transparent; border: none; color: var(--text-muted); padding: 8px; font-size: 0.85rem; font-weight: 600; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
.tab-btn.active { background: #8b5cf6; color: #ffffff; }

/* Main Workspace */
main { flex: 1; overflow-y: auto; display: flex; flex-direction: column; scroll-behavior: smooth; }

/* Home View (Greeting & Suggestions) */
#home-view { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: 1; padding: 20px; }
.big-logo { width: 64px; height: 64px; margin-bottom: 16px; }
.greeting-text { font-size: 1.85rem; font-weight: 400; color: #f3f4f6; text-align: center; line-height: 1.3; margin-bottom: 30px; }
.greeting-text span { background: -webkit-linear-gradient(45deg, #8b5cf6, #ec4899, #f43f5e); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

.suggestions-list { width: 100%; max-width: 360px; display: flex; flex-direction: column; gap: 12px; }
.suggestion-item {
  display: flex; align-items: center; gap: 16px; background: rgba(31, 41, 55, 0.5); padding: 14px 16px;
  border-radius: 16px; cursor: pointer; transition: background 0.2s; border: 1px solid #374151;
}
.suggestion-item:hover { background: var(--input-bg); }
.suggestion-icon { color: #8b5cf6; display: flex; align-items: center; justify-content: center; }
.suggestion-text { font-size: 0.9rem; color: #d1d5db; font-weight: 400; }

/* Chat View */
#chat-view { display: none; flex-direction: column; padding: 16px 16px 100px; gap: 24px; }
.chat-row { display: flex; flex-direction: column; width: 100%; }
.user-row { align-items: flex-end; }
.ai-row { align-items: flex-start; }
.chat-bubble { max-width: 90%; font-size: 1rem; line-height: 1.5; word-wrap: break-word; }
.user-bubble { background: var(--input-bg); color: #f3f4f6; padding: 12px 18px; border-radius: 24px 24px 4px 24px; border: 1px solid #374151; }
.user-bubble img { max-width: 100%; border-radius: 12px; margin-top: 8px; }
.ai-bubble { background: var(--bubble-ai); color: #f3f4f6; padding: 4px 8px; display: flex; gap: 12px; }
.ai-avatar { width: 28px; height: 28px; flex-shrink: 0; margin-top: 4px; }

/* Studio View (Manga Canvas Creator) */
#studio-view { display: none; flex-direction: column; padding: 16px 16px 100px; gap: 16px; height: 100%; }
.manga-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; width: 100%; }
.manga-panel {
  background: #111827; border: 2px dashed #374151; border-radius: 12px; height: 150px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative;
  cursor: pointer; transition: border-color 0.2s; overflow: hidden;
}
.manga-panel:hover { border-color: #8b5cf6; }
.manga-panel span { font-size: 0.75rem; color: #6b7280; margin-top: 4px; z-index: 2; }
.manga-panel svg { color: #4b5563; z-index: 2; }
.manga-panel input[type="text"] {
  position: absolute; bottom: 8px; left: 8px; right: 8px; background: rgba(0,0,0,0.6); border: 1px solid #374151;
  color: #fff; font-size: 0.7rem; padding: 4px 8px; border-radius: 6px; outline: none; z-index: 3; text-align: center;
}
.panel-actions { display: flex; gap: 8px; width: 100%; margin-top: 4px; }
.studio-btn {
  flex: 1; background: #1f2937; border: 1px solid #374151; color: #f3f4f6; padding: 10px;
  border-radius: 10px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: background 0.2s;
}
.studio-btn:hover { background: #374151; }
.studio-btn.primary { background: linear-gradient(135deg, #8b5cf6, #ec4899); border: none; }

/* Floating Input Area */
.input-container {
  position: absolute; bottom: 0; left: 0; width: 100%; padding: 12px 16px 20px;
  background: linear-gradient(0deg, #0c0f17 60%, transparent 100%);
}
.audio-indicator {
  display: none; align-items: center; justify-content: space-between; background: rgba(139, 92, 246, 0.15);
  border: 1px solid rgba(139, 92, 246, 0.3); padding: 8px 16px; border-radius: 20px; margin-bottom: 12px; font-size: 0.8rem; color: #c084fc;
}
.audio-indicator button { background: none; border: none; color: #f43f5e; font-weight: 600; cursor: pointer; }
.image-preview-box { display: none; position: relative; width: max-content; margin-bottom: 12px; padding-left: 12px; }
.image-preview-box img { max-height: 80px; border-radius: 12px; border: 1px solid #374151; }
.image-preview-box button {
  position: absolute; top: -8px; right: -8px; background: #374151; color: #fff;
  border: none; border-radius: 50%; width: 22px; height: 22px; font-size: 0.7rem; cursor: pointer;
}

.pill-input {
  display: flex; align-items: center; background: var(--input-bg); border-radius: 32px;
  padding: 6px 6px 6px 16px; gap: 8px; border: 1px solid #374151; box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.action-icon {
  background: none; border: none; color: var(--text-muted); font-size: 1.3rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 50%;
}
.action-icon:hover { background: #374151; color: #f3f4f6; }
.action-icon.recording { color: #f43f5e; animation: pulse 1s infinite alternate; }
.text-input { flex: 1; border: none; background: transparent; outline: none; font-size: 1rem; color: #f3f4f6; padding: 8px 0; }
.send-icon { color: #8b5cf6; display: none; }

@keyframes pulse { 0% { transform: scale(1); opacity: 0.9; } 100% { transform: scale(1.05); opacity: 1; } }
</style>
</head>
<body>

<!-- KomiX Custom Gradient & Logo Icon -->
<svg style="width:0;height:0;position:absolute;" aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="komixGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6" />
      <stop offset="50%" stop-color="#ec4899" />
      <stop offset="100%" stop-color="#f43f5e" />
    </linearGradient>
  </defs>
</svg>

<div class="mobile-shell">
  
  <!-- Onboarding Screen -->
  <div id="onboarding-screen">
    <svg class="onboard-logo" viewBox="0 0 100 100" fill="none">
      <rect x="10" y="10" width="80" height="80" rx="20" fill="url(#komixGrad)"/>
      <path d="M35 30L65 50L35 70V30Z" fill="#ffffff"/>
      <circle cx="70" cy="30" r="8" fill="#38bdf8"/>
    </svg>
    <h1>Welcome to KomiX</h1>
    <p>Your AI Anime & Manga Studio.</p>
    <input type="text" id="user-name-input" class="name-input" placeholder="What should I call you?" onkeypress="if(event.key==='Enter')saveName()">
    <button class="get-started-btn" onclick="saveName()">Get Started</button>
    <div class="credits-text">Engineered by Avdhesh</div>
  </div>

  <!-- Header -->
  <header>
    <button class="menu-btn">☰</button>
    <div class="model-selector">
      <svg width="24" height="24" viewBox="0 0 100 100" fill="none">
        <rect x="10" y="10" width="80" height="80" rx="20" fill="url(#komixGrad)"/>
        <path d="M38 32L68 50L38 68V32Z" fill="#ffffff"/>
      </svg>
      KomiX
    </div>
    <div class="lang-selector">
      <button class="lang-chip active" id="b-en" onclick="setLang('en')">EN</button>
      <button class="lang-chip" id="b-hi" onclick="setLang('hi')">HI</button>
      <button class="lang-chip" id="b-gu" onclick="setLang('gu')">GU</button>
    </div>
  </header>

  <!-- Workspace Tabs Switcher -->
  <div class="workspace-tabs">
    <button class="tab-btn active" id="tab-chat" onclick="switchView('chat')">💬 AI Studio</button>
    <button class="tab-btn" id="tab-canvas" onclick="switchView('studio')">🎨 Panel Canvas</button>
  </div>

  <!-- Main Workspace -->
  <main id="main-scroll">
    
    <!-- Home View (Greeting & Suggestions) -->
    <div id="home-view">
      <svg class="big-logo" viewBox="0 0 100 100" fill="none">
        <rect x="10" y="10" width="80" height="80" rx="20" fill="url(#komixGrad)"/>
        <path d="M38 32L68 50L38 68V32Z" fill="#ffffff"/>
      </svg>
      <h1 class="greeting-text" id="dynamic-greeting">What shall we create today,<br><span>Creator</span>?</h1>
      
      <div class="suggestions-list" id="suggestions-container">
        <!-- Rendered via JS -->
      </div>
    </div>

    <!-- Chat View -->
    <div id="chat-view"></div>

    <!-- Studio View (Manga Canvas Creator with Export) -->
    <div id="studio-view">
      <div style="font-size: 1.1rem; font-weight: 600; color: #f3f4f6; margin-bottom: 2px;">🎨 KomiX Panel Canvas</div>
      <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 8px;">Type captions and export your manga layout page!</p>
      
      <div class="manga-grid" id="manga-page-grid">
        <div class="manga-panel">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
          <span>Panel 01</span>
          <input type="text" placeholder="Enter dialogue / caption..." value="The journey begins...">
        </div>
        <div class="manga-panel">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
          <span>Panel 02</span>
          <input type="text" placeholder="Enter dialogue / caption..." value="A sudden clash!">
        </div>
        <div class="manga-panel">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
          <span>Panel 03</span>
          <input type="text" placeholder="Enter dialogue / caption..." value="Unleashing the power!">
        </div>
        <div class="manga-panel">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
          <span>Panel 04</span>
          <input type="text" placeholder="Enter dialogue / caption..." value="To be continued...">
        </div>
      </div>

      <div class="panel-actions">
        <button class="studio-btn" onclick="exportMangaCanvas()">📥 Export Page (.png)</button>
        <button class="studio-btn primary" onclick="alert('Batch panel generation initialized!')">✨ AI Fill Panels</button>
      </div>
    </div>
  </main>

  <!-- Floating Input Bottom Bar -->
  <div class="input-container">
    <div class="audio-indicator" id="tts-audio-indicator">
      <span>🔊 <i>KomiX is speaking...</i></span>
      <button onclick="stopTTS()">Stop</button>
    </div>

    <div class="image-preview-box" id="img-preview-box">
      <img id="img-preview" src="">
      <button onclick="clearImage()">✕</button>
    </div>

    <div class="pill-input">
      <button class="action-icon" onclick="document.getElementById('image-upload').click()">+</button>
      <input type="file" id="image-upload" accept="image/*" style="display: none;" onchange="handleImage(event)">
      
      <input type="text" id="user-input" class="text-input" placeholder="Ask KomiX..." oninput="toggleSendIcon()" onkeypress="if(event.key==='Enter')sendPrompt()">
      
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
const komixLogoSvg = `<svg class="ai-avatar" viewBox="0 0 100 100" fill="none">
  <rect x="10" y="10" width="80" height="80" rx="20" fill="url(#komixGrad)"/>
  <path d="M38 32L68 50L38 68V32Z" fill="#ffffff"/>
</svg>`;

const I18N = {
  en: {
    locale: 'en',
    greeting: "What shall we create today,<br><span>{name}</span>?",
    placeholder: "Ask KomiX...",
    suggs: [
      { text: "Generate a 4-panel manga script", prompt: "Create a 4-panel manga script for: " },
      { text: "Write an anime character concept", prompt: "Design an epic anime character with backstory: " },
      { text: "Optimize an art prompt for generation", prompt: "Turn this idea into a detailed anime art prompt: " }
    ]
  },
  hi: {
    locale: 'hi',
    greeting: "आज हम क्या बनाएँगे,<br><span>{name}</span>?",
    placeholder: "KomiX से पूछें...",
    suggs: [
      { text: "4-पैनल मंगा स्क्रिप्ट बनाएं", prompt: "इसके लिए 4-पैनल मंगा स्क्रिप्ट बनाएं: " },
      { text: "एक बेहतरीन एनिमे कैरेक्टर डिज़ाइन करें", prompt: "बैकस्टोरी के साथ एक एपिक एनिमे कैरेक्टर डिज़ाइन करें: " },
      { text: "आर्ट प्रॉम्प्ट को ऑप्टिमाइज़ करें", prompt: "इस विचार को एक विस्तृत एनिमे आर्ट प्रॉम्प्ट में बदलें: " }
    ]
  },
  gu: {
    locale: 'gu',
    greeting: "આજે આપણે શું બનાવીશું,<br><span>{name}</span>?",
    placeholder: "KomiX ને પૂછો...",
    suggs: [
      { text: "4-પેનલ મંગા સ્ક્રિપ્ટ બનાવો", prompt: "આના માટે 4-પેનલ મંગા સ્ક્રિપ્ટ બનાવો: " },
      { text: "એક શાનદાર એનિમે કેરેક્ટર ડિઝાઇન કરો", prompt: "બેકસ્ટोरी સાથે એક એપિક એનિમે કેરેક્ટર ડિઝાઇન કરો: " },
      { text: "આર્ટ પ્રોમ્પ્ટ ઑપ્ટિમાઇઝ કરો", prompt: "આ વિચારને વિગતવાર એનિમે આર્ટ પ્રોમ્પ્ટમાં રૂપાંતરિત કરો: " }
    ]
  }
};

let curLang = 'en', isListening = false, activeAudio = null, currentImageBase64 = null, userName = "Creator";
const inputField = document.getElementById('user-input');
const chatStream = document.getElementById('chat-view');
const homeView = document.getElementById('home-view');
const studioView = document.getElementById('studio-view');
const micBtn = document.getElementById('mic-btn');
const sendBtn = document.getElementById('send-btn');
const ttsIndicator = document.getElementById('tts-audio-indicator');
const mainScroll = document.getElementById('main-scroll');

// --- View Switcher Logic ---
function switchView(viewName) {
  homeView.style.display = 'none';
  chatStream.style.display = 'none';
  studioView.style.display = 'none';

  document.getElementById('tab-chat').classList.remove('active');
  document.getElementById('tab-canvas').classList.remove('active');

  if (viewName === 'chat') {
    if (chatStream.children.length > 0) {
      chatStream.style.display = 'flex';
    } else {
      homeView.style.display = 'flex';
    }
    document.getElementById('tab-chat').classList.add('active');
  } else if (viewName === 'studio') {
    studioView.style.display = 'flex';
    document.getElementById('tab-canvas').classList.add('active');
  }
}

// --- Canvas Image Export Logic ---
function exportMangaCanvas() {
  const canvas = document.createElement('canvas');
  canvas.width = 1200;
  canvas.height = 1200;
  const ctx = canvas.getContext('2d');

  // Background Manga Page Style
  ctx.fillStyle = '#0c0f17';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Title Banner
  ctx.fillStyle = '#f3f4f6';
  ctx.font = 'bold 48px sans-serif';
  ctx.fillText('KomiX Manga Page Studio', 60, 90);

  ctx.fillStyle = '#8b5cf6';
  ctx.font = '24px sans-serif';
  ctx.fillText('Engineered by Avdhesh', 60, 130);

  // Read Panels & Captions
  const panels = document.querySelectorAll('.manga-panel');
  const coords = [
    {x: 60, y: 180}, {x: 630, y: 180},
    {x: 60, y: 680}, {x: 630, y: 680}
  ];

  panels.forEach((panel, index) => {
    const pos = coords[index];
    const caption = panel.querySelector('input').value || `Panel 0${index+1}`;

    // Panel Card Box
    ctx.fillStyle = '#111827';
    ctx.strokeStyle = '#374151';
    ctx.lineWidth = 4;
    ctx.fillRect(pos.x, pos.y, 510, 430);
    ctx.strokeRect(pos.x, pos.y, 510, 430);

    // Panel Number Badge
    ctx.fillStyle = '#8b5cf6';
    ctx.font = 'bold 22px sans-serif';
    ctx.fillText(`0${index+1}`, pos.x + 30, pos.y + 50);

    // Caption Box inside Panel
    ctx.fillStyle = 'rgba(0,0,0,0.7)';
    ctx.fillRect(pos.x + 20, pos.y + 350, 470, 55);
    
    ctx.fillStyle = '#ffffff';
    ctx.font = '20px sans-serif';
    ctx.fillText(caption, pos.x + 40, pos.y + 385);
  });

  // Trigger Download
  const link = document.createElement('a');
  link.download = 'komix-manga-page.png';
  link.href = canvas.toDataURL('image/png');
  link.click();
}

// --- Onboarding Logic ---
function initApp() {
  const savedName = localStorage.getItem('komixUserName');
  if (savedName) {
    userName = savedName;
    document.getElementById('onboarding-screen').style.display = 'none';
    setLang('en');
  } else {
    document.getElementById('user-name-input').value = "";
  }
}

function saveName() {
  const inputName = document.getElementById('user-name-input').value.trim();
  if (inputName) {
    userName = inputName;
    localStorage.setItem('komixUserName', userName);
    document.getElementById('onboarding-screen').style.opacity = '0';
    setTimeout(() => {
      document.getElementById('onboarding-screen').style.display = 'none';
      setLang(curLang);
    }, 400);
  }
}

// --- Image & Input Logic ---
function toggleSendIcon() {
  if (inputField.value.trim().length > 0 || currentImageBase64) {
    micBtn.style.display = 'none';
    sendBtn.style.display = 'flex';
  } else {
    micBtn.style.display = 'flex';
    sendBtn.style.display = 'none';
  }
}

function handleImage(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(e) {
    currentImageBase64 = e.target.result;
    document.getElementById('img-preview').src = currentImageBase64;
    document.getElementById('img-preview-box').style.display = 'block';
    toggleSendIcon();
  };
  reader.readAsDataURL(file);
}

function clearImage() {
  currentImageBase64 = null;
  document.getElementById('img-preview-box').style.display = 'none';
  document.getElementById('img-preview').src = '';
  document.getElementById('image-upload').value = '';
  toggleSendIcon();
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
    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>`,
    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`,
    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>`
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
  const imageAttached = currentImageBase64; 
  if (!q && !imageAttached) return;

  stopTTS();
  inputField.value = '';
  toggleSendIcon();
  
  homeView.style.display = 'none';
  chatStream.style.display = 'flex';
  switchView('chat');
  
  let userBubbleHtml = `<div class="chat-bubble user-bubble">${q}`;
  if (imageAttached) userBubbleHtml += `<br><img src="${imageAttached}">`;
  userBubbleHtml += `</div>`;

  chatStream.innerHTML += `<div class="chat-row user-row">${userBubbleHtml}</div>`;

  const thinkingId = 'think-' + Date.now();
  chatStream.innerHTML += `
    <div class="chat-row ai-row" id="${thinkingId}">
      <div class="ai-bubble">
        ${komixLogoSvg}
        <div class="chat-bubble" style="color:#c084fc; font-style:italic;">Drafting panels...</div>
      </div>
    </div>`;
  mainScroll.scrollTop = mainScroll.scrollHeight;

  const payload = { 
    prompt: q || "Please analyze this art/reference.", 
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
    document.getElementById(thinkingId).remove();

    chatStream.innerHTML += `
      <div class="chat-row ai-row">
        <div class="ai-bubble">
          ${komixLogoSvg}
          <div class="chat-bubble">${data.reply.replace(/\n/g, '<br>')}</div>
        </div>
      </div>`;
    mainScroll.scrollTop = mainScroll.scrollHeight;
    playNaturalVoice(data.reply, I18N[curLang].locale);
  } catch (err) {
    document.getElementById(thinkingId).innerHTML = `<div class="ai-bubble"><div class="chat-bubble" style="color:#f43f5e;">Error connecting to server.</div></div>`;
  }
}

window.addEventListener('DOMContentLoaded', initApp);
</script>
</body>
</html>
"""

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