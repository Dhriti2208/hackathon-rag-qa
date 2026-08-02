"""
STEP 5: The Streamlit chat interface — Fully Featured HTE Portal.
Merged version: teammate's UI polish (sidebar, native feedback, loading
states) + real backend (login, actual RAG answers, real summarize/compare,
per-source scores, conflict detection, browse documents).

Run with: streamlit run app/app.py
"""

import streamlit as st
import sys
import os
import time
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from rag_engine.rag_pipeline import (
    generate_answer,
    get_all_document_names,
    summarize_document,
    compare_documents,
    explain_simply,
    get_documents_browse_list,
)
from auth import register_user, login_user, save_history, load_history, save_feedback

st.set_page_config(page_title="HTE Portal", page_icon="🏛️", layout="wide")

# ----------------------------
# DARK MODE TOGGLE
# Our custom palette hardcodes colors (needed for the seal/paper identity to
# render consistently), which means Streamlit's own light/dark theme menu has
# nothing left to switch. So we run our own toggle and branch the palette on it.
# ----------------------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

with st.sidebar:
    st.toggle("🌙  Dark mode", key="dark_mode")

# ----------------------------
# THEME — "Rajmudra": an official-seal identity for a government
# knowledge portal. Deep archive-navy + verification-gold, on a warm
# paper ground, with a Fraunces/Inter/IBM Plex Mono type system.
# Signature element: a circular gold "verification seal" that stands
# in for the confidence score on every grounded answer.
# ----------------------------
NAVY = "#0B1E37"        # authority — sidebar, headings, primary buttons
NAVY_MID = "#15335C"    # hover / secondary panels
GOLD = "#B98A2E"        # accent — the seal, rules, focus states
GOLD_LIGHT = "#E7C77E"  # button text on navy, highlights

if st.session_state.dark_mode:
    PAPER = "#11151C"       # main ground — near-black, warm-neutral
    CARD = "#1A2028"        # message / panel surface
    INK = "#EDE7D8"         # primary text (light, on the dark ground)
    MUTED = "#9C9585"       # secondary text
    BORDER = "#333B47"      # hairline border
    MAROON = "#C97078"      # conflict / error accent, lifted for dark contrast
else:
    PAPER = "#F6F3EC"       # main ground — warm, not the cliché cream+terracotta pair
    CARD = "#FCFBF8"        # message / panel surface, slightly lighter than PAPER
    INK = "#1C2431"         # primary text
    MUTED = "#6B6357"       # secondary text (warm gray, ties to paper)
    BORDER = "#E1DACB"      # warm hairline border
    MAROON = "#7A2E33"      # conflict / error accent — replaces generic red

APP_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

/* Warm paper ground — kept light so reruns repaint instantly and don't flash */
html, body {{ background-color: {PAPER}; }}
.stApp {{
    background-color: {PAPER}; color: {INK};
    background-image: radial-gradient(circle at 100% 0%, rgba(185,138,46,0.08), transparent 45%);
    transition: background-color 0.1s ease;
}}
[data-testid="stAppViewContainer"] > .main {{ padding-top: 1.2rem; }}

/* Hide Streamlit's dev-mode chrome (Deploy/Stop/hamburger) — it ignores our
   theme and looks out of place on a government portal */
header[data-testid="stHeader"] {{ display: none !important; }}
#MainMenu {{ visibility: hidden !important; }}
footer {{ visibility: hidden !important; }}

::selection {{ background: {GOLD}55; }}
::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 8px; }}
::-webkit-scrollbar-thumb:hover {{ background: {GOLD}; }}

/* Force real text color everywhere content renders. Streamlit's own markdown/
   expander/dataframe text ships a fixed gray that only happened to look right
   on a light background — on the dark palette it went near-invisible. */
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stExpander"] p,
[data-testid="stExpander"] li,
[data-testid="stExpander"] summary,
[data-testid="stAlert"] p,
[data-testid="stAlert"] li,
label, .stSelectbox label, .stTextInput label {{
    color: {INK} !important;
}}
[data-testid="stCaptionContainer"] p, .stCaption p {{ color: {MUTED} !important; }}
[data-testid="stDataFrame"] * {{ color: {INK} !important; }}
[data-testid="stExpander"] svg {{ fill: {INK} !important; }}

