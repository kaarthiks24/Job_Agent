# app.py
import streamlit as st
import schedule
import time
import threading
import fitz  # PyMuPDF
from resume_parser import ResumeParser
from job_matcher import JobMatcher
from job_searcher import JobSearcher
from database import DatabaseManager

# Initialize components
resume_parser = ResumeParser(st.secrets["gemini"]["api_key"])
job_matcher = JobMatcher(st.secrets["gemini"]["api_key"])
job_searcher = JobSearcher("8940cc9a", "0cf476c449a223260cd2e5f5a897e49e", job_matcher)
db = DatabaseManager()

# Background scheduler
def run_job_search():
    users = [row[0] for row in db.conn.execute("SELECT email FROM users")]
    for user_email in users:
        job_searcher.search_jobs(user_email)

def run_scheduler():
    schedule.every(1).days.do(run_job_search)
    while True:
        schedule.run_pending()
        time.sleep(60)

threading.Thread(target=run_scheduler, daemon=True).start()

# Streamlit App
st.title("AI Job Search Agent with LLM Agents")

# Sidebar for user input
st.sidebar.header("User Setup")
email = st.sidebar.text_input("Your Email")
uploaded_file = st.sidebar.file_uploader("Upload Your Resume (PDF)", type="pdf")
job_title = st.sidebar.text_input("Desired Job Title", "Software Developer")
location = st.sidebar.text_input("Preferred Location", "Remote")
submit = st.sidebar.button("Save & Start")

# Parse resume and run search
if submit and uploaded_file is not None:
    pdf_document = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    resume_text = "".join(page.get_text() or "" for page in pdf_document)
    pdf_document.close()

    if resume_text:
        parsed_data = resume_parser.parse_resume(resume_text)  # Agent 1
        skills_str = ",".join(parsed_data["skills"])
        db.save_user(email, skills_str, job_title, location)
        job_searcher.search_jobs(email)  # Agent 2 via JobSearcher
        st.sidebar.success("Preferences saved! Job search started.")
        st.sidebar.write("Extracted Skills (first 10):", parsed_data["skills"][:10], "...")
    else:
        st.sidebar.error("Failed to extract text from PDF.")

# Display matches
if email:
    st.header("Your Job Matches")
    matches = db.get_matches(email)
    st.write(f"Database matches found: {len(matches)}")
    if matches:
        for job_title, score, redirect_url, description, company, location, salary_max in matches:
            st.subheader(job_title)
            st.write(f"**Match Score:** {score*100:.0f}%")
            st.write(f"**Company:** {company}")
            st.write(f"**Location:** {location}")
            st.write(f"**Salary (Max):** ${salary_max:,.2f}" if salary_max else "**Salary:** Not provided")
            st.write(f"**Description:** {description[:200]}..." if len(description) > 200 else description)
            st.markdown(f"[View Job Listing]({redirect_url})", unsafe_allow_html=True)
            st.write("---")
    else:
        st.write("No matches yet. Check job descriptions for skill matches.")