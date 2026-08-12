import streamlit as st
import requests
import json
import base64
import html
import asyncio
import time
import re
from pathlib import Path
import pypdf
from docx import Document

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
SOURCES_DIR = APP_DIR / "sources"
BANNER_FILE = APP_DIR / "ka_abot_banner.png"
WELCOME_AUDIO_FILE = APP_DIR / "ka_abot_welcome.mp3"
REPLY_AUDIO_FILE = APP_DIR / "ka_abot_reply.mp3"

# ============================================================
# GEMINI API KEY & MODEL
# ============================================================
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
GEMINI_MODEL = "gemini-3.6-flash"

# ============================================================
# SMART FILE SEARCH (MAS MALAWAK NA PAGBASA PARA HINDI BITIN)
# ============================================================
@st.cache_data
def get_file_list():
    if not SOURCES_DIR.exists(): return []
    return [f.name for f in SOURCES_DIR.iterdir() if f.suffix.lower() in [".pdf", ".docx", ".txt"]]

def read_specific_file(filename):
    file_path = SOURCES_DIR / filename
    text = ""
    try:
        if file_path.suffix.lower() == ".pdf":
            reader = pypdf.PdfReader(file_path)
            for page in reader.pages[:4]: # Binasa ang unang 4 pages para kumpleto ang detalye
                extracted = page.extract_text()
                if extracted: text += extracted + "\n"
        elif file_path.suffix.lower() == ".docx":
            doc = Document(file_path)
            text = "\n".join([p.text for p in doc.paragraphs[:20] if p.text.strip()])
        elif file_path.suffix.lower() == ".txt":
            text = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"Error sa pagbasa ng {filename}: {e}")
    
    return text[:2500] # Tumaas nang kaunti para siguradong hindi mawala ang ibang rules

FILE_LIST = get_file_list()

# ============================================================
# SYSTEM PROMPT (MAS MAHIGPIT AT CONSISTENT)
# ============================================================

SYSTEM_INSTRUCTION = f"""
Ikaw ang opisyal na si Ka A-bot, ang Chatbot ng SSS Antipolo Branch.
Ang layunin mo ay magbigay ng tumpak, magalang, at mabilis na impormasyon sa mga kliyente tungkol sa SSS.

May access ka sa mga internal documents na ito: {', '.join(FILE_LIST) if FILE_LIST else 'Wala pang files'}.

MAHIGPIT NA ALITUNTUNIN:

1. Wika at Porma ng Tanong (Language Matching Rule):
- Unawain ang mga tanong kahit nasa estilong "jejemon", may typos, o naka-English.
- Kung English ang tanong, sumagot sa English. Kung Tagalog o Taglish, sagutin ito sa Tagalog/Taglish.

2. Pag-handle ng mga Tanong (STRICT & CONSISTENT):
- KAPAG MAY IBINIGAY NA INTERNAL REFERENCE DOCUMENT SA TANONG, DAPAT YON ANG UNAHING SURIIN AT GAMITIN. Kopyahin nang tumpak ang mga detalye mula rito. Huwag magbago ng sagot sa parehong tanong.
- Mag-ingat sa mga tanong na bitin o implicit (hal. "Bakit di pumasok hulog ko?", "May walk in ba?"). Iugnay at unawain ito bilang tanong patungkol sa mga transaksyon ng SSS.
- KUNG ANG TANONG AY WALANG KINALAMAN SA SSS, magalang na sabihin na tanging mga tanong na may kinalaman sa SSS service lamang ang iyong masasagot.

3. Paghanap ng Impormasyon:
- Unahin ang Internal Documents kung ang tanong ay tungkol sa mga programa (tulad ng Uplift Program). Ibigay ang buong detalye mula sa file nang malinaw at sunud-sunod.
- Kung wala sa files at wala sa sss.gov.ph, magalang na sabihin na makipag-ugnayan sa SSS Antipolo Branch.

4. FORMAT NG PAALALA:
Ilagay sa dulo: 💡 Paalala: Kung tapos ka nang magtanong, mangyaring i-click ang refresh/End service button sa ibaba upang mabura ang ating usapan at mapanatiling ligtas at pribado ang iyong mga impormasyon para sa susunod na gagamit.
"""

# ============================================================
# SESSION STATE & CSS
# ============================================================

if "messages" not in st.session_state: st.session_state.messages = []
if "voice_enabled" not in st.session_state: st.session_state.voice_enabled = True
if "welcomed" not in st.session_state: st.session_state.welcomed = False
if "latest_reply_audio" not in st.session_state: st.session_state.latest_reply_audio = None

