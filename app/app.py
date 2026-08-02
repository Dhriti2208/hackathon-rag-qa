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

st.set_page_config(page_title="HTE Portal", page_icon="🎓", layout="wide")

# ----------------------------
# THEME (single, polished, ScholarStack-inspired: white + orange accent + navy sidebar)
# ----------------------------
ACCENT = "#FF6B4A"
ACCENT_DARK = "#E85A3A"
SIDEBAR_BG = "#14151F"
SIDEBAR_TEXT = "#E8E9ED"
PANEL_SOFT = "#F1EEFB"
BORDER = "#E2E5EA"
TEXT_DARK = "#1A1A2E"
TEXT_MUTED = "#6B7280"

APP_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

.stApp {{ background-color: #ffffff; color: {TEXT_DARK}; }}

/* Sidebar - dark navy like ScholarStack's dashboard nav */
[data-testid="stSidebar"] {{ background-color: {SIDEBAR_BG}; }}
[data-testid="stSidebar"] * {{ color: {SIDEBAR_TEXT} !important; }}

/* Fix: selectbox/dropdown inside sidebar needs its own background so text isn't invisible */
[data-testid="stSidebar"] [data-baseweb="select"] > div {{
    background-color: #1F2130 !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    color: {SIDEBAR_TEXT} !important;
}}
[data-testid="stSidebar"] [data-baseweb="select"] span {{ color: {SIDEBAR_TEXT} !important; }}
[data-testid="stSidebar"] svg {{ fill: {SIDEBAR_TEXT} !important; }}
[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.12); }}

/* Simple top brand bar (replaces heavy gradient banner) */
.brand-bar {{
    display: flex; align-items: center; gap: 10px;
    padding: 14px 4px 18px 4px; border-bottom: 1px solid {BORDER}; margin-bottom: 24px;
}}
.brand-bar .logo {{ font-size: 26px; }}
.brand-bar .name {{ font-size: 22px; font-weight: 800; color: {TEXT_DARK}; }}
.brand-bar .tagline {{ font-size: 13px; color: {TEXT_MUTED}; margin-left: 8px; }}

/* Section headers */
.section-title {{ font-size: 26px; font-weight: 800; color: {TEXT_DARK}; margin-bottom: 4px; }}
.section-sub {{ font-size: 14px; color: {TEXT_MUTED}; margin-bottom: 20px; }}

/* Text inputs - clean thin border like ScholarStack forms */
.stTextInput input {{
    border-radius: 8px !important;
    border: 1.5px solid {BORDER} !important;
    padding: 12px 14px !important;
    background-color: #ffffff !important;
    color: {TEXT_DARK} !important;
    transition: border-color 0.15s ease;
}}
.stTextInput input:focus {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 3px {ACCENT}22 !important;
}}
.stTextInput label {{ color: {TEXT_DARK} !important; font-weight: 500; font-size: 13px; }}

