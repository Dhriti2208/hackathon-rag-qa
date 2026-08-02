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

if "theme" not in st.session_state:
    st.session_state.theme = "Light"


def get_theme_css(theme):
    if theme == "Dark":
        bg, card_bg, text, accent, sidebar_bg = "#0f1729", "#1a2332", "#e8edf5", "#4a7fd4", "#0a1120"
        bg_end = "#131c30"
    else:
        bg, card_bg, text, accent, sidebar_bg = "#ffffff", "#f7f9fc", "#1a1a1a", "#1a3a6e", "#eef2f8"
        bg_end = "#eef2f8"

    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{
        background: linear-gradient(180deg, {bg} 0%, {bg_end} 100%);
        color: {text};
    }}
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg}; border-right: 2px solid {accent}; }}
    [data-testid="stSidebar"] * {{ color: {text} !important; }}

    /* Gradient header banner */
    .hte-header {{
        background: linear-gradient(135deg, {accent} 0%, #2c5aa0 60%, #3a6bc4 100%);
        padding: 32px 36px; border-radius: 16px; margin-bottom: 28px; color: white;
        box-shadow: 0 8px 24px rgba(26,58,110,0.25);
    }}
    .hte-header h1 {{ color: white !important; margin: 0; font-size: 32px; font-weight: 800; }}
    .hte-header p {{ color: #dce6f5 !important; margin-top: 8px; font-size: 15px; }}

    /* Login/register card - centered, elevated */
    .login-card {{
        background-color: {card_bg}; border-radius: 16px; padding: 8px 8px 24px 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid rgba(128,128,128,0.12);
    }}

    /* Styled text inputs */
    .stTextInput input {{
        border-radius: 10px !important;
        border: 1.5px solid rgba(128,128,128,0.25) !important;
        padding: 12px 14px !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }}
    .stTextInput input:focus {{
        border-color: {accent} !important;
        box-shadow: 0 0 0 3px {accent}2a !important;
    }}

    /* Pill-style tabs for login/register and main nav */
    .stTabs [data-baseweb="tab-list"] {{ gap: 10px; }}
    .stTabs [data-baseweb="tab"] {{
        height: 44px; white-space: pre-wrap; border-radius: 22px !important;
        padding: 0px 22px !important; font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {accent} !important; color: white !important;
        box-shadow: 0 3px 10px {accent}55;
    }}

    /* Buttons - smooth hover lift */
    .stButton button {{
        border-radius: 10px; font-weight: 600; transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}
    .stButton button:hover {{
        transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}

    /* Chat message cards */
    [data-testid="stChatMessage"] {{
        background-color: {card_bg}; border-radius: 14px; padding: 10px 6px;
        margin-bottom: 10px; border: 1px solid rgba(128,128,128,0.15);
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }}

    /* Expanders */
    div[data-testid="stExpander"] {{
        border-radius: 12px; border: 1px solid rgba(128,128,128,0.2);
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }}

    /* Dataframe / Browse Documents table */
    .stDataFrame thead tr th {{
        background-color: {accent} !important; color: white !important; font-weight: 700 !important;
    }}
    .stDataFrame {{ border-radius: 12px; overflow: hidden; }}

    /* Progress bar (confidence score) */
    .stProgress > div > div {{ background-color: {accent} !important; border-radius: 8px; }}
    </style>
    """


st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)

# ----------------------------
# LOGIN / REGISTER SCREEN
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = None

if not st.session_state.logged_in:
    st.markdown(
        '<div class="hte-header"><h1>🏛️ HTE Portal</h1>'
        '<p>AI-Powered Decision Support — Please log in or create an account to continue</p></div>',
        unsafe_allow_html=True
    )

    login_col1, login_col2, login_col3 = st.columns([1, 1.4, 1])
    with login_col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        login_tab, register_tab = st.tabs(["Log In", "Register"])

        with login_tab:
            login_username = st.text_input("Username", key="login_username")
            login_password = st.text_input("Password", type="password", key="login_password")
            if st.button("Log In", use_container_width=True):
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
            reg_username = st.text_input("Choose a username", key="reg_username")
            reg_password = st.text_input("Choose a password", type="password", key="reg_password")
            if st.button("Register", use_container_width=True):
                if reg_username and reg_password:
                    success, message = register_user(reg_username, reg_password)
                    if success:
                        st.success(message + " Please log in now.")
                    else:
                        st.error(message)
                else:
                    st.error("Please enter both a username and password.")
        st.markdown('</div>', unsafe_allow_html=True)

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
    st.title("🏛️ HTE Portal")
    st.caption("AI-Powered Decision Support")

    st.write(f"👤 Logged in as: **{st.session_state.username}**")

    theme_choice = st.selectbox("🎨 Theme", ["Light", "Dark"], index=0 if st.session_state.theme == "Light" else 1)
    if theme_choice != st.session_state.theme:
        st.session_state.theme = theme_choice
        st.rerun()

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
    st.markdown(
        '<div class="hte-header"><h1>HTE Department Assistant</h1>'
        '<p>Ask questions and get verified answers based on official GRs, circulars, and notifications — '
        'in English, Hindi, or Marathi.</p></div>',
        unsafe_allow_html=True
    )

    def render_answer_extras(message, idx, is_new=False):
        conf = message.get("confidence", 0)
        st.progress(conf / 100.0, text=f"Overall Confidence: {conf}%")

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
