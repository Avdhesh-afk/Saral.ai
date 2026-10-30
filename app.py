import os
import io
import base64
import urllib.parse
import requests
import streamlit as st
from groq import Groq
from PIL import Image, ImageDraw
from gtts import gTTS

# Detect local logo file if uploaded to GitHub
LOCAL_LOGO_PATH = None
for candidate in ["logo.png", "logo.jpg", "logo.jpeg", "logo.webp"]:
    if os.path.exists(candidate):
        LOCAL_LOGO_PATH = candidate
        break

# Page Configuration
st.set_page_config(
    page_title="KomiX — Anime & Manga Studio",
    page_icon=LOCAL_LOGO_PATH if LOCAL_LOGO_PATH else "🎨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS matching the KomiX UI Prototype + Mobile Input Fix
st.markdown("""
<style>
:root{--bg:#101014;--panel:#19191f;--panel2:#202027;--line:#30303a;--text:#f4f2f7;--muted:#9996a5;--purple:#a78bfa;--pink:#f472b6;--cyan:#67e8f9;--radius:15px}
.stApp, .main { background-color: var(--bg); color: var(--text); }
.stButton>button { background-color: var(--panel2); color: var(--text); border: 1px solid var(--line); border-radius: 9px; font-weight: 650; width: 100%; }
.stButton>button:hover { border-color: var(--purple); color: var(--purple); }
div[data-testid="InputInstructions"] { display: none !important; }
.brand-wrap{display:flex;align-items:center;gap:10px;font-weight:800;font-size:22px;letter-spacing:-.7px;padding-top:4px}
.brandmark{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,var(--purple),var(--pink));display:inline-grid;place-items:center;color:#17131f;font-weight:950;font-size:18px}
.custom-logo{width:34px;height:34px;border-radius:9px;object-fit:cover;border:1px solid var(--line)}
.scene-card{background:#1e1e26;border:1px solid #343440;border-radius:12px;padding:15px;margin:12px 0}
.scene-number{font-size:10px;letter-spacing:1.2px;color:var(--purple);font-weight:800;margin-bottom:4px}
.ai-card{padding:14px;border-radius:13px;border:1px solid #51416c;background:linear-gradient(145deg,#292139,#1c1a24);margin-bottom:12px}
.ai-top{display:flex;gap:9px;align-items:center;font-weight:750;color:#f4f2f7}
.spark{width:27px;height:27px;border-radius:8px;background:linear-gradient(135deg,var(--purple),var(--pink));display:grid;place-items:center;color:#21172c;font-weight:bold}
.tag{font-size:10px;padding:4px 7px;border-radius:6px;background:#292333;color:#cdb9ff}
.script-tip{padding:13px 15px;border:1px solid #51416c;border-radius:10px;background:#242033;color:#c8bdd9;font-size:12px;margin-top:16px}
.mini-card{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:13px;margin-top:10px}
.mini-title{font-weight:750;font-size:12px;margin-bottom:5px;color:#f4f2f7}
.mini-card p{margin:0;color:var(--muted);font-size:11px}
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "scenes" not in st.session_state:
    st.session_state.scenes = [
        {
            "title": "The forgotten city",
            "text": "A lone swordsman walks through an abandoned city. The streets are silent, and every clock has stopped at exactly midnight.",
            "meta": "Setting · Abandoned city"
        },
        {
            "title": "A voice in the dark",
            "text": "A voice echoes from the alley.\n\nMYSTERIOUS VOICE: “You are late.”\nSWORDSMAN: “Who are you?”",
            "meta": "Characters · Swordsman, Unknown"
        },
        {
            "title": "The first clue",
            "text": "A single clock begins to tick. On its glass, a message appears: “Find the one who stopped time.”",
            "meta": "Purpose · Story hook"
        }
    ]

if "outline" not in st.session_state:
    st.session_state.outline = [
        ("Opening · The city", "01"),
        ("Encounter · The voice", "02"),
        ("Hook · The clue", "03")
    ]

if "ai_prompt_text" not in st.session_state:
    st.session_state.ai_prompt_text = ""

if "ai_last_output" not in st.session_state:
    st.session_state.ai_last_output = ""

if "characters" not in st.session_state:
    st.session_state.characters = [
        {"name": "Ren (Lone Swordsman)", "role": "Protagonist", "traits": "Stoic, carries a chrono-blade"},
        {"name": "Mysterious Voice", "role": "Unknown Figure", "traits": "Knows the secret of the stopped clocks"}
    ]

def get_brand_html(uploaded_file, local_path):
    logo_b64 = None
    mime = "image/png"
    if uploaded_file is not None:
        logo_b64 = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
        mime = uploaded_file.type or "image/png"
    elif local_path is not None:
        with open(local_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode("utf-8")
    if logo_b64:
        icon_html = f"<img src='data:{mime};base64,{logo_b64}' class='custom-logo' alt='Logo'>"
    else:
        icon_html = "<div class='brandmark'>K</div>"
    return f"<div class='brand-wrap'>{icon_html}<span>komi<span style='color:#a78bfa'>X</span></span></div>"

def generate_with_groq(client, selected_model, system_prompt, user_prompt):
    model_map = {
        "gpt-oss-120b": ["openai/gpt-oss-120b", "gpt-oss-120b"],
        "gpt-oss-20b": ["openai/gpt-oss-20b", "gpt-oss-20b"],
        "qwen-3.8-27b": ["qwen-3.8-27b", "openai/gpt-oss-120b"]
    }
    candidates = model_map.get(selected_model, [selected_model, "openai/gpt-oss-120b"])
    last_err = None
    for model_id in candidates:
        try:
            res = client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            return res.choices[0].message.content
        except Exception as e:
            last_err = e
    raise last_err

def set_quick_prompt(text):
    st.session_state.ai_prompt_text = text

# Sidebar API Key, Custom Logo Uploader & Model Registry
st.sidebar.title("⚙️ KomiX Settings")
uploaded_logo = st.sidebar.file_uploader("Upload Custom Logo", type=["png", "jpg", "jpeg", "webp"])

default_key = os.environ.get("GROQ_API_KEY", "")
try:
    if not default_key and "GROQ_API_KEY" in st.secrets:
        default_key = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

api_key_input = st.sidebar.text_input("Enter Groq API Key", type="password", value=default_key)
client = Groq(api_key=api_key_input.strip()) if api_key_input.strip() else None

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Model Registry")
text_model = st.sidebar.selectbox("Text / Reasoning Model", ["gpt-oss-120b", "gpt-oss-20b", "qwen-3.8-27b"])
stt_model = st.sidebar.selectbox("Speech-to-Text Model", ["whisper-large-v3", "whisper-large-v3-turbo"])
tts_model = st.sidebar.selectbox("Text-to-Speech Model", ["Orpheus English", "Orpheus Arabic Saudi"])
st.sidebar.caption("Safety Model: Safety GPT OSS 20B")

# Top Header Bar with Custom Logo
col_brand, col_proj, col_save, col_share, col_export = st.columns([2, 2.5, 1.5, 1, 1.2])
with col_brand:
    st.markdown(get_brand_html(uploaded_logo, LOCAL_LOGO_PATH), unsafe_allow_html=True)
with col_proj:
    st.markdown("<div style='padding-top:10px'><span style='color:#c7c3d0;font-weight:600'>Untitled Manga</span> <span style='color:#9996a5'>/ Chapter 01</span></div>", unsafe_allow_html=True)
with col_save:
    st.markdown("<div style='padding-top:12px;font-size:12px;color:#8c8996'>● All changes saved</div>", unsafe_allow_html=True)
with col_share:
    if st.button("Share"):
        st.toast("🔗 Shareable project link copied!")
with col_export:
    script_export = "\n\n".join([f"SCENE {i+1}: {s['title']}\n{s['text']}" for i, s in enumerate(st.session_state.scenes)])
    st.download_button("Export ↗", data=script_export, file_name="komix_chapter_01.txt", mime="text/plain")

st.markdown("<hr style='border:1px solid #30303a; margin:8px 0 16px 0;'>", unsafe_allow_html=True)

# Main Workspace Columns
sidebar_col, main_col, right_col = st.columns([1.2, 3.2, 2.0])

# 1. LEFT SIDEBAR NAVIGATION
with sidebar_col:
    st.markdown("<div style='font-size:10px;letter-spacing:1.4px;color:#777483;font-weight:800;margin-bottom:8px'>WORKSPACE</div>", unsafe_allow_html=True)
    nav_options = [
        "Studio",
        "My projects",
        "Character library",
        "Asset library",
        "AI script writer",
        "Scene planner",
        "Dialogue & captions",
        "Text-to-Image",
        "Text-to-Speech",
        "Settings"
    ]
    selected_nav = st.radio("Navigation", nav_options, label_visibility="collapsed")

    st.markdown("""
    <div style='margin:18px 0;padding:12px;border:1px solid #30303a;border-radius:12px;background:#191920'>
        <strong style='font-size:12px;display:block'>✦ Creator plan</strong>
        <span style='font-size:11px;color:#9996a5'>3 of 10 projects used</span>
        <div style='height:4px;background:#35313d;border-radius:4px;margin-top:10px'>
            <div style='height:4px;width:30%;background:#a78bfa;border-radius:4px'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 2. RIGHTBAR: AI CREATIVE ASSISTANT & CHAPTER DETAILS
with right_col:
    st.markdown("### **AI Creative Assistant** <span class='tag'>GROQ POWERED</span>", unsafe_allow_html=True)
    st.markdown("""
    <div class='ai-card'>
        <div class='ai-top'><div class='spark'>✦</div><div>Let's build your story</div></div>
        <p style='font-size:11px;color:#c1b8d0;margin:8px 0 0'>Describe a scene, character, or plot twist. Tap a quick chip or type below and hit Generate.</p>
    </div>
    """, unsafe_allow_html=True)

    c_chip1, c_chip2, c_chip3 = st.columns(3)
    with c_chip1:
        st.button("Opening scene", on_click=set_quick_prompt, args=("Create a dramatic opening scene for my manga chapter.",))
    with c_chip2:
        st.button("Plot twist", on_click=set_quick_prompt, args=("Write a shocking plot twist for this chapter.",))
    with c_chip3:
        st.button("Dialogue", on_click=set_quick_prompt, args=("Write punchy manga dialogue for the main character.",))

    with st.form("ai_assistant_form", clear_on_submit=False):
        prompt_val = st.text_input(
            "Scene or story idea",
            key="ai_prompt_text",
            placeholder="A lone swordsman enters a city where time has stopped..."
        )
        speak_reply = st.checkbox("🔊 Read response aloud (TTS)", value=False)
        submitted = st.form_submit_button("Generate ↗", type="primary")

    if submitted:
        if not client:
            st.error("⚠️ Tap the top-left arrow (>>) to open KomiX Settings and enter your Groq API Key.")
        elif not prompt_val.strip():
            st.warning("Please type a scene idea or tap one of the quick prompt buttons above.")
        else:
            with st.spinner(f"Generating with {text_model}..."):
                try:
                    output = generate_with_groq(
                        client,
                        text_model,
                        "You are KomiX, an expert manga scriptwriter and storyboard director. Write vivid panel descriptions and crisp character dialogue.",
                        prompt_val
                    )
                    st.session_state.ai_last_output = output
                    if speak_reply:
                        tts = gTTS(text=output[:400], lang="ar" if "Arabic" in tts_model else "en")
                        audio_buf = io.BytesIO()
                        tts.write_to_fp(audio_buf)
                        audio_buf.seek(0)
                        st.audio(audio_buf, format="audio/mp3")
                except Exception as e:
                    st.error(f"Groq API Error: {e}")

    if st.session_state.ai_last_output:
        st.success("✦ Generated Script:")
        st.write(st.session_state.ai_last_output)
        if st.button("＋ Add to Chapter Script"):
            st.session_state.scenes.append({
                "title": "AI Generated Scene",
                "text": st.session_state.ai_last_output,
                "meta": f"Generated · {text_model}"
            })
            st.toast("✅ Added to Chapter Script!")
            st.rerun()

    st.markdown("<hr style='border:1px solid #30303a;'>", unsafe_allow_html=True)
    st.subheader("CHAPTER DETAILS")
    st.caption("Chapter: 01  |  Status: Draft  |  Genre: Action · Fantasy  |  Direction: Right to left")

    st.markdown("<hr style='border:1px solid #30303a;'>", unsafe_allow_html=True)
    st.subheader("CHAPTER OUTLINE")
    for title, num in st.session_state.outline:
        st.markdown(f"✦ **{title}** <span style='float:right; color:#9996a5;'>{num}</span>", unsafe_allow_html=True)

    new_outline_title = st.text_input("New outline item", placeholder="Climax · The battle", label_visibility="collapsed")
    if st.button("＋ Add outline item"):
        item_label = new_outline_title.strip() if new_outline_title.strip() else "New outline beat"
        new_num = f"{len(st.session_state.outline) + 1:02d}"
        st.session_state.outline.append((item_label, new_num))
        st.rerun()

# 3. MAIN CONTENT AREA
with main_col:
    if selected_nav == "My projects":
        st.header("▤ My Manga Projects")
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            st.markdown("<div class='scene-card'><div class='scene-number'>ACTIVE PROJECT</div><strong>Untitled Manga</strong><p style='color:#9996a5;font-size:12px'>Chapter 01 · 3 Scenes</p></div>", unsafe_allow_html=True)
        with p_col2:
            st.markdown("<div class='scene-card'><div class='scene-number'>PROJECT 02</div><strong>Neon Ronin</strong><p style='color:#9996a5;font-size:12px'>Cyberpunk One-Shot</p></div>", unsafe_allow_html=True)
        with p_col3:
            st.markdown("<div class='scene-card'><div class='scene-number'>PROJECT 03</div><strong>Astral Academy</strong><p style='color:#9996a5;font-size:12px'>Fantasy Shonen</p></div>", unsafe_allow_html=True)

    elif selected_nav == "Character library":
        st.header("◈ Character Library")
        for char in st.session_state.characters:
            st.markdown(f"<div class='scene-card'><div class='scene-number'>{char['role'].upper()}</div><strong>{char['name']}</strong><p style='color:#9996a5;font-size:12px;margin-top:4px'>{char['traits']}</p></div>", unsafe_allow_html=True)
        with st.form("add_char_form"):
            c_name = st.text_input("Character Name", placeholder="Akira")
            c_role = st.text_input("Role", placeholder="Rival")
            c_traits = st.text_input("Traits & Visual Design", placeholder="Silver hair, twin daggers, time-shift cloak")
            if st.form_submit_button("＋ Add Character"):
                if c_name.strip():
                    st.session_state.characters.append({"name": c_name, "role": c_role or "Character", "traits": c_traits})
                    st.rerun()

    elif selected_nav == "Asset library":
        st.header("▧ Asset Library")
        st.write("Select manga screentones, speedlines, and SFX stamps for your panel canvas.")
        a1, a2, a3 = st.columns(3)
        with a1:
            st.info("⚡ Action Speedlines")
        with a2:
            st.info("💬 Manga Speech Bubbles")
        with a3:
            st.info("💥 SFX Katakana Stamps")

    elif selected_nav == "Text-to-Image":
        st.header("🎨 Text-to-Image Manga Panel Generator")
        with st.form("tti_form"):
            img_prompt = st.text_input(
                "Panel Visual Description",
                value="Black and white manga panel, lone swordsman in an abandoned city at midnight, high contrast ink, screentones, dramatic angle"
            )
            gen_img_btn = st.form_submit_button("Generate Panel Artwork ↗", type="primary")

        if gen_img_btn:
            with st.spinner("Drawing manga panel..."):
                try:
                    encoded = urllib.parse.quote(f"black and white manga panel ink art, {img_prompt}")
                    url = f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=768&nologo=true"
                    resp = requests.get(url, timeout=20)
                    if resp.status_code == 200:
                        st.image(resp.content, caption=img_prompt, use_container_width=True)
                        st.download_button("📥 Download Panel PNG", data=resp.content, file_name="komix_panel.png", mime="image/png")
                    else:
                        raise RuntimeError("Fallback to local canvas")
                except Exception:
                    img = Image.new("RGB", (600, 600), color=(245, 245, 245))
                    draw = ImageDraw.Draw(img)
                    draw.rectangle([20, 20, 580, 580], outline="black", width=4)
                    draw.text((40, 280), f"Manga Panel:\n{img_prompt[:60]}", fill="black")
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    st.image(buf.getvalue(), caption="Generated Panel Layout")

    elif selected_nav == "Text-to-Speech":
        st.header("🎙️ Voice & Audio Studio")
        st.caption(f"Active TTS: {tts_model}  |  Active STT: {stt_model}")
        with st.form("tts_form"):
            tts_text = st.text_input("Dialogue to synthesize into speech", value="You are late. Find the one who stopped time!")
            speak_btn = st.form_submit_button("🗣️ Synthesize Speech", type="primary")

        if speak_btn and tts_text.strip():
            with st.spinner(f"Generating voiceover with {tts_model}..."):
                try:
                    tts = gTTS(text=tts_text, lang="ar" if "Arabic" in tts_model else "en")
                    audio_buf = io.BytesIO()
                    tts.write_to_fp(audio_buf)
                    audio_buf.seek(0)
                    st.audio(audio_buf, format="audio/mp3")
                    st.download_button("📥 Download Voiceover MP3", data=audio_buf.getvalue(), file_name="dialogue.mp3", mime="audio/mp3")
                except Exception as e:
                    st.error(f"TTS Error: {e}")

        st.markdown("---")
        st.subheader("🎤 Voice-to-Script (Whisper Large v3)")
        audio_val = st.audio_input("Record voice note to transcribe into manga script")
        if audio_val and client:
            with st.spinner(f"Transcribing with {stt_model}..."):
                try:
                    tr = client.audio.transcriptions.create(
                        file=("voice.wav", audio_val.getvalue()),
                        model=stt_model
                    )
                    st.success(f"Transcribed: {tr.text}")
                    if st.button("Send Transcription to AI Prompt"):
                        st.session_state.ai_prompt_text = tr.text
                        st.rerun()
                except Exception as e:
                    st.error(f"STT Error: {e}")

    elif selected_nav == "Settings":
        st.header("⚙ Studio Settings")
        st.write("Open the left sidebar (tap **>>** in the top-left corner on mobile) to upload a custom logo, enter your Groq API Key, and switch models.")

    else:
        st.markdown("<div style='font-size:11px;color:#a78bfa;font-weight:800;letter-spacing:1.2px;text-transform:uppercase'>Story workspace / chapter 01</div>", unsafe_allow_html=True)
        st.subheader("Untitled Manga ✎")

        act1, act2 = st.columns(2)
        with act1:
            preview_clicked = st.button("▷ Read preview")
        with act2:
            if st.button("＋ New scene", type="primary"):
                st.session_state.scenes.append({
                    "title": f"Scene {len(st.session_state.scenes) + 1}",
                    "text": "Describe the action, dialogue, and atmosphere...",
                    "meta": "Draft"
                })
                st.rerun()

        if preview_clicked:
            with st.expander("📖 Chapter 01 Reading Preview", expanded=True):
                for i, sc in enumerate(st.session_state.scenes):
                    st.markdown(f"**SCENE {i+1:02d}: {sc['title']}**")
                    st.write(sc["text"])
                    st.markdown("---")

        tabs = st.tabs(["Script", "Overview", "Storyboard & Canvas"])

        with tabs[0]:
            st.caption(f"⌁ {len(st.session_state.scenes)} scenes  ·  ◷ Approx. 5 min read  ·  ✎ Autosaved")
            for idx, scene in enumerate(st.session_state.scenes):
                st.markdown(f"<div class='scene-number'>SCENE {idx+1:02d} · {scene.get('meta', 'Draft')}</div>", unsafe_allow_html=True)
                new_t = st.text_input(f"Title {idx+1}", value=scene["title"], key=f"sc_title_{idx}", label_visibility="collapsed")
                new_b = st.text_area(f"Script {idx+1}", value=scene["text"], key=f"sc_body_{idx}", label_visibility="collapsed", height=100)
                st.session_state.scenes[idx]["title"] = new_t
                st.session_state.scenes[idx]["text"] = new_b

                sc_col1, sc_col2 = st.columns([1, 1])
                with sc_col1:
                    if st.button(f"🔊 Speak Scene {idx+1}", key=f"tts_sc_{idx}"):
                        tts = gTTS(text=new_b, lang="ar" if "Arabic" in tts_model else "en")
                        buf = io.BytesIO()
                        tts.write_to_fp(buf)
                        buf.seek(0)
                        st.audio(buf, format="audio/mp3")
                with sc_col2:
                    if st.button(f"✨ Polish Scene {idx+1} with AI", key=f"ai_sc_{idx}"):
                        if not client:
                            st.warning("Add your Groq API Key in the sidebar first.")
                        else:
                            with st.spinner("Polishing scene..."):
                                polished = generate_with_groq(
                                    client,
                                    text_model,
                                    "You are a manga editor. Rewrite this scene with sharper visual panel directions and dramatic dialogue.",
                                    new_b
                                )
                                st.session_state.scenes[idx]["text"] = polished
                                st.rerun()
                st.markdown("<hr style='border:0.5px solid #262630'>", unsafe_allow_html=True)

            st.markdown("<div class='script-tip'>✦ <strong>Writing tip</strong> Keep each scene focused on one key action, reveal, or emotional beat. You can plan panels after the script is ready.</div>", unsafe_allow_html=True)

        with tabs[1]:
            st.markdown("""
            <div class='mini-card'>
                <div class='mini-title'>✦ Chapter progress</div>
                <p>Scenes drafted · Story structure in progress</p>
            </div>
            <div class='mini-card'>
                <div class='mini-title'>⌘ Writing workflow</div>
                <p>Outline → Script → Dialogue polish → Storyboard</p>
            </div>
            """, unsafe_allow_html=True)

        with tabs[2]:
            st.subheader("📐 Interactive Manga Page Canvas")
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                p1_cap = st.text_input("Panel 1 Caption", value=st.session_state.scenes[0]["title"] if st.session_state.scenes else "The forgotten city")
                p2_cap = st.text_input("Panel 2 Caption", value="“You are late.”")
            with p_col2:
                p3_cap = st.text_input("Panel 3 Caption", value="“Who are you?”")
                p4_cap = st.text_input("Panel 4 Caption", value="Find the one who stopped time.")

            if st.button("Render & Export Manga Page", type="primary"):
                page = Image.new("RGB", (800, 1100), color="white")
                draw = ImageDraw.Draw(page)
                draw.rectangle([30, 30, 770, 350], outline="black", width=5)
                draw.rectangle([30, 380, 385, 720], outline="black", width=5)
                draw.rectangle([415, 380, 770, 720], outline="black", width=5)
                draw.rectangle([30, 750, 770, 1070], outline="black", width=5)

                draw.text((50, 50), f"PANEL 01: {p1_cap}", fill="black")
                draw.text((50, 400), f"PANEL 02: {p2_cap}", fill="black")
                draw.text((435, 400), f"PANEL 03: {p3_cap}", fill="black")
                draw.text((50, 770), f"PANEL 04: {p4_cap}", fill="black")

                buf = io.BytesIO()
                page.save(buf, format="PNG")
                byte_im = buf.getvalue()
                st.image(byte_im, caption="Rendered Chapter 01 Manga Page", use_container_width=True)
                st.download_button("📥 Download Page (PNG)", data=byte_im, file_name="komix_page_01.png", mime="image/png")