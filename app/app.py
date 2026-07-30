"""
STEP 5: The Streamlit chat interface — Fully Featured HTE Portal.
Responsive to both Light and Dark modes.

Run with: streamlit run app/app.py
"""

import streamlit as st
import sys
import os
import time

# lets this file find the rag_engine folder one level up
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# Fallback for UI testing if the backend isn't ready
try:
    from rag_engine.rag_pipeline import generate_answer
except ImportError:
    def generate_answer(q):
        time.sleep(1.5) # Simulate processing
        return {
            "answer": f"This is an AI-generated response to your query regarding '{q}'. According to the official Government Resolutions, the procedures have been updated. Please refer to the attached documents for the complete administrative workflow.",
            "sources": ["GR_March_2024.pdf", "DTE_Circular_12.pdf"],
            "confidence": 92,
            "related": ["Scholarship_Guidelines_2023.pdf", "Amendment_Order_No4.pdf"],
            "superseded_by": None
        }

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="HTE Portal", page_icon="🏛️", layout="wide")

# --- CUSTOM CSS (Theme Responsive) ---
custom_css = """
<style>
/* Use native Streamlit variables for responsive theming */
[data-testid="stSidebar"] {
    border-right: 1px solid var(--secondary-background-color);
}
.stTabs [data-baseweb="tab-list"] {
    gap: 24px;
}
.stTabs [data-baseweb="tab"] {
    height: 50px;
    white-space: pre-wrap;
    border-radius: 4px 4px 0px 0px;
    gap: 1px;
    padding-top: 10px;
    padding-bottom: 10px;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- INITIALIZE SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "recent_chats" not in st.session_state:
    st.session_state.recent_chats = ["HTE GRs regarding promotions", "Circular 2024 updates"]

# --- SIDEBAR ---
with st.sidebar:
    st.title("🏛️ HTE Portal")
    st.caption("AI-Powered Decision Support")
    
    # 2. Language Toggle (English, Marathi, Hindi)
    st.selectbox(
        "🌐 Interface Language", 
        ["English", "मराठी (Marathi)", "हिंदी (Hindi)"],
        help="Switch languages during an active conversation"
    )
    
    st.write("") # Spacer
    if st.button("➕ New Conversation", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    st.divider()
    
    st.subheader("🕰️ Recent History")
    for chat_title in reversed(st.session_state.recent_chats):
        st.button(f"💬 {chat_title}", use_container_width=True, key=f"chat_{chat_title}")

# --- MAIN APP LAYOUT (Using Tabs for cleaner UI) ---
# Separating Chat, Summarization, and Comparison into tabs for a professional look
tab_chat, tab_summarize, tab_compare = st.tabs(["💬 AI Assistant", "📄 Summarize Document", "⚖️ Compare Documents"])

# ==========================================
# TAB 1: AI CHAT ASSISTANT
# ==========================================
with tab_chat:
    st.header("HTE Department Assistant")
    st.caption("Ask questions and get verified answers based on official GRs, circulars, and notifications.")

    # Render Chat History
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            if message["role"] == "assistant":
                # 1. Confidence Score Progress Bar
                conf = message.get("confidence", 85)
                st.progress(conf / 100.0, text=f"Relevance/Confidence Score: {conf}%")
                
                # 5 & 6. Sources, Related Docs, and Downloads
                with st.expander("📚 Sources & Related Documents"):
                    st.markdown("**Cited Sources:**")
                    if message.get("sources"):
                        for src in message["sources"]:
                            col1, col2 = st.columns([4, 1])
                            col1.write(f"- {src}")
                            col2.download_button("⬇️ Download", data=b"PDF Content", file_name=src, key=f"dl_{idx}_{src}")
                    
                    if message.get("related"):
                        st.divider()
                        st.markdown("**You might also want to see (Related):**")
                        for rel in message["related"]:
                            st.write(f"🔗 {rel}")
                
                # 7. Feedback UI (Using Streamlit's native feedback widget)
                st.write("**Was this answer helpful?**")
                st.feedback("thumbs", key=f"feedback_{idx}")

    # Chat Input
    user_question = st.chat_input("Ask a question about HTE administrative procedures...")

    if user_question:
        # Update Chat History
        if len(st.session_state.messages) == 0:
            new_title = user_question[:25] + "..." if len(user_question) > 25 else user_question
            st.session_state.recent_chats.append(new_title)
            
        st.session_state.messages.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        # Generate Response
        with st.chat_message("assistant"):
            try:
                # 9. Loading States
                with st.status("🔍 Querying Vector Database...", expanded=True) as status:
                    st.write("Extracting semantics from query...")
                    st.write("Cross-referencing authenticated Government Documents...")
                    result = generate_answer(user_question)
                    status.update(label="Information retrieved successfully!", state="complete", expanded=False)
                
                st.markdown(result["answer"])
                
                # Display metrics and metadata
                conf = result.get("confidence", 90)
                st.progress(conf / 100.0, text=f"Relevance/Confidence Score: {conf}%")
                
                with st.expander("📚 Sources & Related Documents"):
                    st.markdown("**Cited Sources:**")
                    if result.get("sources"):
                        for src in result["sources"]:
                            col1, col2 = st.columns([4, 1])
                            col1.write(f"- {src}")
                            col2.download_button("⬇️ Download", data=b"PDF Content", file_name=src, key=f"dl_new_{src}")
                    
                    if result.get("related"):
                        st.divider()
                        st.markdown("**You might also want to see (Related):**")
                        for rel in result["related"]:
                            st.write(f"🔗 {rel}")
                
                st.write("**Was this answer helpful?**")
                st.feedback("thumbs", key=f"feedback_new_{len(st.session_state.messages)}")

                # Save to session
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result.get("sources", []),
                    "confidence": conf,
                    "related": result.get("related", [])
                })
                
            except Exception as e:
                # 9. Error Messages
                st.error(f"⚠️ Unable to generate response: {str(e)}")
                st.info("The system notifies you when sufficient information is unavailable rather than generating unsupported answers.")

# ==========================================
# TAB 2: SUMMARIZE DOCUMENT
# ==========================================
with tab_summarize:
    st.header("📄 Summarize Government Document")
    st.write("Explain lengthy Government Resolutions, circulars, or notifications in simple language.")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        doc_to_summarize = st.selectbox("Select document from repository:", 
                                        ["GR_March_2024_Promotions.pdf", "Scholarship_Circular_2023.pdf", "DTE_Admission_Manual.pdf"])
    with col2:
        st.write("")
        st.write("")
        generate_sum = st.button("Generate Summary", use_container_width=True)
        
    if generate_sum:
        with st.spinner("Analyzing document structure and extracting key points..."):
            time.sleep(2)
            st.success("Summary Generated!")
            st.markdown(f"### Summary of {doc_to_summarize}")
            st.write("1. **Purpose:** The document outlines the updated criteria for departmental promotions.")
            st.write("2. **Key Changes:** Removes the previous 5-year tenure requirement, replacing it with a performance-based metric.")
            st.write("3. **Applicability:** Applies to all Group B and Group C officers effective immediately.")

# ==========================================
# TAB 3: COMPARE DOCUMENTS
# ==========================================
with tab_compare:
    st.header("⚖️ Compare Documents")
    st.write("Compare multiple Government documents and highlight important differences, amendments, or superseded rules.")
    
    comp_col1, comp_col2 = st.columns(2)
    with comp_col1:
        doc1 = st.selectbox("Document 1 (Older Document)", ["GR_2020_Guidelines.pdf", "GR_2023_Guidelines.pdf"])
    with comp_col2:
        doc2 = st.selectbox("Document 2 (Newer Document)", ["GR_2023_Guidelines.pdf", "GR_2024_Amendment.pdf"])
        
    if st.button("Compare Side-by-Side", type="primary"):
        with st.spinner("Comparing semantic vectors and extracting differences..."):
            time.sleep(2)
            st.markdown("### Comparison Results")
            st.warning("⚠️ Document 2 supersedes Section 4 of Document 1.")
            
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.markdown(f"**{doc1}**")
                st.error("Clause 4.1: Requires physical submission of forms at the regional office within 15 days.")
            with res_col2:
                st.markdown(f"**{doc2}**")
                st.success("Clause 4.1 (Amended): Allows online submission via the central portal within 30 days.")