st.markdown("""<style>.stApp {background: linear-gradient(180deg, #e1f5ff 0%, #c9ebfa 55%, #b9e2f4 100%);} #MainMenu, footer {visibility: hidden;} header {background: transparent !important;} .block-container {max-width: 950px !important; padding-top: 1.0rem !important; padding-bottom: 6rem !important;} .banner-wrap {width: 100%; border-radius: 18px; overflow: hidden; box-shadow: 0 7px 22px rgba(0, 70, 110, 0.13); margin-bottom: 18px;} .banner-wrap img {width: 100%; display: block;} .welcome-card {text-align: center; padding: 16px 10px 10px; color: #245b7c;} .robot {font-size: 34px; line-height: 1; margin-bottom: 7px;} .title {font-size: 22px; font-weight: 700; margin-bottom: 5px;} .text {font-size: 15px;} .user-bubble {background: #d9ecfa; border-radius: 18px 18px 5px 18px; padding: 11px 15px; margin: 8px 0 8px auto; max-width: 82%; color: #173f58;} .bot-bubble {background: #eef7fc; border-left: 4px solid #1f6b99; border-radius: 5px 18px 18px 18px; padding: 12px 15px; margin: 8px auto 8px 0; max-width: 90%; color: #183b4f;} .label {font-size: 12px; font-weight: 700; opacity: 0.72; margin-bottom: 4px;} .controls-title {text-align: center; color: #2a6385; font-size: 14px; font-weight: 700; margin: 8px 0 8px;} div.stButton > button {border-radius: 22px !important; min-height: 42px !important; font-weight: 600 !important; border: 1.5px solid #2c6c95 !important; background: white !important; color: #245d80 !important;} div.stButton > button:hover {border-color: #174b6d !important; color: #174b6d !important;} div[data-testid="stToggle"] label {color: #245d80 !important; font-weight: 600 !important;} .status-ok {text-align: center; color: #286c46; font-size: 12px; margin-top: 7px;} .ka-footer {text-align: center; color: #4c7d98; font-size: 12px; margin-top: 14px; margin-bottom: 8px;} div[data-testid="stChatInput"] {border-radius: 16px !important;}</style>""", unsafe_allow_html=True)

