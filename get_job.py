import streamlit as st
import sqlite3
import fitz  # PyMuPDF
import requests
import schedule
import time
import threading
import json
import os
from dotenv import load_dotenv
from ollama import Client  # Ollama Python client

load_dotenv()

ADZUNA_APP_IDADZUNA_APP_ID=os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY =os.getenv("ADZUNA_APP_KEY")
# Initialize Ollama client (assumes Ollama is running locally)
ollama_client = Client(host='http://localhost:11434')  # Default Ollama port

# Database setup with expanded schema
conn = sqlite3.connect("job_agent.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (email TEXT PRIMARY KEY, skills TEXT, job_title TEXT, location TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS matches 
             (email TEXT, job_title TEXT, score REAL, redirect_url TEXT, description TEXT, 
              company TEXT, location TEXT, salary_max REAL, 
              FOREIGN KEY(email) REFERENCES users(email))''')
conn.commit()

# Agent 1: Resume Parsing Agent using Ollama LLM
def parse_resume_with_llm(resume_text):
    prompt = f"""
    You are a resume parsing expert. Extract the following from the provided resume text in JSON format:
    - Skills (list of technical and soft skills)
    - Job titles (list of previous job titles)
    - Experience (list of dicts with job title, company, duration)
    - Education (list of dicts with degree, institution, year)

    Resume text:
    {resume_text[:2000]}  # Limit to 2000 chars to avoid token limits; adjust as needed
    """
    
    response = ollama_client.chat(model='qwen2.5-coder', messages=[{"role": "user", "content": prompt}])
    try:
        parsed_data = json.loads(response['message']['content'])
        # Ensure skills is a list; fallback if LLM fails
        if not isinstance(parsed_data.get("skills"), list):
            parsed_data["skills"] = ["Python", "Java", "SQL"]  # Fallback
        return parsed_data
    except json.JSONDecodeError:
        print("LLM failed to return valid JSON; using fallback.")
        return {
            "skills": ["Python", "Java", "JavaScript", "SQL", "Teamwork"],  # Fallback
            "job_titles": ["Software Engineer"],
            "experience": [{"job_title": "Software Engineer", "company": "Tech Corp", "duration": "2020-2023"}],
            "education": [{"degree": "B.S. Computer Science", "institution": "University X", "year": "2018"}]
        }

# Agent 2: Job Matching Agent using Ollama LLM
def compute_match_score(job_description, skills):
    prompt = f"""
    You are a job matching expert. Given a job description and a list of candidate skills, determine how well the candidate matches the job on a scale of 0 to 1 (0 = no match, 1 = perfect match). Consider skill relevance, implied requirements, and context. Return only a float value between 0 and 1.

    Job Description:
    {job_description[:2000]}  # Limit to 2000 chars

    Candidate Skills:
    {', '.join(skills)}
    """
    
    response = ollama_client.chat(model='qwen2.5-coder', messages=[{"role": "user", "content": prompt}])
    try:
        score = float(response['message']['content'])
        return min(max(score, 0), 1)  # Clamp between 0 and 1
    except (ValueError, TypeError):
        print(f"LLM failed to return a valid score for job: {job_description[:50]}...; using fallback.")
        return 0.5  # Fallback score if LLM fails

# Adzuna API credentials
ADZUNA_APP_ID = "8940cc9a"
ADZUNA_APP_KEY = "0cf476c449a223260cd2e5f5a897e49e"

# Job search function with LLM-based matching
def search_jobs(email):
    c.execute("SELECT skills, job_title, location FROM users WHERE email = ?", (email,))
    user_data = c.fetchone()
    if not user_data:
        print(f"No user data for {email}")
        st.write(f"No user data for {email}")
        return
    
    skills, job_title, location = user_data[0].split(","), user_data[1], user_data[2]
    print(f"Searching for: {job_title} in {location}, Skills: {skills}")
    st.write(f"Searching for: {job_title} in {location}, Skills ({len(skills)} total): {skills[:10]}...")
    
    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "what": job_title,
        "where": location,
        "results_per_page": 10,
        "content-type": "application/json"
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"API Status Code: {response.status_code}")
        print(f"API Response (first 500 chars): {response.text[:500]}")
        st.write(f"API Status Code: {response.status_code}")
        st.write(f"API Response (first 500 chars): {response.text[:500]}")
        response.raise_for_status()
        jobs = response.json().get("results", [])
        print(f"Found {len(jobs)} jobs")
        st.write(f"Found {len(jobs)} jobs")
    except requests.RequestException as e:
        print(f"Error fetching jobs: {e}")
        st.error(f"Error fetching jobs: {e}")
        return []

    matches = []
    for job in jobs:
        desc = job["description"]
        print(f"Job: {job['title']}, Description: {desc[:200]}...")
        match_score = compute_match_score(desc, skills)  # Use LLM for scoring
        print(f"Job: {job['title']}, Score: {match_score}")
        st.write(f"Job: {job['title']}, Score: {match_score}")
        if match_score > 0.3:  # Adjusted threshold for LLM-based scoring
            matches.append({
                "title": job["title"],
                "score": match_score,
                "redirect_url": job.get("redirect_url", ""),
                "description": job.get("description", ""),
                "company": job["company"].get("display_name", ""),
                "location": job["location"].get("display_name", ""),
                "salary_max": job.get("salary_max", 0)
            })
            c.execute('''INSERT INTO matches 
                         (email, job_title, score, redirect_url, description, company, location, salary_max) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (email, job["title"], match_score, job.get("redirect_url", ""), 
                       job.get("description", ""), job["company"].get("display_name", ""), 
                       job["location"].get("display_name", ""), job.get("salary_max", 0)))
            print(f"Saved match: {job['title']} for {email}")
            st.write(f"Saved match: {job['title']} for {email}")
    conn.commit()
    return matches

# Background scheduler
def run_job_search():
    c.execute("SELECT email FROM users")
    users = c.fetchall()
    for (user_email,) in users:
        search_jobs(user_email)

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
        parsed_data = parse_resume_with_llm(resume_text)  # Use LLM Agent 1
        skills_str = ",".join(parsed_data["skills"])
        c.execute("INSERT OR REPLACE INTO users (email, skills, job_title, location) VALUES (?, ?, ?, ?)", 
                  (email, skills_str, job_title, location))
        conn.commit()
        search_jobs(email)  # Run search with LLM Agent 2
        st.sidebar.success("Preferences saved! Job search started.")
        st.sidebar.write("Extracted Skills (first 10):", parsed_data["skills"][:10], "...")
    else:
        st.sidebar.error("Failed to extract text from PDF.")

# Display matches with more details
if email:
    st.header("Your Job Matches")
    c.execute("SELECT job_title, score, redirect_url, description, company, location, salary_max FROM matches WHERE email = ? ORDER BY score DESC", (email,))
    matches = c.fetchall()
    print(f"Database matches found: {len(matches)}")
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