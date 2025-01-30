import streamlit as st
import google.generativeai as genai
from io import BytesIO
import json
import matplotlib.pyplot as plt
import re
from fpdf import FPDF
from supabase import create_client, Client

# --- Supabase Configuration ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Google AI Configuration ---
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# --- Streamlit Page Setup ---
st.set_page_config(page_title="Escalytics", page_icon="📧", layout="wide")
st.title("⚡ Escalytics by EverTech")
st.write("Extract insights, root causes, and actionable steps from emails.")

# --- Authentication ---
st.sidebar.header("User Authentication")
auth_status = st.sidebar.session_state.get("auth_status", None)

if auth_status != "authenticated":
    auth_choice = st.sidebar.radio("Login or Signup", ["Login", "Signup"])
    
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")
    
    if auth_choice == "Signup":
        if st.sidebar.button("Signup"):
            res = supabase.auth.sign_up({"email": email, "password": password})
            if "error" not in res:
                st.sidebar.success("Signup successful! Please login.")
            else:
                st.sidebar.error("Signup failed: " + str(res["error"]))
    
    if auth_choice == "Login":
        if st.sidebar.button("Login"):
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            if "error" not in res:
                st.sidebar.session_state["auth_status"] = "authenticated"
                st.sidebar.session_state["user"] = email
                st.rerun()
            else:
                st.sidebar.error("Login failed: " + str(res["error"]))
    
    st.stop()

if st.sidebar.button("Logout"):
    supabase.auth.sign_out()
    st.sidebar.session_state["auth_status"] = None
    st.rerun()

st.sidebar.success(f"Logged in as {st.sidebar.session_state.get('user', 'Unknown')}")

# --- Sidebar for Features ---
st.sidebar.header("Settings")
features = {
    "sentiment": st.sidebar.checkbox("Perform Sentiment Analysis"),
    "highlights": st.sidebar.checkbox("Highlight Key Phrases"),
    "response": st.sidebar.checkbox("Generate Suggested Response"),
    "wordcloud": st.sidebar.checkbox("Generate Word Cloud"),
    "grammar_check": st.sidebar.checkbox("Grammar Check"),
    "key_phrases": st.sidebar.checkbox("Extract Key Phrases"),
    "actionable_items": st.sidebar.checkbox("Extract Actionable Items"),
    "root_cause": st.sidebar.checkbox("Root Cause Detection"),
    "risk_assessment": st.sidebar.checkbox("Risk Assessment"),
    "export": st.sidebar.checkbox("Export Options"),
}

# --- Email Content Input ---
email_content = st.text_area("Paste your email content here:", height=200)
MAX_EMAIL_LENGTH = 1000

# --- AI Response Function ---
@st.cache_data(ttl=3600)
def get_ai_response(prompt, email_content):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt + email_content[:MAX_EMAIL_LENGTH])
        return response.text.strip()
    except Exception as e:
        return f"Error: {e}"

# --- Sentiment Analysis ---
def get_sentiment(email_content):
    positive_words = ["happy", "good", "great", "excellent", "love"]
    negative_words = ["sad", "bad", "hate", "angry", "disappointed"]
    score = sum([1 for w in email_content.split() if w.lower() in positive_words]) - \
            sum([1 for w in email_content.split() if w.lower() in negative_words])
    return "Positive" if score > 0 else "Negative" if score < 0 else "Neutral"

# --- Grammar Check ---
def grammar_check(text):
    corrections = {"recieve": "receive", "adress": "address", "teh": "the", "occured": "occurred"}
    for wrong, right in corrections.items():
        text = text.replace(wrong, right)
    return text

# --- Key Phrases Extraction ---
def extract_key_phrases(text):
    return list(set(re.findall(r"\b[A-Za-z]{4,}\b", text)))  # Removes duplicates

# --- Word Cloud Generation ---
def generate_wordcloud(text):
    words = text.lower().split()
    word_counts = {word: words.count(word) for word in set(words)}
    return word_counts

# --- Export to PDF ---
def export_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text)
    return pdf.output(dest='S').encode('latin1')

# --- Display Results ---
if email_content and st.button("Generate Insights"):
    summary = get_ai_response("Summarize:\n", email_content)
    response = get_ai_response("Generate a response:\n", email_content) if features["response"] else ""
    sentiment = get_sentiment(email_content)
    corrected_text = grammar_check(email_content) if features["grammar_check"] else ""
    key_phrases = extract_key_phrases(email_content) if features["key_phrases"] else []
    word_counts = generate_wordcloud(email_content) if features["wordcloud"] else {}

    st.subheader("AI Summary")
    st.write(summary)

    if features["response"]:
        st.subheader("Suggested Response")
        st.write(response)

    if features["sentiment"]:
        st.subheader("Sentiment Analysis")
        st.write(f"Sentiment: {sentiment}")

    if features["grammar_check"]:
        st.subheader("Grammar Check")
        st.write(corrected_text)

    if features["key_phrases"]:
        st.subheader("Key Phrases Extracted")
        st.write(key_phrases)

    if features["wordcloud"]:
        st.subheader("Word Cloud")
        plt.figure(figsize=(10, 5))
        plt.bar(word_counts.keys(), word_counts.values())
        plt.xticks(rotation=45)
        plt.tight_layout()
        st.pyplot(plt)

    if features["export"]:
        pdf_data = BytesIO(export_pdf(summary))
        txt_data = BytesIO(summary.encode("utf-8"))
        st.download_button("Download as PDF", pdf_data, "analysis.pdf", "application/pdf")
        st.download_button("Download as Text", txt_data, "analysis.txt", "text/plain")