# ============================================================
# BANNER & AUDIO HELPERS (FIXED PRONUNCIATION & NUMBERS)
# ============================================================
if BANNER_FILE.exists():
    st.markdown('<div class="banner-wrap">', unsafe_allow_html=True)
    st.image(str(BANNER_FILE), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

def clean_text_for_speech(text: str) -> str:
    clean_text = text.split("💡")[0]
    
    # Linisin ang mga Markdown headers tulad ng ### at asterisks
    clean_text = re.sub(r'#{1,6}\s*', '', clean_text)
    clean_text = re.sub(r'[*#_`~]', '', clean_text)
    
    # Pagbigkas ng My.SSS at mga Acronyms
    clean_text = clean_text.replace("My.SSS", "Mai Es Es Es").replace("my.sss", "Mai Es Es Es")
    clean_text = clean_text.replace("MySSS", "Mai Es Es Es").replace("mysss", "Mai Es Es Es")
    clean_text = clean_text.replace("SSS", "Es Es Es").replace("sss", "Es Es Es")
    clean_text = clean_text.replace("ID", "Ayditi").replace("id", "Ayditi")
    
    # Pagbigkas ng www at .gov.ph
    clean_text = clean_text.replace("www.", "W W W dot ").replace("WWW.", "W W W dot ")
    clean_text = clean_text.replace(".gov.ph", " dot gov dot p h").replace(".GOV.PH", " dot gov dot p h")
    clean_text = clean_text.replace(".com", " dot kom")

    # CONVERT DIGIT NUMBERS TO ENGLISH WORDS PARA CONSISTENT SA BOSES
    digit_map = {
        '1': 'One', '2': 'Two', '3': 'Three', '4': 'Four', '5': 'Five',
        '6': 'Six', '7': 'Seven', '8': 'Eight', '9': 'Nine', '0': 'Zero'
    }
    
    def translate_digits(match):
        num_str = match.group(0)
        # Kung single digit (tulad ng 1., 2., 3. sa listahan), i-convert sa English word
        if len(num_str) == 1 and num_str in digit_map:
            return digit_map[num_str]
        return num_str

    clean_text = re.sub(r'\b\d+\b', translate_digits, clean_text)
    
    return clean_text.strip()[:1800]

def make_speech_audio(text: str, output_file: Path):
    try:
        import edge_tts
        async def generate():
            communicate = edge_tts.Communicate(clean_text_for_speech(text), "fil-PH-AngeloNeural")
            await communicate.save(str(output_file))
        asyncio.run(generate())
        return output_file
    except: return None

def play_invisible_audio(audio_file: Path):
    if audio_file.exists():
        encoded = base64.b64encode(audio_file.read_bytes()).decode("utf-8")
        st.markdown(f'<audio autoplay src="data:audio/mp3;base64,{encoded}"></audio>', unsafe_allow_html=True)

if st.session_state.voice_enabled and not st.session_state.welcomed:
    play_invisible_audio(make_speech_audio("Magandang araw! Ako po si Ka A-bot, ang Chatbot ng SSS Antipolo Branch. Para sa inyong mga katanungan, i-type lamang at ikalulugod ko na kayo po ay matugunan.", WELCOME_AUDIO_FILE))
    st.session_state.welcomed = True

# ============================================================
# CHAT AREA (MALINIS NA RENDER NG MARKDOWN)
# ============================================================
if not st.session_state.messages:
    st.markdown('<div class="welcome-card"><div class="robot">🤖</div><div class="title">Kumusta po!</div><div class="text">Ako po si Ka A-bot.<br>Ano po ang maitutulong ko sa inyo ngayon?</div></div>', unsafe_allow_html=True)
else:
    for message in st.session_state.messages:
        safe_text = html.escape(message["content"])
        # Alisin ang mga ### headers sa visual chat box para maging malinis
        safe_text = re.sub(r'#{1,6}\s*', '', safe_text)
        safe_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', safe_text)
        safe_text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', safe_text)
        safe_text = safe_text.replace("\n", "<br>")

        if message["role"] == "user": 
            st.markdown(f'<div class="user-bubble"><div class="label">👤 Kayo</div>{safe_text}</div>', unsafe_allow_html=True)
        else: 
            st.markdown(f'<div class="bot-bubble"><div class="label">🤖 Ka A-bot</div>{safe_text}</div>', unsafe_allow_html=True)
            
    if st.session_state.latest_reply_audio:
        play_invisible_audio(st.session_state.latest_reply_audio)
        st.session_state.latest_reply_audio = None

# ============================================================
# CONTROLS
# ============================================================
col1, col2 = st.columns([1, 1])
with col1:
    current_voice = st.toggle("🔊 Voice Prompt On/Off", value=st.session_state.voice_enabled)
    if current_voice != st.session_state.voice_enabled: st.session_state.voice_enabled = current_voice; st.rerun()
with col2:
    if st.button("🔄 New User / End Service", use_container_width=True):
        st.session_state.messages = []; st.session_state.welcomed = False; st.rerun()

# ============================================================
# GEMINI CHAT LOGIC
# ============================================================
prompt = st.chat_input("I-type ang iyong tanong...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    matched_content = ""
    for filename in FILE_LIST:
        if any(kw in prompt.lower() for kw in filename.lower().split() if len(kw) > 3):
            matched_content = read_specific_file(filename)
            break

    contents = []
    if matched_content:
        contents.append({"role": "user", "parts": [{"text": f"GAMITIN ITO BILANG OPISYAL NA SANGGUNIAN SA PAG SAGOT (KOPYAHIN NG TUMPAK ANG MGA DETALYE):\n{matched_content}"}]})
    
    for msg in st.session_state.messages[-4:]:
        contents.append({"role": "user" if msg["role"] == "user" else "model", "parts": [{"text": msg["content"]}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {"systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]}, "contents": contents}
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY.strip()}

    try:
        with st.spinner("Nag-iisip si Ka A-bot..."):
            response = None
            wait_time = 2
            for _ in range(4):
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                if response.status_code != 503: break
                time.sleep(wait_time); wait_time *= 2
            
            if response and response.ok:
                parts = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [])
                bot_reply = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
                st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                if st.session_state.voice_enabled: st.session_state.latest_reply_audio = make_speech_audio(bot_reply, REPLY_AUDIO_FILE)
                st.rerun()
            else: st.error("Masyadong maraming gumagamit ngayon, pakisubukan ulit.")
    except Exception as e: st.error(f"Error: {e}")

st.markdown('<div class="ka-footer">SSS Antipolo Branch • Ka A-bot</div>', unsafe_allow_html=True)
