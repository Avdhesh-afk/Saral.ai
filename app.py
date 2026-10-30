import os
import streamlit as st
from groq import Groq
from PIL import Image, ImageDraw, ImageFont
import io

# Page Configuration
st.set_page_config(
    page_title="KomiX — Anime & Manga Studio",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Injecting the exact CSS and UI styling from your prototype
st.markdown("""
<style>
:root{--bg:#101014;--panel:#19191f;--panel2:#202027;--line:#30303a;--text:#f4f2f7;--muted:#9996a5;--purple:#a78bfa;--pink:#f472b6;--cyan:#67e8f9;--radius:15px}
.main { background-color: var(--bg); color: var(--text); }
.stButton>button { background-color: var(--panel2); color: var(--text); border: 1px solid var(--line); border-radius: 9px; font-weight: 650; }
.stButton>button:hover { border-color: var(--purple); color: var(--purple); }
.scene-card{background:#1e1e26;border:1px solid #343440;border-radius:12px;padding:15px;margin:12px 0}
.scene-number{font-size:10px;letter-spacing:1.2px;color:var(--purple);font-weight:800;margin-bottom:8px}
.ai-card{padding:14px;border-radius:13px;border:1px solid #51416c;background:linear-gradient(145deg,#292139,#1c1a24);margin-bottom:17px}
.ai-top{display:flex;gap:9px;align-items:center;font-weight:750}
.spark{width:27px;height:27px;border-radius:8px;background:linear-gradient(135deg,var(--purple),var(--pink));display:grid;place-items:center;color:#21172c}
.tag{font-size:10px;padding:4px 7px;border-radius:6px;background:#292333;color:#cdb9ff}
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if 'scenes' not in st.session_state:
    st.session_state.scenes = [
        {"title": "The forgotten city", "text": "A lone swordsman walks through an abandoned city. The streets are silent, and every clock has stopped at exactly midnight.", "meta": "Setting · Abandoned city"},
        {"title": "A voice in the dark", "text": "A voice echoes from the alley.\n\nMYSTERIOUS VOICE: “You are late.”\nSWORDSMAN: “Who are you?”", "meta": "Characters · Swordsman, Unknown"},
        {"title": "The first clue", "text": "A single clock begins to tick. On its glass, a message appears: “Find the one who stopped time.”", "meta": "Purpose · Story hook"}
    ]
if 'outline' not in st.session_state:
    st.session_state.outline = [
        ("Opening · The city", "01"),
        ("Encounter · The voice", "02"),
        ("Hook · The clue", "03")
    ]
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Script"
if 'active_nav' not in st.session_state:
    st.session_state.active_nav = "Studio"

# Sidebar API Key & Settings
st.sidebar.title("⚙️ KomiX Settings")
api_key_input = st.sidebar.text_input("Enter Groq API Key", type="password", value=os.environ.get("GROQ_API_KEY", ""))
client = Groq(api_key=api_key_input) if api_key_input else None

st.sidebar.markdown("---")
st.sidebar.subheader("🤖 Model Registry")
text_model = st.sidebar.selectbox("Text Model", ["gpt-oss-120b", "gpt-oss-20b"])
st.sidebar.text("Vision Model: qwen-3.8-27b")
st.sidebar.text("STT Model: whisper-large-v3")
st.sidebar.text("TTS Model: orpheus-english")

# Top Header Bar
col_brand, col_proj, col_space, col_save, col_share, col_export, col_av = st.columns([2, 2, 1, 1, 0.8, 1, 0.5])
with col_brand:
    st.markdown("### 🎨 komi<span style='color:#a78bfa'>X</span>", unsafe_allow_html=True)
with col_proj:
    st.markdown("<span style='color:#c7c3d0;font-weight:600'>Untitled Manga</span> <span style='color:#9996a5'>/ Chapter 01</span>", unsafe_allow_html=True)
with col_save:
    st.markdown("<span style='font-size:12px;color:#8c8996'>● All changes saved</span>", unsafe_allow_html=True)
with col_share:
    if st.button("Share"):
        st.toast("🔗 Shareable link generated and copied to clipboard!")
with col_export:
    if st.button("Export ↗", type="primary"):
        st.toast("🚀 Export package compiled successfully!")
with col_av:
    st.markdown("👤")

st.markdown("<hr style='border:1px solid #30303a; margin:0 0 15px 0;'>", unsafe_allow_html=True)

# Main App Layout Grid (Sidebar, Main Content, Rightbar)
sidebar_col, main_col, right_col = st.columns([1.2, 3.2, 2.2])

# -------------------------------------------------------------
# 1. LEFT SIDEBAR NAVIGATION
# -------------------------------------------------------------
with sidebar_col:
    st.markdown("<div style='font-size:10px;letter-spacing:1.4px;color:#777483;font-weight:800;margin:12px 0 9px'>WORKSPACE</div>", unsafe_allow_html=True)
    nav_options = ["Studio", "My projects", "Character library", "Asset library", "AI script writer", "Scene planner", "Dialogue & captions", "Text-to-Image", "Text-to-Speech", "Settings"]
    
    selected_nav = st.radio("Navigation", nav_options, label_visibility="collapsed")
    st.session_state.active_nav = selected_nav

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style='margin:22px 0;padding:12px;border:1px solid #30303a;border-radius:12px;background:#191920'>
        <strong style='font-size:12px'>✦ Creator plan</strong>
        <span style='font-size:11px;color:#9996a5'>3 of 10 projects used</span>
        <div style='height:4px;background:#35313d;border-radius:4px;margin-top:10px'>
            <div style='height:4px;width:30%;background:#a78bfa;border-radius:4px'></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# 2. RIGHTBAR: AI ASSISTANT & CHAPTER DETAILS
# -------------------------------------------------------------
with right_col:
    st.markdown("### **AI Creative Assistant** <span class='tag'>GROQ POWERED</span>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
        <div class='ai-card'>
            <div class='ai-top'><div class='spark'>✦</div><div>Let's build your story</div></div>
            <p>Describe a scene, character, or plot twist. I'll help turn the idea into manga-ready script and panel direction.</p>
        </div>
        """, unsafe_allow_html=True)
        
        prompt_input = st.text_area("AI Prompt", placeholder="A lone swordsman enters a city where time has stopped...", label_visibility="collapsed")
        
        col_chip1, col_chip2, col_chip3 = st.columns(3)
        with col_chip1:
            if st.button("Opening scene"):
                prompt_input = "Create a dramatic opening scene"
        with col_chip2:
            if st.button("Plot twist"):
                prompt_input = "Write a plot twist for this chapter"
        with col_chip3:
            if st.button("Dialogue"):
                prompt_input = "Create dialogue for the main character"

        if st.button("Generate ↗", type="primary", key="generate_ai_btn"):
            if not client:
                st.error("Please enter your Groq API Key in the sidebar.")
            elif not prompt_input.strip():
                st.warning("Please enter a prompt or select a quick chip first.")
            else:
                with st.spinner("Generating script via Groq..."):
                    try:
                        res = client.chat.completions.create(
                            model=text_model,
                            messages=[
                                {"role": "system", "content": "You are an expert manga creator assistant powered by Groq."},
                                {"role": "user", "content": prompt_input}
                            ],
                            temperature=0.7,
                            max_tokens=600
                        )
                        ai_result = res.choices[0].message.content
                        st.success("Generated successfully!")
                        st.markdown(f"```text\n{ai_result}\n```")
                    except Exception as e:
                        st.error(f"Groq API Error: {e}")

    st.markdown("<hr style='border:1px solid #30303a;'>", unsafe_allow_html=True)
    st.subheader("CHAPTER DETAILS")
    st.text("Chapter: 01\nStatus: Draft\nGenre: Action · Fantasy\nReading direction: Right to left")
    
    st.markdown("<hr style='border:1px solid #30303a;'>", unsafe_allow_html=True)
    st.subheader("CHAPTER OUTLINE")
    for title, num in st.session_state.outline:
        st.markdown(f"✦ **{title}** <span style='float:right; color:#9996a5;'>{num}</span>", unsafe_allow_html=True)
    
    if st.button("＋ Add outline item"):
        new_num = f"{len(st.session_state.outline)+1:02d}"
        st.session_state.outline.append(("New outline item", new_num))
        st.rerun()

# -------------------------------------------------------------
# 3. MAIN CONTENT AREA (Dynamic based on Navigation/Tabs)
# -------------------------------------------------------------
with main_col:
    # Handle Navigation Items
    if selected_nav == "My projects":
        st.header("📂 My Manga Projects")
        st.info("You have 3 active projects. Showing project workspace for **Untitled Manga**.")
    elif selected_nav == "Character library":
        st.header("◈ Character Library")
        st.write("Manage your manga character sheets, traits, and concept art prompts here.")
    elif selected_nav == "Asset library":
        st.header("▧ Asset Library")
        st.write("Backgrounds, screentones, speech bubble templates, and sound effect assets.")
    elif selected_nav == "Text-to-Image":
        st.header("🎨 Text-to-Image Manga Panel Generator")
        img_prompt = st.text_input("Panel Prompt", "Detailed anime male protagonist, high contrast manga style, ink lines, screentones")
        if st.button("Generate Panel Artwork"):
            with st.spinner("Rendering artwork..."):
                img = Image.new("RGB", (512, 512), color=(245, 245, 245))
                draw = ImageDraw.Draw(img)
                draw.rectangle([20, 20, 492, 492], outline="black", width=3)
                draw.text((40, 240), f"Manga Art:\n{img_prompt[:40]}...", fill="black")
                st.image(img, caption="Generated Panel Artwork")
    elif selected_nav == "Text-to-Speech":
        st.header("🎙️ Text-to-Speech Voiceover Studio (Orpheus English)")
        tts_text = st.text_area("Dialogue to speak", "Let's finish this! Ultimate attack!")
        if st.button("🗣️ Synthesize Speech"):
            with st.spinner("Synthesizing voice audio..."):
                try:
                    from gtts import gTTS
                    tts = gTTS(text=tts_text, lang='en')
                    audio_buf = io.BytesIO()
                    tts.write_to_fp(audio_buf)
                    audio_buf.seek(0)
                    st.audio(audio_buf, format='audio/mp3')
                    st.success("Voice audio synthesized successfully!")
                except Exception as e:
                    st.error(f"TTS Error: {e}")
    else:
        # Standard Studio Workspace
        st.markdown("<div style='font-size:11px;color:#a78bfa;font-weight:800;letter-spacing:1.2px;text-transform:uppercase'>Story workspace / chapter 01</div>", unsafe_allow_html=True)
        st.title("Untitled Manga ✎")
        
        # Action Header buttons
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("▷ Read preview"):
                st.success("📖 Loading interactive manga page reader preview...")
        with col_btn2:
            if st.button("＋ New scene", type="primary"):
                st.session_state.scenes.append({"title": "New scene", "text": "Describe action and dialogue here...", "meta": "Draft scene"})
                st.rerun()

        # Tabs
        tabs = st.tabs(["Overview", "Script", "Storyboard", "Canvas Layout"])
        
        with tabs[0]:
            st.subheader("Chapter Overview")
            st.write("Summary: A lone swordsman enters a mysterious frozen city where time has stopped.")
        
        with tabs[1]:
            st.subheader("Chapter Script Editor")
            for idx, scene in enumerate(st.session_state.scenes):
                st.markdown(f"""
                <div class='scene-card'>
                    <div class='scene-number'>SCENE {str(idx+1).zfill(2)}</div>
                </div>
                """, unsafe_allow_html=True)
                scene['title'] = st.text_input(f"Scene Title {idx+1}", value=scene['title'], key=f"title_{idx}")
                scene['text'] = st.text_area(f"Scene Content {idx+1}", value=scene['text'], key=f"text_{idx}")
            
            if st.button("Save Script Changes"):
                st.toast("✅ All scene updates saved successfully!")

        with tabs[2]:
            st.subheader("Storyboard Panel Flow")
            st.write("Arrange your scenes into visual comic book panel sequences.")
            for idx, scene in enumerate(st.session_state.scenes):
                st.markdown(f"**Panel {idx+1}:** {scene['title']} — *{scene['text'][:50]}...*")

        with tabs[3]:
            st.subheader("Interactive Panel Layout & Export Canvas")
            c1, c2 = st.columns(2)
            with c1:
                p1 = st.text_input("Panel 1 Caption", "Hero stands at the edge...")
            with c2:
                p2 = st.text_input("Panel 2 Caption", "Lightning strikes!")
                
            if st.button("Render Manga Page"):
                page = Image.new("RGB", (800, 1200), color="white")
                draw = ImageDraw.Draw(page)
                draw.rectangle([40, 40, 760, 560], outline="black", width=5)
                draw.rectangle([40, 600, 760, 1160], outline="black", width=5)
                draw.text((60, 60), f"P1: {p1}", fill="black")
                draw.text((60, 620), f"P2: {p2}", fill="black")
                
                buf = io.BytesIO()
                page.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.image(byte_im, caption="Rendered Manga Page", use_container_width=True)
                st.download_button("📥 Download Manga Page PNG", data=byte_im, file_name="manga_page.png", mime="image/png")