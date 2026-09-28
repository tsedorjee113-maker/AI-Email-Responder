import os
import json
import base64
import streamlit as st
from dotenv import load_dotenv
from google import genai
from streamlit_oauth import OAuth2Component
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText

# Load local .env variables if present
load_dotenv()

# Helper function to read secrets from Streamlit Cloud or local .env
def get_secret(key_name):
    if key_name in st.secrets:
        return st.secrets[key_name]
    return os.getenv(key_name)

# Retrieve Environment Credentials
default_api_key = get_secret("GEMINI_API_KEY")
CLIENT_ID = get_secret("GOOGLE_CLIENT_ID")
CLIENT_SECRET = get_secret("GOOGLE_CLIENT_SECRET")

# Google OAuth Endpoints
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# OAuth Scopes for OpenID + Gmail Read & Send
OAUTH_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

st.set_page_config(page_title="AI Email Assistant", page_icon="✉️", layout="wide")

# ---------------------------------------------------------
# Sidebar / Configuration & Authentication
# ---------------------------------------------------------
st.sidebar.header("🔑 Configuration")

# Secure API Key input (falls back to default secret)
user_input_key = st.sidebar.text_input(
    "Gemini API Key", 
    value="", 
    type="password",
    placeholder="Loaded from Secrets (or enter custom key)"
)
user_api_key = user_input_key.strip() if user_input_key.strip() else default_api_key

st.sidebar.markdown("---")
st.sidebar.header("👤 Authentication")

if CLIENT_ID and CLIENT_SECRET:
    oauth2 = OAuth2Component(
        CLIENT_ID, 
        CLIENT_SECRET, 
        AUTHORIZE_ENDPOINT, 
        TOKEN_ENDPOINT, 
        TOKEN_ENDPOINT
    )

    if "user_email" not in st.session_state:
        st.sidebar.info("Log in with Google to unlock Direct Gmail Inbox Sync & Auto-Send.")
        
        redirect_uri = os.getenv("REDIRECT_URI", "https://email-responder-ai.streamlit.app/")
        
        try:
            result = oauth2.authorize_button(
                name="Continue with Google",
                redirect_uri=redirect_uri,
                scope=" ".join(OAUTH_SCOPES),
                key="google_oauth"
            )

            if result:
                # Save tokens to session state
                st.session_state["token"] = result["token"]
                
                # Extract and decode ID Token
                id_token = result["token"]["id_token"]
                payload = id_token.split(".")[1]
                payload += "=" * (-len(payload) % 4)
                user_info = json.loads(base64.b64decode(payload))
                
                st.session_state["user_email"] = user_info.get("email", "")
                st.rerun()

        except Exception as e:
            st.sidebar.warning("Session expired or state mismatched. Please click below to sign in again.")
            if st.sidebar.button("Retry Google Sign-In"):
                st.query_params.clear()
                st.rerun()

    else:
        st.sidebar.success(f"Logged in as:\n**{st.session_state['user_email']}**")
        if st.sidebar.button("Log Out"):
            for key in ["user_email", "token", "unread_emails"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.query_params.clear()
            st.rerun()
else:
    st.sidebar.warning("Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Secrets/.env for OAuth.")

# ---------------------------------------------------------
# Gmail & Gemini Helper Functions
# ---------------------------------------------------------
def call_gemini(prompt_text, key):
    client = genai.Client(api_key=key.strip())
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt_text,
    )
    return response.text

def get_gmail_service():
    """Builds the Gmail API service using OAuth tokens from session state."""
    if "token" not in st.session_state:
        return None
    token_data = st.session_state["token"]
    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=TOKEN_ENDPOINT,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    return build("gmail", "v1", credentials=creds)

def fetch_gmail_emails(max_results=10, folder_query='is:unread'):
    """Fetches emails from Gmail based on query filters and count limit."""
    service = get_gmail_service()
    if not service:
        return []
    
    results = service.users().messages().list(userId='me', q=folder_query, maxResults=max_results).execute()
    messages = results.get('messages', [])
    
    email_list = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_detail.get('payload', {}).get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        snippet = msg_detail.get('snippet', '')
        
        email_list.append({
            'id': msg['id'],
            'from': sender,
            'subject': subject,
            'snippet': snippet
        })
    return email_list

def send_gmail_message(to_address, subject, body_text):
    """Sends an email directly through the Gmail API."""
    service = get_gmail_service()
    if not service:
        return False
    
    message = MIMEText(body_text)
    message['to'] = to_address
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
    return True

# ---------------------------------------------------------
# Main App Layout
# ---------------------------------------------------------
is_logged_in = "user_email" in st.session_state

if not is_logged_in:
    # =========================================================
    # FEATURE SET A: Quick Email Writer (Guest Mode)
    # =========================================================
    st.title("✉️ Quick AI Email Writer")
    st.caption("Generate emails instantly. Log in via Google to fetch live inbox emails and send responses directly.")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Your Goal")
        recipient_name = st.text_input("Recipient Name / Email", placeholder="e.g., Alex / alex@example.com")
        intent_instruction = st.text_area(
            "What should the email say?", 
            placeholder="e.g., Schedule my meeting with Alex this Friday at 3 PM to discuss the project timeline.",
            height=150
        )
        tone = st.selectbox("Tone", ["Professional", "Friendly", "Concise", "Formal", "Persuasive"])
        
    with col2:
        st.subheader("📄 Generated Email Output")
        if st.button("Generate Email Draft", use_container_width=True, type="primary"):
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
                        st.code(draft, language="text")
                    except Exception as e:
                        st.error(f"Gemini API Error: {e}")

