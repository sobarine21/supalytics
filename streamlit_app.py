import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import json
import matplotlib.pyplot as plt
import re
from io import BytesIO
from fpdf import FPDF

# Supabase Configuration
SUPABASE_URL = "https://your-supabase-url.supabase.co"
SUPABASE_KEY = "your-anon-key"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Streamlit Configuration
st.set_page_config(page_title="Escalytics", page_icon="📧", layout="wide")
st.title("⚡Escalytics by EverTech")
st.write("Extract insights, root causes, and actionable steps from emails.")

# Authentication
st.sidebar.header("User Authentication")

# Login/Signup UI
auth_choice = st.sidebar.radio("Choose an option:", ["Login", "Sign Up"])

if auth_choice == "Sign Up":
    email = st.sidebar.text_input("Email", key="signup_email")
    password = st.sidebar.text_input("Password", type="password", key="signup_password")
    if st.sidebar.button("Sign Up"):
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.get("error"):
            st.sidebar.error(response["error"]["message"])
        else:
            st.sidebar.success("Signup successful! Please log in.")

if auth_choice == "Login":
    email = st.sidebar.text_input("Email", key="login_email")
    password = st.sidebar.text_input("Password", type="password", key="login_password")
    if st.sidebar.button("Login"):
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.get("error"):
            st.sidebar.error(response["error"]["message"])
        else:
            st.sidebar.success("Login successful!")
            user = response["user"]

# Logout button
if "user" in locals():
    if st.sidebar.button("Logout"):
        supabase.auth.sign_out()
        st.sidebar.success("Logged out!")

# Only show email analysis if user is authenticated
if "user" in locals():
    # Secure API Key usage
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

    # Sidebar Features
    st.sidebar.header("Settings")
    features = {
        "sentiment": st.sidebar.checkbox("Perform Sentiment Analysis"),
        "key_phrases": st.sidebar.checkbox("Extract Key Phrases"),
        "response": st.sidebar.checkbox("Generate Suggested Response"),
        "export": st.sidebar.checkbox("Export Options"),
    }

    # Input Email Section
    email_content = st.text_area("Paste your email content here:", height=200)

    MAX_EMAIL_LENGTH = 1000

    @st.cache_data(ttl=3600)
    def get_ai_response(prompt, email_content):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt + email_content[:MAX_EMAIL_LENGTH])
            return response.text.strip()
        except Exception as e:
            st.error(f"Error: {e}")
            return ""

    # Sentiment Analysis
    def get_sentiment(email_content):
        positive_keywords = ["happy", "good", "great", "excellent", "love"]
        negative_keywords = ["sad", "bad", "hate", "angry", "disappointed"]
        sentiment_score = sum([1 if word in positive_keywords else -1 if word in negative_keywords else 0 for word in email_content.split()])
        return "Positive" if sentiment_score > 0 else "Negative" if sentiment_score < 0 else "Neutral"

    # Export to PDF
    def export_pdf(text):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.multi_cell(0, 10, text)
        return pdf.output(dest='S').encode('latin1')

    # Display Analysis if Email Provided
    if email_content and st.button("Analyze Email"):
        summary = get_ai_response("Summarize the email:\n\n", email_content)
        response = get_ai_response("Generate a response:\n\n", email_content) if features["response"] else ""
        sentiment = get_sentiment(email_content)

        st.subheader("Summary")
        st.write(summary)

        if features["response"]:
            st.subheader("Suggested Response")
            st.write(response)

        st.subheader("Sentiment Analysis")
        st.write(f"**Sentiment:** {sentiment}")

        # Export Options
        if features["export"]:
            export_content = f"Summary:\n{summary}\n\nResponse:\n{response}\n\nSentiment: {sentiment}"
            pdf_buffer = BytesIO(export_pdf(export_content))
            st.download_button("Download as PDF", data=pdf_buffer, file_name="analysis.pdf", mime="application/pdf")

else:
    st.warning("Please log in to analyze emails.")