/* Re-affirm our own components' colors at higher specificity so the broad
   rule above doesn't swallow them */
[data-testid="stMarkdownContainer"] .cite-chip {{ color: {NAVY} !important; }}
[data-testid="stMarkdownContainer"] .seal-pct {{ color: {NAVY} !important; }}
[data-testid="stMarkdownContainer"] .seal-label {{ color: {GOLD} !important; }}
[data-testid="stMarkdownContainer"] .seal-meta .m1 {{ color: {MUTED} !important; }}
[data-testid="stMarkdownContainer"] .seal-meta .m1 b {{ color: {INK} !important; }}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
[data-testid="stSidebar"] label {{ color: #EDE7D8 !important; }}

/* Sidebar — deep archive navy with a gold hairline edge */
[data-testid="stSidebar"] {{
    background-color: {NAVY};
    border-right: 1px solid {GOLD}33;
}}
[data-testid="stSidebar"] * {{ color: #EDE7D8 !important; }}

/* Selectbox control — force navy on every nested BaseWeb layer, since the
   visible box is several levels deep and inherits an inline white fill */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {{
    background-color: {NAVY_MID} !important;
    border: 1px solid {GOLD}55 !important;
    border-radius: 6px !important;
}}
[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] * {{
    background-color: transparent !important;
    color: #EDE7D8 !important;
    -webkit-text-fill-color: #EDE7D8 !important;
}}
[data-testid="stSidebar"] [data-testid="stSelectbox"] svg {{ fill: #EDE7D8 !important; }}
[data-testid="stSidebar"] svg {{ fill: #EDE7D8 !important; }}
[data-testid="stSidebar"] hr {{ border-color: {GOLD}33; }}
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small {{ color: #B9B0A0 !important; }}

/* Sidebar conversation history — count badge vs. individual question rows,
   styled distinctly so they don't read as the same repeated element */
.hist-header {{
    display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;
}}
.hist-header .label {{ font-size: 11px; font-weight: 600; letter-spacing: 1.4px; text-transform: uppercase; color: #B9B0A0; }}
.hist-header .count {{
    font-family: 'IBM Plex Mono', monospace; font-size: 11px; font-weight: 600;
    color: {NAVY}; background: {GOLD_LIGHT}; border-radius: 20px; padding: 1px 8px;
}}
.hist-item {{
    display: flex; align-items: baseline; gap: 7px; padding: 5px 2px;
    border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 12.5px; color: #C9C2B3 !important;
}}
.hist-item .tick {{ color: {GOLD}; flex-shrink: 0; }}

/* Popover list that opens on click renders outside the sidebar in a portal —
   theme it separately so options stay readable */
div[data-baseweb="popover"] li {{ background-color: {CARD} !important; color: {INK} !important; }}
div[data-baseweb="popover"] li:hover {{ background-color: {GOLD}22 !important; }}


/* Sidebar eyebrow labels */
.sb-eyebrow {{
    font-family: 'Inter', sans-serif; font-size: 10.5px; font-weight: 600;
    letter-spacing: 1.6px; text-transform: uppercase; color: {GOLD_LIGHT} !important;
    margin-bottom: 2px;
}}

/* Brand bar — seal mark + Fraunces wordmark + eyebrow */
.brand-bar {{
    display: flex; align-items: center; gap: 14px;
    padding: 6px 2px 22px 2px; border-bottom: 1px solid {BORDER}; margin-bottom: 26px;
}}
.brand-seal {{
    width: 44px; height: 44px; border-radius: 50%; flex-shrink: 0;
    background: radial-gradient(circle at 35% 30%, {GOLD_LIGHT}, {GOLD} 60%, #8C6A22 100%);
    border: 1px solid {GOLD};
    box-shadow: 0 0 0 3px {PAPER}, 0 0 0 4px {BORDER};
    display: flex; align-items: center; justify-content: center;
}}
.brand-seal span {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 17px; color: {NAVY}; }}
.brand-bar .brand-text {{ display: flex; flex-direction: column; gap: 2px; }}
.brand-bar .eyebrow {{
    font-size: 10.5px; font-weight: 600; letter-spacing: 1.6px; text-transform: uppercase; color: {GOLD};
}}
.brand-bar .name {{ font-family: 'Fraunces', serif; font-size: 25px; font-weight: 600; color: {INK}; line-height: 1.1; }}
.brand-bar .tagline {{ font-size: 13px; color: {MUTED}; font-style: italic; }}

/* Section headers */
.section-title {{
    font-family: 'Fraunces', serif; font-size: 30px; font-weight: 600; color: {INK}; margin-bottom: 6px;
}}
.section-sub {{
    font-size: 14px; color: {MUTED}; margin-bottom: 22px; padding-left: 12px; border-left: 2.5px solid {GOLD};
}}

/* Text inputs */
.stTextInput input {{
    border-radius: 6px !important;
    border: 1.5px solid {BORDER} !important;
    padding: 12px 14px !important;
    background-color: {CARD} !important;
    color: {INK} !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}}
.stTextInput input:focus {{
    border-color: {GOLD} !important;
    box-shadow: 0 0 0 3px {GOLD}26 !important;
}}
.stTextInput label {{ color: {INK} !important; font-weight: 500; font-size: 13px; }}

/* Tabs — gold underline, tracked small caps */
.stTabs [data-baseweb="tab-list"] {{ gap: 30px; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{
    height: 44px; background-color: transparent !important; border-radius: 0 !important;
    padding: 0px 2px !important; font-weight: 600; font-size: 13.5px;
    letter-spacing: 0.3px; color: {MUTED} !important;
}}
.stTabs [aria-selected="true"] {{
    color: {NAVY} !important; border-bottom: 2.5px solid {GOLD} !important;
    background-color: transparent !important;
}}

/* Primary buttons — navy with gold ink, small-caps tracking, official tone */
.stButton button {{
    border-radius: 6px; font-weight: 600; font-size: 13.5px;
    letter-spacing: 0.4px; border: 1px solid {NAVY};
    background-color: {NAVY}; color: {GOLD_LIGHT} !important;
    transition: background-color 0.15s ease, transform 0.1s ease;
}}
.stButton button:hover {{ background-color: {NAVY_MID}; color: {GOLD_LIGHT} !important; transform: translateY(-1px); }}
.stButton button:active {{ transform: translateY(0); }}
.stButton button:focus {{ color: {GOLD_LIGHT} !important; }}
[data-testid="stSidebar"] .stButton button {{
    background-color: transparent; border: 1px solid {GOLD}55; color: #EDE7D8 !important;
}}
[data-testid="stSidebar"] .stButton button:hover {{ border-color: {GOLD}; background-color: rgba(185,138,46,0.12); }}

/* Button labels render as a nested <p>, which the broad text-contrast fix
   above was overriding with dark ink — pin them back to the button's own text color */
.stButton button p, .stButton button [data-testid="stMarkdownContainer"] p {{
    color: {GOLD_LIGHT} !important;
}}
[data-testid="stSidebar"] .stButton button p,
[data-testid="stSidebar"] .stButton button [data-testid="stMarkdownContainer"] p {{
    color: #EDE7D8 !important;
}}


/* Chat message cards — quiet document-card feel, gold left rule on replies */
[data-testid="stChatMessage"] {{
    background-color: {CARD}; border-radius: 8px; padding: 12px 14px;
    margin-bottom: 12px; border: 1px solid {BORDER};
    box-shadow: 0 1px 2px rgba(11,30,55,0.04);
}}
[data-testid="stChatMessageAvatarAssistant"] ~ div [data-testid="stChatMessage"],
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{
    border-left: 3px solid {GOLD};
}}

/* Expanders */
div[data-testid="stExpander"] {{ border-radius: 8px; border: 1px solid {BORDER}; background-color: {CARD}; }}

/* Dataframe / Browse Documents table */
.stDataFrame thead tr th {{
    background-color: {NAVY} !important; color: {GOLD_LIGHT} !important; font-weight: 600 !important;
    text-transform: uppercase; letter-spacing: 0.5px; font-size: 12px !important;
}}
.stDataFrame {{ border-radius: 8px; overflow: hidden; border: 1px solid {BORDER}; }}

/* Progress bar fallback */
.stProgress > div > div {{ background-color: {GOLD} !important; border-radius: 6px; }}

/* Alerts — recolored to the palette instead of stock red/orange/blue */
[data-testid="stAlertContentError"], div[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {{
    background-color: {MAROON}14 !important; border: 1px solid {MAROON}55 !important; border-radius: 8px !important;
}}
[data-testid="stAlertContentWarning"], div[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) {{
    background-color: {GOLD}17 !important; border: 1px solid {GOLD}66 !important; border-radius: 8px !important;
}}
[data-testid="stAlertContentInfo"], div[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) {{
    background-color: {NAVY}0F !important; border: 1px solid {NAVY}44 !important; border-radius: 8px !important;
}}
div[data-testid="stAlert"] p {{ color: {INK} !important; }}

/* --- Verification seal (replaces the plain confidence progress bar) --- */
.seal-row {{ display: flex; align-items: center; gap: 14px; margin: 6px 0 10px 0; }}
.seal-ring {{
    width: 60px; height: 60px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 1px 3px rgba(11,30,55,0.15);
}}
.seal-inner {{
    width: 48px; height: 48px; border-radius: 50%; background: {CARD};
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    border: 1px solid {BORDER};
}}
.seal-pct {{ font-family: 'IBM Plex Mono', monospace; font-weight: 600; font-size: 14px; color: {NAVY}; line-height: 1; }}
.seal-label {{ font-size: 7px; font-weight: 600; letter-spacing: 1px; color: {GOLD}; margin-top: 2px; }}
.seal-meta {{ display: flex; flex-direction: column; gap: 2px; }}
.seal-meta .m1 {{ font-size: 12.5px; color: {MUTED}; }}
.seal-meta .m1 b {{ color: {INK}; }}

/* Source / citation chips */
.cite-chip {{
    display: inline-flex; align-items: center; gap: 6px;
    font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: {NAVY};
    background: {GOLD}14; border: 1px solid {GOLD}44; border-radius: 20px;
    padding: 2px 9px; margin: 2px 4px 2px 0;
}}

/* Login split panel */
.auth-illustration {{
    background-color: {CARD}; border-radius: 14px; height: 480px;
    border: 1px solid {BORDER};
    display: flex; align-items: center; justify-content: center; flex-direction: column;
}}
.auth-illustration svg {{ margin-bottom: 22px; }}
.auth-illustration .caption {{ color: {MUTED}; font-size: 14.5px; text-align: center; padding: 0 34px; line-height: 1.6; }}
.auth-illustration .caption b {{ color: {INK}; }}
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)


def render_seal(confidence, sublabel=None):
    """Render the signature 'verification seal' badge for a grounded answer,
    replacing a plain progress bar with a stamp-style confidence indicator."""
    conf = max(0, min(100, confidence))
    deg = conf * 3.6
    meta = f'<div class="m1">{sublabel}</div>' if sublabel else ""
    st.markdown(
        f"""
        <div class="seal-row">
            <div class="seal-ring" style="background: conic-gradient({GOLD} {deg}deg, {BORDER} {deg}deg);">
                <div class="seal-inner">
                    <span class="seal-pct">{conf}%</span>
                    <span class="seal-label">VERIFIED</span>
                </div>
            </div>
            <div class="seal-meta">
                <div class="m1"><b>Answer confidence</b> — grounded in cited source documents</div>
                {meta}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------------------
# LOGIN / REGISTER SCREEN
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if not st.session_state.logged_in:
    st.markdown(
        '<div class="brand-bar">'
        '<div class="brand-seal"><span>HTE</span></div>'
        '<div class="brand-text">'
        '<span class="eyebrow">Higher &amp; Technical Education Dept. · Maharashtra</span>'
        '<span class="name">HTE Portal</span>'
        '</div></div>',
        unsafe_allow_html=True
    )

    illustration_col, form_col = st.columns([1, 1.1], gap="large")

    with illustration_col:
        svg_illustration = """
        <svg width="220" height="230" viewBox="0 0 220 230" xmlns="http://www.w3.org/2000/svg">
            <rect x="34" y="16" width="122" height="164" rx="6" fill="#FCFBF8" stroke="#0B1E37" stroke-width="1.5"/>
            <rect x="34" y="16" width="122" height="10" rx="6" fill="#0B1E37"/>
            <rect x="50" y="42" width="86" height="7" rx="3.5" fill="#0B1E37" opacity="0.85"/>
            <rect x="50" y="60" width="70" height="5" rx="2.5" fill="#6B6357" opacity="0.55"/>
            <rect x="50" y="73" width="76" height="5" rx="2.5" fill="#6B6357" opacity="0.55"/>
            <rect x="50" y="86" width="58" height="5" rx="2.5" fill="#6B6357" opacity="0.55"/>
            <rect x="50" y="106" width="76" height="5" rx="2.5" fill="#6B6357" opacity="0.35"/>
            <rect x="50" y="119" width="64" height="5" rx="2.5" fill="#6B6357" opacity="0.35"/>
            <rect x="50" y="132" width="70" height="5" rx="2.5" fill="#6B6357" opacity="0.35"/>
            <rect x="50" y="152" width="40" height="5" rx="2.5" fill="#6B6357" opacity="0.3"/>
            <g transform="translate(150,150)">
                <circle r="42" fill="none" stroke="#B98A2E" stroke-width="1.6" stroke-dasharray="3.4 4.2" opacity="0.8"/>
                <circle r="34" fill="#FCFBF8" stroke="#B98A2E" stroke-width="2"/>
                <circle r="34" fill="url(#sealGrad)" opacity="0.16"/>
                <path d="M-14 1 L-4 11 L16 -12" stroke="#0B1E37" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                <text x="0" y="-46" text-anchor="middle" font-family="Inter, sans-serif" font-size="7.5" font-weight="700" letter-spacing="1.5" fill="#7A6A3E">VERIFIED</text>
            </g>
            <defs>
                <radialGradient id="sealGrad" cx="35%" cy="30%" r="70%">
                    <stop offset="0%" stop-color="#E7C77E"/>
                    <stop offset="100%" stop-color="#B98A2E"/>
                </radialGradient>
            </defs>
        </svg>
        """
        st.markdown(
            f'<div class="auth-illustration">{svg_illustration}'
            '<div class="caption">Ask in <b>English, Hindi or Marathi</b> and get '
            'answers grounded in official Government Resolutions, circulars and orders — '
            'every response carries its sources.</div>'
            '</div>',
            unsafe_allow_html=True
        )

    with form_col:
        login_tab, register_tab = st.tabs(["Sign In", "Create Account"])

        with login_tab:
            st.markdown('<div class="section-title">Welcome back</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Sign in to continue to your assistant</div>', unsafe_allow_html=True)
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign In", use_container_width=True):
                if login_username and login_password:
                    success, message = login_user(login_username, login_password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.username = login_username
                        st.session_state.messages = load_history(login_username)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.error("Please enter both username and password.")

        with register_tab:
            st.markdown('<div class="section-title">Create your account</div>', unsafe_allow_html=True)
            st.markdown('<div class="section-sub">Get started with the HTE Assistant</div>', unsafe_allow_html=True)
            reg_username = st.text_input("Choose a username", key="reg_username")
            reg_password = st.text_input("Choose a password", type="password", key="reg_password")
            if st.button("Create Account", use_container_width=True):
                if reg_username and reg_password:
                    success, message = register_user(reg_username, reg_password)
                    if success:
                        st.success(message + " Please sign in now.")
                    else:
                        st.error(message)
                else:
                    st.error("Please enter both a username and password.")

    st.stop()


# ----------------------------
# SESSION STATE
# ----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = load_history(st.session_state.username)


def find_source_pdf(source_txt_name):
    pdf_name = source_txt_name.replace(".txt", ".pdf")
    pdf_path = os.path.join(os.path.dirname(__file__), "..", "data", "raw_pdfs", pdf_name)
    if os.path.exists(pdf_path):
        return pdf_path
    return None


# ----------------------------
# SIDEBAR
# ----------------------------
with st.sidebar:
    st.markdown(
        '<div class="sb-eyebrow">Government of Maharashtra</div>'
        '<span style="font-family:\'Fraunces\',serif; font-size:23px; font-weight:600;">HTE Portal</span>',
        unsafe_allow_html=True
    )
    st.caption("AI-Powered Decision Support")

    st.write(f"👤 Logged in as: **{st.session_state.username}**")

    st.selectbox(
        "🌐 Interface Language",

        ["Auto-detect (recommended)", "English", "मराठी (Marathi)", "हिंदी (Hindi)"],
        help="The system auto-detects your question's language and replies in the same language"
    )

    st.write("")
    if st.button("➕ New Conversation", type="primary", use_container_width=True):
        st.session_state.messages = []
        save_history(st.session_state.username, [])
        st.rerun()

    if st.button("🚪 Log Out", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.messages = []
        st.rerun()

    st.divider()
    user_questions = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
    if user_questions:
        st.markdown(
            f'<div class="hist-header"><span class="label">Conversation History</span>'
            f'<span class="count">{len(user_questions)}</span></div>',
            unsafe_allow_html=True,
        )
        rows = ""
        for q in reversed(user_questions[-8:]):
            short_title = q[:34] + "…" if len(q) > 34 else q
            rows += f'<div class="hist-item"><span class="tick">›</span><span>{short_title}</span></div>'
        st.markdown(rows, unsafe_allow_html=True)

# ----------------------------
# MAIN TABS
# ----------------------------
tab_chat, tab_summarize, tab_compare, tab_browse = st.tabs([
    "💬 AI Assistant", "📄 Summarize Document", "⚖️ Compare Documents", "📚 Browse Documents"
])

# ==========================================
# TAB 1: AI CHAT ASSISTANT
# ==========================================
with tab_chat:
    st.markdown('<div class="section-title">HTE Department Assistant</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">Ask questions and get verified answers based on official GRs, '
        'circulars, and notifications — in English, Hindi, or Marathi.</div>',
        unsafe_allow_html=True
    )

    def render_answer_extras(message, idx, is_new=False):
        conf = message.get("confidence", 0)
        time_note = f"Answered in {message['response_time']:.1f}s" if message.get("response_time") else None
        render_seal(conf, sublabel=time_note)

        if message.get("conflict_detected"):
            st.error(f"⚠️ Conflicting information found across sources:\n\n{message.get('conflict_explanation', '')}")

        if message.get("supersession_flags"):
            st.warning("⚠️ This may supersede or amend another document:\n\n" +
                       "\n\n".join([f"...{s}..." for s in message["supersession_flags"]]))

        if message.get("per_source_scores") or message.get("related_documents"):
            with st.expander("📚 Sources & Related Documents"):
                if message.get("per_source_scores"):
                    st.markdown("**Cited Sources**")
                    for item in message["per_source_scores"]:
                        col1, col2 = st.columns([4, 1])
                        col1.markdown(
                            f'<div style="margin-bottom:4px;">{item.get("title", item["source"])} '
                            f'<span class="cite-chip">{item["relevance_score"]}% match</span></div>',
                            unsafe_allow_html=True,
                        )
                        pdf_path = find_source_pdf(item["source"])
                        if pdf_path:
                            with open(pdf_path, "rb") as f:
                                col2.download_button(
                                    "⬇️ PDF", f,
                                    file_name=item["source"].replace(".txt", ".pdf"),
                                    key=f"dl_{idx}_{item['source']}_{is_new}"
                                )

                if message.get("related_documents"):
                    st.divider()
                    st.markdown("**You might also want to see (Related):**")
                    for rel in message["related_documents"]:
                        st.write(f"🔗 {rel}")

        if message.get("sources"):
            col1, col2 = st.columns([1, 5])
            with col1:
                explain_clicked = st.button("🔎 Explain Simply", key=f"explain_{idx}_{is_new}")

            if explain_clicked:
                with st.spinner("Simplifying..."):
                    simple_text = explain_simply(message["content"])
                    st.session_state[f"simple_text_{idx}_{is_new}"] = simple_text

            if f"simple_text_{idx}_{is_new}" in st.session_state:
                st.info(st.session_state[f"simple_text_{idx}_{is_new}"])

            st.write("**Was this answer helpful?**")
            feedback_score = st.feedback("thumbs", key=f"feedback_{idx}_{is_new}")
            if feedback_score is not None:
                feedback_type = "up" if feedback_score == 1 else "down"
                save_feedback(st.session_state.username, message.get("question", ""), message["content"], feedback_type)

    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                render_answer_extras(message, idx)

    user_question = st.chat_input("Ask a question about HTE administrative procedures...")

    if user_question:
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            try:
                with st.status("🔍 Querying Vector Database...", expanded=True) as status:
                    st.write("Extracting semantics from query...")
                    st.write("Cross-referencing authenticated Government Documents...")
                    start_time = time.time()
                    result = generate_answer(user_question)
                    elapsed = time.time() - start_time
                    status.update(label="Information retrieved successfully!", state="complete", expanded=False)

                st.markdown(result["answer"])

                assistant_message = {
                    "role": "assistant",
                    "content": result["answer"],
                    "question": user_question,
                    "confidence": result["confidence"],
                    "per_source_scores": result["per_source_scores"],
                    "related_documents": result["related_documents"],
                    "supersession_flags": result["supersession_flags"],
                    "conflict_detected": result["conflict_detected"],
                    "conflict_explanation": result["conflict_explanation"],
                    "sources": result["sources"],
                    "response_time": elapsed,
                }
                render_answer_extras(assistant_message, len(st.session_state.messages), is_new=True)

                st.session_state.messages.append(assistant_message)
                save_history(st.session_state.username, st.session_state.messages)

            except Exception as e:
                st.error(f"⚠️ Unable to generate response: {str(e)}")
                st.info("The system notifies you when sufficient information is unavailable rather than generating unsupported answers.")

# ==========================================
# TAB 2: SUMMARIZE DOCUMENT
# ==========================================
with tab_summarize:
    st.markdown('<div class="section-title">Summarize a Document</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Get a plain-language summary of any Government Resolution, circular or order in the repository.</div>', unsafe_allow_html=True)

    all_docs = get_all_document_names()

    if not all_docs:
        st.warning("No documents found. Make sure the vector store has been built.")
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            doc_to_summarize = st.selectbox("Select document from repository:", all_docs)
        with col2:
            st.write("")
            st.write("")
            generate_sum = st.button("Generate Summary", use_container_width=True)

        if generate_sum:
            with st.spinner("Analyzing document and extracting key points..."):
                result = summarize_document(doc_to_summarize)
                st.success("Summary Generated!")
                st.markdown(f"### Summary of {doc_to_summarize}")
                st.write(result["summary"])

# ==========================================
# TAB 3: COMPARE DOCUMENTS
# ==========================================
with tab_compare:
    st.markdown('<div class="section-title">Compare Documents</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Set two Government documents side by side to surface differences, amendments, or superseded rules.</div>', unsafe_allow_html=True)

    all_docs_compare = get_all_document_names()

    if len(all_docs_compare) < 2:
        st.warning("Need at least 2 documents in the system to compare.")
    else:
        comp_col1, comp_col2 = st.columns(2)
        with comp_col1:
            doc1 = st.selectbox("Document 1", all_docs_compare, key="compare_doc1")
        with comp_col2:
            doc2 = st.selectbox("Document 2", all_docs_compare, index=1, key="compare_doc2")

        if st.button("Compare Side-by-Side", type="primary"):
            if doc1 == doc2:
                st.error("Please select two different documents.")
            else:
                with st.spinner("Comparing documents and extracting differences..."):
                    result = compare_documents(doc1, doc2)
                    st.markdown("### Comparison Results")
                    st.markdown(result["comparison"])

# ==========================================
# TAB 4: BROWSE DOCUMENTS
# ==========================================
with tab_browse:
    st.markdown('<div class="section-title">Browse the Repository</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Every authenticated document in the system, with its metadata, in one register.</div>', unsafe_allow_html=True)

    browse_list = get_documents_browse_list()

    if not browse_list:
        st.warning("No document metadata found. Run ingestion/extract_metadata.py first.")
    else:
        df = pd.DataFrame(browse_list)

        categories = ["All"] + sorted(df["Category"].unique().tolist())
        selected_category = st.selectbox("Filter by category:", categories)

        if selected_category != "All":
            df = df[df["Category"] == selected_category]

        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Showing {len(df)} of {len(browse_list)} documents")