/* Tabs - clean underline style, not boxy */
.stTabs [data-baseweb="tab-list"] {{ gap: 28px; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{
    height: 42px; background-color: transparent !important; border-radius: 0 !important;
    padding: 0px 2px !important; font-weight: 600; color: {TEXT_MUTED} !important;
}}
.stTabs [aria-selected="true"] {{
    color: {ACCENT} !important; border-bottom: 2.5px solid {ACCENT} !important;
    background-color: transparent !important;
}}

/* Primary buttons - solid orange, ScholarStack style */
.stButton button {{
    border-radius: 8px; font-weight: 600; border: none;
    background-color: {ACCENT}; color: white;
    transition: background-color 0.15s ease;
}}
.stButton button:hover {{ background-color: {ACCENT_DARK}; color: white; }}
.stButton button:focus {{ color: white !important; }}
[data-testid="stSidebar"] .stButton button {{
    background-color: transparent; border: 1px solid rgba(255,255,255,0.2); color: {SIDEBAR_TEXT} !important;
}}
[data-testid="stSidebar"] .stButton button:hover {{ border-color: {ACCENT}; background-color: rgba(255,107,74,0.1); }}

/* Chat message cards - soft, minimal */
[data-testid="stChatMessage"] {{
    background-color: #FAFAFB; border-radius: 12px; padding: 10px 6px;
    margin-bottom: 10px; border: 1px solid {BORDER};
}}

/* Expanders */
div[data-testid="stExpander"] {{ border-radius: 10px; border: 1px solid {BORDER}; }}

/* Dataframe / Browse Documents table */
.stDataFrame thead tr th {{ background-color: {TEXT_DARK} !important; color: white !important; font-weight: 700 !important; }}
.stDataFrame {{ border-radius: 10px; overflow: hidden; border: 1px solid {BORDER}; }}

/* Progress bar (confidence score) - orange fill */
.stProgress > div > div {{ background-color: {ACCENT} !important; border-radius: 6px; }}

/* Login split panel */
.auth-illustration {{
    background-color: {PANEL_SOFT}; border-radius: 16px; height: 480px;
    display: flex; align-items: center; justify-content: center; flex-direction: column;
}}
.auth-illustration svg {{ margin-bottom: 20px; }}
.auth-illustration .caption {{ color: {TEXT_MUTED}; font-size: 15px; text-align: center; padding: 0 30px; }}
</style>
"""
st.markdown(APP_CSS, unsafe_allow_html=True)

# ----------------------------
# LOGIN / REGISTER SCREEN
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if not st.session_state.logged_in:
    st.markdown(
        '<div class="brand-bar"><span class="logo">🎓</span>'
        '<span class="name">HTE Portal</span>'
        '<span class="tagline">AI-Powered Decision Support</span></div>',
        unsafe_allow_html=True
    )

    illustration_col, form_col = st.columns([1, 1.1], gap="large")

    with illustration_col:
        svg_illustration = """
        <svg width="220" height="220" viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg">
            <circle cx="30" cy="40" r="10" fill="#FF6B4A" opacity="0.15"/>
            <circle cx="195" cy="60" r="14" fill="#8B7FE8" opacity="0.2"/>
            <circle cx="190" cy="180" r="8" fill="#FF6B4A" opacity="0.25"/>
            <circle cx="20" cy="180" r="6" fill="#8B7FE8" opacity="0.3"/>
            <rect x="55" y="30" width="110" height="140" rx="12" fill="#FFFFFF" stroke="#E2E5EA" stroke-width="2"/>
            <rect x="72" y="55" width="76" height="8" rx="4" fill="#14151F" opacity="0.85"/>
            <rect x="72" y="75" width="60" height="6" rx="3" fill="#6B7280" opacity="0.5"/>
            <rect x="72" y="90" width="66" height="6" rx="3" fill="#6B7280" opacity="0.5"/>
            <rect x="72" y="105" width="50" height="6" rx="3" fill="#6B7280" opacity="0.5"/>
            <rect x="72" y="128" width="76" height="6" rx="3" fill="#6B7280" opacity="0.3"/>
            <rect x="72" y="142" width="55" height="6" rx="3" fill="#6B7280" opacity="0.3"/>
            <circle cx="155" cy="145" r="28" fill="#FF6B4A"/>
            <path d="M142 145 L151 154 L169 134" stroke="white" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
            <rect x="40" y="185" width="140" height="8" rx="2" fill="#14151F" opacity="0.15"/>
        </svg>
        """
        st.markdown(
            f'<div class="auth-illustration">{svg_illustration}'
            '<div class="caption">Ask questions in English, Hindi, or Marathi and get '
            'source-grounded answers from official HTE department documents.</div>'
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
    st.markdown('<span style="font-size:22px; font-weight:800;">🎓 HTE Portal</span>', unsafe_allow_html=True)
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
        st.caption(f"🗨️ {len(user_questions)} question(s) in this conversation")
        for q in reversed(user_questions[-8:]):
            short_title = q[:30] + "..." if len(q) > 30 else q
            st.caption(f"💬 {short_title}")

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
        st.caption(f"Overall Confidence: **{conf}%**")
        st.progress(conf / 100.0)

        if message.get("response_time"):
            st.caption(f"⏱️ Answered in {message['response_time']:.1f}s")

        if message.get("conflict_detected"):
            st.error(f"⚠️ Conflicting information found across sources:\n\n{message.get('conflict_explanation', '')}")

        if message.get("supersession_flags"):
            st.warning("⚠️ This may supersede or amend another document:\n\n" +
                       "\n\n".join([f"...{s}..." for s in message["supersession_flags"]]))

        if message.get("per_source_scores") or message.get("related_documents"):
            with st.expander("📚 Sources & Related Documents"):
                if message.get("per_source_scores"):
                    st.markdown("**Cited Sources (with relevance score):**")
                    for item in message["per_source_scores"]:
                        col1, col2 = st.columns([4, 1])
                        col1.write(f"- **{item.get('title', item['source'])}** — {item['relevance_score']}% relevant")
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
    st.header("📄 Summarize Government Document")
    st.write("Get an easy-to-understand summary of any document in the system.")

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
    st.header("⚖️ Compare Documents")
    st.write("Compare two Government documents and highlight important differences, amendments, or superseded rules.")

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
    st.header("📚 Browse All Documents")
    st.write("See every document in the system with its metadata.")

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
