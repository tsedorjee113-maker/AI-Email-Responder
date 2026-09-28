# ✉️ AI Email Writer & Inbox Smart Reply Assistant

An intelligent, dual-mode AI Email Assistant starter kit built with **Python**, **Streamlit**, **Google Gemini API** (`google-genai`), **Google OAuth 2.0**, and the **Gmail API**.

---

## 🌟 Features

* **Guest Mode (Quick Email Writer):** Generate complete, professional emails instantly from simple instructions without logging in (e.g., *"Schedule my meeting with Alex this Friday"*).
* **Logged-In Mode (Google OAuth 2.0):** Authenticate securely with Google to unlock direct Gmail syncing, email context analysis, and 1-click email dispatching.
* **📬 Gmail Inbox Explorer:** Fetch 5, 10, 15, or 20 emails directly from filtered views (`Unread`, `Important`, `Starred`, or `All Recent`).
* **💡 One-Click Smart Presets:** Pre-configured action buttons (*Accept/Agree*, *Decline Politely*, *Ask to Schedule*) to rapidly populate reply instructions.
* **🚀 Direct Gmail Send:** Dispatch generated email drafts directly from your connected Gmail inbox with a single click.
* **Tone Controls:** Choose from multiple response tones (*Professional*, *Friendly*, *Concise*, *Formal*, *Persuasive*).
* **Modern SDK Integration:** Powered by Google's latest `google-genai` SDK (`gemini-2.5-flash`).

---

## 🛠️ Quickstart Guide

### 1. Clone or Extract Files
Extract all files from this bundle into a local project folder:
- `app.py`
- `requirements.txt`
- `.env.example`
- `README.md`

### 2. Set Up Virtual Environment (Recommended)
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
