import streamlit as st
import os
import json
import base64
from dotenv import load_dotenv
from google import genai
from streamlit_oauth import OAuth2Component

load_dotenv()

# Environment Credentials
default_api_key = os.getenv("GEMINI_API_KEY")
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# Google OAuth Endpoints
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
REVOKE_ENDPOINT = "https://oauth2.googleapis.com/revoke"

st.set_page_config(page_title="AI Email Assistant", page_icon="✉️", layout="wide")

# ---------------------------------------------------------
# Sidebar / Authentication
# ---------------------------------------------------------
st.sidebar.header("🔑 Configuration")
user_api_key = st.sidebar.text_input("Gemini API Key", value=default_api_key or "", type="password")

st.sidebar.markdown("---")
st.sidebar.header("👤 Authentication")

if CLIENT_ID and CLIENT_SECRET:
    oauth2 = OAuth2Component(
        CLIENT_ID, 
        CLIENT_SECRET, 
        AUTHORIZE_ENDPOINT, 
        TOKEN_ENDPOINT, 
        TOKEN_ENDPOINT, 
        REVOKE_ENDPOINT
    )

    if "user_email" not in st.session_state:
        st.sidebar.info("Log in to unlock Inbox Smart Replies.")
        
        try:
            result = oauth2.authorize_button(
                name="Continue with Google",
                redirect_uri="http://localhost:8501",
                scope="openid email profile",
                key="google_oauth"
            )

            if result:
                # Extract and decode ID Token
                id_token = result["token"]["id_token"]
                payload = id_token.split(".")[1]
                payload += "=" * (-len(payload) % 4)
                user_info = json.loads(base64.b64decode(payload))
                
                st.session_state["user_email"] = user_info.get("email", "")
                st.rerun()

        except Exception as e:
            # Handle state mismatch gracefully
            st.sidebar.warning("Session expired or state mismatched. Please click below to sign in again.")
            if st.sidebar.button("Retry Google Sign-In"):
                # Clear query parameters to reset the OAuth URL state
                st.query_params.clear()
                st.rerun()

    else:
        st.sidebar.success(f"Logged in as:\n**{st.session_state['user_email']}**")
        if st.sidebar.button("Log Out"):
            del st.session_state["user_email"]
            st.query_params.clear()
            st.rerun()
else:
    st.sidebar.warning("Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env for OAuth.")

# ---------------------------------------------------------
# Helper Function for Gemini
# ---------------------------------------------------------
def call_gemini(prompt_text, key):
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_text,
    )
    return response.text

# ---------------------------------------------------------
# Main App Layout
# ---------------------------------------------------------
is_logged_in = "user_email" in st.session_state

if not is_logged_in:
    # =========================================================
    # FEATURE SET A: Quick Email Writer (Guest Mode)
    # =========================================================
    st.title("✉️ Quick AI Email Writer")
    st.caption("Generate emails instantly from simple prompts. Log in via Google to unlock Inbox Smart Replies.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Your Goal")
        recipient_name = st.text_input("Recipient Name / Email", placeholder="e.g., Biru / biru@example.com")
        intent_instruction = st.text_area(
            "What should the email say?", 
            placeholder="e.g., Schedule my meeting with Biru this Friday at 3 PM to discuss the project timeline.",
            height=150
        )
        tone = st.selectbox("Tone", ["Professional", "Friendly", "Concise", "Formal", "Persuasive"])
        
    with col2:
        st.subheader("📄 Generated Email Output")
        if st.button("Generate Email Draft", use_container_width=True):
            if not intent_instruction:
                st.warning("Please type a short instruction first!")
            elif not user_api_key:
                st.error("Please provide a Gemini API Key in the sidebar.")
            else:
                prompt = f"""
                You are a professional email assistant.
                Write a complete email based on the following details:
                - Recipient: {recipient_name}
                - Instructions: {intent_instruction}
                - Tone: {tone}
                
                Provide a Subject line and the Email Body clearly formatted.
                """
                with st.spinner("Drafting email..."):
                    try:
                        draft = call_gemini(prompt, user_api_key)
                        st.text_area("Ready-to-Send Email", value=draft, height=280)
                    except Exception as e:
                        st.error(f"Gemini API Error: {e}")

else:
    # =========================================================
    # FEATURE SET B: Inbox Analyzer & Smart Reply (Logged-In Mode)
    # =========================================================
    st.title("📥 AI Email Inbox & Smart Reply Assistant")
    st.caption(f"Connected Account: **{st.session_state['user_email']}**")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📩 Incoming Email")
        incoming_sender = st.text_input("From (Sender)", placeholder="e.g., client@company.com")
        incoming_subject = st.text_input("Subject Line", placeholder="e.g., Quick question about delivery date")
        incoming_body = st.text_area("Email Content", height=180, placeholder="Paste the email you received here...")
        
        st.markdown("---")
        st.subheader("💡 Your Quick Reply Hint")
        reply_hint = st.text_input(
            "How do you want to respond?", 
            placeholder="e.g., Say him that we will meet this Friday at 2 PM."
        )
        
    with col2:
        st.subheader("🤖 AI Analysis & Smart Draft")
        response_tone = st.selectbox("Reply Tone", ["Professional", "Friendly", "Concise", "Formal", "Persuasive"])
        
        if st.button("Analyze & Draft Smart Reply", use_container_width=True):
            if not incoming_body:
                st.warning("Please paste the incoming email content first.")
            elif not user_api_key:
                st.error("Please provide a Gemini API Key in the sidebar.")
            else:
                prompt = f"""
                You are an AI Email Assistant acting on behalf of {st.session_state['user_email']}.
                
                [INCOMING EMAIL]
                From: {incoming_sender}
                Subject: {incoming_subject}
                Body:
                {incoming_body}
                
                [USER'S REPLY HINT]
                {reply_hint if reply_hint else 'Acknowledge the email politely and offer next steps.'}
                
                [TASK]
                1. Provide a concise 2-bullet analysis of the key points in the incoming email.
                2. Write a draft reply in a {response_tone} tone that incorporates the user's reply hint accurately.
                """
                
                with st.spinner("Analyzing email and building draft..."):
                    try:
                        ai_output = call_gemini(prompt, user_api_key)
                        st.markdown("### Analysis & Generated Reply:")
                        st.text_area("AI Response Draft", value=ai_output, height=320)
                    except Exception as e:
                        st.error(f"Gemini API Error: {e}")
