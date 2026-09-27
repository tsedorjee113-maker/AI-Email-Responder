import re
import requests
import streamlit as st

# 1. Page Configuration & Title
st.set_page_config(
    page_title="AI Auto-Responder", page_icon="📩", layout="wide"
)
st.title("📩 AI Auto-Responder App")
st.write("Generate clean, professional email replies using the Gemini API.")

# 2. Sidebar Configuration
with st.sidebar:
  st.header("⚙️ Configuration")
  user_key = st.text_input("Enter your Gemini API Key:", type="password")
  system_tone = st.selectbox(
      "Select Response Tone:", ["Professional", "Casual", "Urgent", "Friendly"]
  )

  st.divider()
  st.subheader("👤 Personalization (Optional)")
  sender_name = st.text_input("Your Name (Sender):", value="")
  recipient_name = st.text_input("Recipient's Name:", value="")

# 3. Main Inputs
email_input = st.text_area("Paste incoming email text below:", height=180)


# Helper function to clean remaining placeholders if any slip through
def clean_placeholders(text: str, sender: str, recipient: str) -> str:
  # Clean up recipient placeholders
  recip_default = recipient.strip() if recipient.strip() else "there"
  text = re.sub(
      r"\[Customer Name\]|\[Recipient Name\]|\[Name\]", recip_default, text
  )

  # Clean up sender placeholders
  sender_default = sender.strip() if sender.strip() else ""
  text = re.sub(r"\[Your Name\]|\[My Name\]|\[Sender Name\]", sender_default, text)

  return text


# 4. Action Trigger
if st.button("🚀 Draft AI Reply", type="primary"):
  if not user_key or not email_input:
    st.error("⚠️ Please enter both your Gemini API Key and the email text!")
  else:
    st.info("🤖 AI is analyzing the text...")

    try:
      clean_key = user_key.strip()

      # Build customized instructions
      prompt_instructions = (
          f"Write a {system_tone.lower()} reply to the following email.\n"
      )
      if recipient_name.strip():
        prompt_instructions += f"- Address the recipient as '{recipient_name.strip()}'.\n"
      else:
        prompt_instructions += (
            "- Use a natural greeting like 'Hi there,' without generic"
            " bracketed placeholders.\n"
        )

      if sender_name.strip():
        prompt_instructions += f"- Sign off using the name '{sender_name.strip()}'.\n"
      else:
        prompt_instructions += (
            "- Do not include generic bracketed placeholders like [Your Name]"
            " at the end.\n"
        )

      full_prompt = (
          f"Instructions:\n{prompt_instructions}\n\nEmail Content:\n{email_input}"
      )

      # Correct Gemini 2.5 Flash REST API Endpoint
      api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={clean_key}"
      headers = {"Content-Type": "application/json"}
      payload = {"contents": [{"parts": [{"text": full_prompt}]}]}

      response = requests.post(api_url, json=payload, headers=headers)
      response_data = response.json()

      if response.status_code == 200:
        raw_ai_text = response_data["candidates"][0]["content"]["parts"][0][
            "text"
        ]

        # Post-process text to remove leftover placeholders
        final_ai_text = clean_placeholders(
            raw_ai_text, sender_name, recipient_name
        )

        st.success("✨ Response Drafted Successfully!")

        # Display final output
        st.text_area("AI Generated Draft:", value=final_ai_text, height=250)

        # Quick copy snippet block
        st.code(final_ai_text, language="text")
        st.caption("💡 Click the copy button in the top-right of the box above to quickly copy your draft.")

      else:
        error_msg = response_data.get("error", {}).get(
            "message", "Failed to get response from Gemini API."
        )
        st.error(f"❌ API Request Failed ({response.status_code}): {error_msg}")

    except Exception as e:
      st.error(f"❌ Connection or Parsing error: {e}")
