import streamlit as st
import requests
import json
import base64
import html
import asyncio
import re
from pathlib import Path

# ============================================================
# KA A-BOT — SSS ANTIPOLO BRANCH
# ============================================================

st.set_page_config(
    page_title="Ka A-bot - SSS Antipolo",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_DIR = Path(__file__).resolve().parent
BANNER_FILE = APP_DIR / "ka_abot_banner.png"
WELCOME_AUDIO_FILE = APP_DIR / "ka_abot_welcome.mp3"
REPLY_AUDIO_FILE = APP_DIR / "ka_abot_reply.mp3"

# ============================================================
# GEMINI API KEY
# ============================================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GEMINI_MODEL = "gemini-3.6-flash"

# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_INSTRUCTION = """
Ikaw ang opisyal na si Ka A-bot, ang Chatbot ng SSS Antipolo Branch.
Ang layunin mo ay magbigay ng tumpak, magalang, at mabilis na impormasyon sa mga kliyente.

Sundin mo nang mahigpit ang mga alituntuning ito:

1. Wika at Porma ng Tanong (Language Matching Rule):
- Unawain ang mga tanong kahit ito ay nasa estilong "jejemon", may mga typographical error (typos), o nakasulat sa English.
- Kung ang tanong ay nakasulat sa English, DAPAT mong sagutin ito sa English. Kung sa Tagalog o Taglish, sagutin ito sa Tagalog/Taglish.

2. Pag-handle ng mga Tanong at Implicit/Bitin na Tanong:
- Pangunahing pag-aralan at kunin ang sagot mula sa opisyal na website ng SSS (sss.gov.ph).
- Mag-ingat sa mga tanong na mukhang maikling pahayag, bitin, o implicit ngunit maaari namang mai-konekta sa serbisyo ng SSS. (Halimbawa: "Bakit di pumasok hulog ko?", "May walk in ba kayo?")
- Huwag itong tanggihan. Sa halip, iugnay at unawain ito bilang tanong patungkol sa mga transaksyon ng SSS.
- Para sa mga tanong na talagang walang kinalaman sa SSS, magalang na sabihin na tanging mga tanong na may kinalaman sa SSS service lamang ang iyong masasagot.

3. FORMAT NG PAALALA:
Ilagay sa pinakadulo ng Bawat Tugon:
💡 Paalala: Kung tapos ka nang magtanong, mangyaring i-click ang New User/End Service button sa ibaba upang mabura ang ating usapan at mapanatiling ligtas at pribado ang iyong mga impormasyon para sa susunod na gagamit.
"""

# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "voice_enabled" not in st.session_state:
    st.session_state.voice_enabled = True

if "welcomed" not in st.session_state:
    st.session_state.welcomed = False

if "welcome_nonce" not in st.session_state:
    st.session_state.welcome_nonce = 0

if "latest_reply_audio" not in st.session_state:
    st.session_state.latest_reply_audio = None

# ============================================================
# CSS — CLEAN KIOSK LAYOUT
# ============================================================

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #e1f5ff 0%, #c9ebfa 55%, #b9e2f4 100%);
    }

    #MainMenu, footer {
        visibility: hidden;
    }

    header {
        background: transparent !important;
    }

    .block-container {
        max-width: 950px !important;
        padding-top: 1.0rem !important;
        padding-bottom: 6rem !important;
    }

    .banner-wrap {
        width: 100%;
        border-radius: 18px;
        overflow: hidden;
        box-shadow: 0 7px 22px rgba(0, 70, 110, 0.13);
        margin-bottom: 18px;
    }

    .banner-wrap img {
        width: 100%;
        display: block;
    }

    .welcome-card {
        text-align: center;
        padding: 16px 10px 10px;
        color: #245b7c;
    }

    .welcome-card .robot {
        font-size: 34px;
        line-height: 1;
        margin-bottom: 7px;
    }

    .welcome-card .title {
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .welcome-card .text {
        font-size: 15px;
    }

    .user-bubble {
        background: #d9ecfa;
        border-radius: 18px 18px 5px 18px;
        padding: 11px 15px;
        margin: 8px 0 8px auto;
        max-width: 82%;
        color: #173f58;
    }

    .bot-bubble {
        background: #eef7fc;
        border-left: 4px solid #1f6b99;
        border-radius: 5px 18px 18px 18px;
        padding: 12px 15px;
        margin: 8px auto 8px 0;
        max-width: 90%;
        color: #183b4f;
    }

    .label {
        font-size: 12px;
        font-weight: 700;
        opacity: 0.72;
        margin-bottom: 4px;
    }

    .controls-title {
        text-align: center;
        color: #2a6385;
        font-size: 14px;
        font-weight: 700;
        margin: 8px 0 8px;
    }

    div.stButton > button {
        border-radius: 22px !important;
        min-height: 42px !important;
        font-weight: 600 !important;
        border: 1.5px solid #2c6c95 !important;
        background: white !important;
        color: #245d80 !important;
    }

    div.stButton > button:hover {
        border-color: #174b6d !important;
        color: #174b6d !important;
    }

    div[data-testid="stToggle"] label {
        color: #245d80 !important;
        font-weight: 600 !important;
    }

    .status-ok {
        text-align: center;
        color: #286c46;
        font-size: 12px;
        margin-top: 7px;
    }

    .ka-footer {
        text-align: center;
        color: #4c7d98;
        font-size: 12px;
        margin-top: 14px;
        margin-bottom: 8px;
    }

    div[data-testid="stChatInput"] {
        border-radius: 16px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# BANNER
# ============================================================

if BANNER_FILE.exists():
    st.markdown('<div class="banner-wrap">', unsafe_allow_html=True)
    st.image(str(BANNER_FILE), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.error("Hindi makita ang ka_abot_banner.png.")

# ============================================================
# AUDIO HELPERS & TEXT CLEANER
# ============================================================

def clean_text_for_speech(text: str) -> str:
    clean_text = text.split("💡")[0]
    clean_text = re.sub(r'[*#_`~]', '', clean_text)
    
    clean_text = clean_text.replace("SSS", "Es Es Es").replace("sss", "Es Es Es")
    clean_text = clean_text.replace("ID", "Ayditi").replace("id", "Ayditi")
    clean_text = clean_text.replace("www.", "W W W dot ").replace("WWW.", "W W W dot ")
    clean_text = clean_text.replace(".gov.ph", " dot gov dot pi").replace(".GOV.PH", " dot gov dot pi")
    clean_text = clean_text.replace(".com", " dot kom")
    
    return clean_text.strip()[:1800]

def make_speech_audio(text: str, output_file: Path):
    clean_text = clean_text_for_speech(text)

    try:
        import edge_tts
        async def generate():
            communicate = edge_tts.Communicate(clean_text, "fil-PH-AngeloNeural")
            await communicate.save(str(output_file))
        asyncio.run(generate())
        if output_file.exists():
            return output_file
    except Exception:
        pass

    try:
        from gtts import gTTS
        tts = gTTS(text=clean_text, lang="tl", slow=False)
        tts.save(str(output_file))
        if output_file.exists():
            return output_file
    except Exception:
        pass

    return None

WELCOME_TEXT = "Magandang araw! Ako po si Ka A-bot, ang Chatbot ng SSS Antipolo Branch. Para sa inyong mga katanungan, i-type lamang at ikalulugod ko na kayo po ay matugunan."
make_speech_audio(WELCOME_TEXT, WELCOME_AUDIO_FILE)

def make_reply_voice(text: str):
    return make_speech_audio(text, REPLY_AUDIO_FILE)

def play_invisible_audio(audio_file: Path):
    if audio_file.exists():
        encoded = base64.b64encode(audio_file.read_bytes()).decode("utf-8")
        st.markdown(f'<audio autoplay src="data:audio/mp3;base64,{encoded}"></audio>', unsafe_allow_html=True)

# ============================================================
# WELCOME VOICE (ISANG BESES LANG TUSTRUGOT)
# ============================================================

if st.session_state.voice_enabled and not st.session_state.welcomed:
    play_invisible_audio(WELCOME_AUDIO_FILE)
    st.session_state.welcomed = True

# ============================================================
# CHAT AREA
# ============================================================

if not st.session_state.messages:
    st.markdown(
        """
        <div class="welcome-card">
            <div class="robot">🤖</div>
            <div class="title">Kumusta po!</div>
            <div class="text">
                Ako po si Ka A-bot.<br>
                Ano po ang maitutulong ko sa inyo ngayon?
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    for message in st.session_state.messages:
        safe_text = html.escape(message["content"])
        safe_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_text)
        safe_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', safe_text)
        safe_text = safe_text.replace("\n", "<br>")

        if message["role"] == "user":
            st.markdown(
                f"""
                <div class="user-bubble">
                    <div class="label">👤 Kayo</div>
                    {safe_text}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="bot-bubble">
                    <div class="label">🤖 Ka A-bot</div>
                    {safe_text}
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.session_state.latest_reply_audio:
        play_invisible_audio(st.session_state.latest_reply_audio)
        st.session_state.latest_reply_audio = None

# ============================================================
# CONTROLS
# ============================================================

st.markdown('<div class="controls-title">Ka A-bot Controls</div>', unsafe_allow_html=True)

col1, col2 = st.columns([1, 1])

with col1:
    current_voice = st.toggle(
        "🔊 Voice Prompt On/Off",
        value=st.session_state.voice_enabled,
        key="voice_control",
    )
    if current_voice != st.session_state.voice_enabled:
        st.session_state.voice_enabled = current_voice
        st.rerun()

with col2:
    if st.button("🔄 New User / End Service", use_container_width=True, key="new_user_button"):
        st.session_state.messages = []
        st.session_state.voice_enabled = True
        st.session_state.welcomed = False
        st.session_state.welcome_nonce += 1
        st.rerun()

# ============================================================
# API KEY STATUS
# ============================================================

API_KEY_READY = isinstance(GEMINI_API_KEY, str) and bool(GEMINI_API_KEY.strip())

if API_KEY_READY:
    st.markdown('<div class="status-ok">● Ka A-bot is ready</div>', unsafe_allow_html=True)
else:
    st.warning('Wala pang Gemini API Key.')

# ============================================================
# CHAT INPUT + GEMINI
# ============================================================

prompt = st.chat_input("I-type ang iyong tanong o concern tungkol sa SSS...")

if prompt:
    if not API_KEY_READY:
        st.error("Hindi makapagsagot si Ka A-bot dahil wala pang Gemini API Key.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})

        contents = []
        for msg in st.session_state.messages:
            contents.append({
                "role": "user" if msg["role"] == "user" else "model",
                "parts": [{"text": msg["content"]}],
            })

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": 2048},
        }
        headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY.strip()}

        try:
            with st.spinner("Nag-iisip si Ka A-bot..."):
                response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            try:
                res_json = response.json()
            except Exception:
                res_json = {}

            if response.ok:
                candidates = res_json.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}) .get("parts", [])
                    bot_reply = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()

                    if bot_reply:
                        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

                        if st.session_state.voice_enabled:
                            reply_file = make_reply_voice(bot_reply)
                            if reply_file:
                                st.session_state.latest_reply_audio = reply_file

                        st.rerun() 
                    else:
                        st.error("Nakakonekta sa Gemini pero walang text na sagot na natanggap.")
                else:
                    st.error("Nakakonekta sa Gemini pero walang candidate response.")
            else:
                st.error(f"Error mula sa Google Gemini API: {response.text}")

        except Exception as e:
            st.error(f"Network error habang kumokonekta sa Gemini API: {e}")

# ============================================================
# FOOTER
# ============================================================

st.markdown('<div class="ka-footer">SSS Antipolo Branch • Ka A-bot</div>', unsafe_allow_html=True)