else:
    # =========================================================
    # FEATURE SET B: Live Gmail Sync & AI Smart Reply (Logged-In Mode)
    # =========================================================
    st.title("📥 AI Email Inbox & Direct Send Assistant")
    st.caption(f"Connected Account: **{st.session_state['user_email']}**")
    
    # ---------------------------------------------------------
    # Inbox View & Custom Fetch Controls
    # ---------------------------------------------------------
    st.markdown("### 📬 Gmail Inbox Explorer")
    
    col_folder, col_count, col_btn = st.columns([2, 1, 1])
    
    with col_folder:
        inbox_filter = st.selectbox(
            "Select Mail View / Category:",
            ["Unread Emails (`is:unread`)", "Important Emails (`is:important`)", "Starred Emails (`is:starred`)", "All Recent Emails (`in:inbox`)"]
        )
        
        query_map = {
            "Unread Emails (`is:unread`)": "is:unread",
            "Important Emails (`is:important`)": "is:important",
            "Starred Emails (`is:starred`)": "is:starred",
            "All Recent Emails (`in:inbox`)": "in:inbox"
        }
        selected_query = query_map[inbox_filter]

    with col_count:
        fetch_limit = st.selectbox("Max Emails to Fetch:", [5, 10, 15, 20], index=1)

    with col_btn:
        st.write("") # Spacer for vertical alignment
        st.write("")
        fetch_clicked = st.button("🔄 Sync Emails", use_container_width=True)

    if fetch_clicked:
        with st.spinner("Connecting to Gmail API..."):
            try:
                st.session_state["unread_emails"] = fetch_gmail_emails(max_results=fetch_limit, folder_query=selected_query)
                st.success(f"Fetched {len(st.session_state['unread_emails'])} email(s).")
            except Exception as e:
                st.error(f"Failed to fetch emails: {e}")
                
    # Display fetched emails selector if available
    fetched_emails = st.session_state.get("unread_emails", [])
    selected_sender = ""
    selected_subject = ""
    selected_snippet = ""
    
    if fetched_emails:
        email_options = [f"{e['from']} | {e['subject']}" for e in fetched_emails]
        chosen_idx = st.selectbox("Select an email to inspect & reply:", range(len(email_options)), format_func=lambda x: email_options[x])
        chosen_email = fetched_emails[chosen_idx]
        selected_sender = chosen_email['from']
        selected_subject = chosen_email['subject']
        selected_snippet = chosen_email['snippet']

    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📩 Incoming Email")
        incoming_sender = st.text_input("From (Sender)", value=selected_sender, placeholder="e.g., client@company.com")
        incoming_subject = st.text_input("Subject Line", value=selected_subject, placeholder="e.g., Quick question about project")
        incoming_body = st.text_area("Email Content / Snippet", value=selected_snippet, height=180, placeholder="Email snippet or full content will show here...")
        
        st.markdown("---")
        st.subheader("💡 Quick Presets & Reply Hints")
        
        # Preset Prompt Buttons
        preset_cols = st.columns(3)
        default_hint = ""
        if preset_cols[0].button("👍 Accept / Agree"):
            default_hint = "Politely accept the offer/request and state looking forward to working together."
        if preset_cols[1].button("✋ Decline Politely"):
            default_hint = "Thank them for reaching out, but politely decline due to current schedule constraints."
        if preset_cols[2].button("📅 Ask to Schedule"):
            default_hint = "Propose meeting next week to discuss details in depth."
            
        reply_hint = st.text_input(
            "Custom Reply Instruction", 
            value=default_hint,
            placeholder="e.g., Tell them we can meet this Friday at 2 PM."
        )

    with col2:
        st.subheader("🤖 AI Smart Draft & Direct Send")
        response_tone = st.selectbox("Reply Tone", ["Professional", "Friendly", "Concise", "Formal", "Persuasive"])
        
        if st.button("Analyze & Draft Smart Reply", use_container_width=True, type="primary"):
            if not incoming_body and not reply_hint:
                st.warning("Please provide incoming email details or a reply hint.")
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
                {reply_hint if reply_hint else 'Acknowledge the email politely and offer helpful next steps.'}
                
                [TASK]
                Write a complete, ready-to-send email reply in a {response_tone} tone.
                Format the response with:
                SUBJECT: <Suggested Subject>
                BODY: <Complete Email Body>
                """
                
                with st.spinner("Analyzing email and generating draft..."):
                    try:
                        ai_output = call_gemini(prompt, user_api_key)
                        st.session_state["current_draft"] = ai_output
                    except Exception as e:
                        st.error(f"Gemini API Error: {e}")

        # Display Draft & Direct Send Option
        if "current_draft" in st.session_state:
            draft_text = st.session_state["current_draft"]
            st.text_area("Generated Draft", value=draft_text, height=260)
            
            st.markdown("---")
            send_to_email = st.text_input("Send To Address:", value=incoming_sender)
            
            if st.button("🚀 Send Email directly via Gmail", use_container_width=True):
                if not send_to_email:
                    st.warning("Please specify a recipient email address.")
                else:
                    with st.spinner("Sending email via Gmail API..."):
                        try:
                            subject_line = f"Re: {incoming_subject}" if incoming_subject else "AI Assistant Response"
                            success = send_gmail_message(send_to_email, subject_line, draft_text)
                            if success:
                                st.success(f"✅ Email successfully sent to **{send_to_email}**!")
                            else:
                                st.error("Failed to send email. Check credentials.")
                        except Exception as e:
                            st.error(f"Error sending email via Gmail API: {e}")
