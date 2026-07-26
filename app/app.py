"""
STEP 5: The Streamlit chat interface — what the user actually sees and uses.

Run with: streamlit run app/app.py
(run this command from the main project folder, not from inside app/)
"""

import streamlit as st
import sys
import os

# lets this file find the rag_engine folder one level up
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from rag_engine.rag_pipeline import generate_answer

st.set_page_config(page_title="HTE Q&A Assistant", page_icon="🎓")

st.title("🎓 HTE Department Q&A Assistant")
st.caption("Ask questions about HTE department documents, circulars, and GRs")

if "messages" not in st.session_state:
    st.session_state.messages = []

# show past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("📄 Sources"):
                for src in message["sources"]:
                    st.write(f"- {src}")

user_question = st.chat_input("Ask your question...")

if user_question:
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = generate_answer(user_question)
            st.markdown(result["answer"])
            if result["sources"]:
                with st.expander("📄 Sources"):
                    for src in result["sources"]:
                        st.write(f"- {src}")

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["answer"],
        "sources": result["sources"]
    })
