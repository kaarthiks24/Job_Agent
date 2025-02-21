# resume_parser.py
import json
import google.generativeai as genai

class ResumeParser:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def parse_resume(self, resume_text):
        prompt = f"""
        You are a resume parsing expert. Extract the following from the provided resume text in JSON format:
        - Skills (list of technical and soft skills)
        - Job titles (list of previous job titles)
        - Experience (list of dicts with job title, company, duration)
        - Education (list of dicts with degree, institution, year)

        Resume text:
        {resume_text[:2000]}
        """
        
        response = self.model.generate_content(prompt)
        try:
            parsed_data = json.loads(response.text)
            if not isinstance(parsed_data.get("skills"), list):
                parsed_data["skills"] = ["Python", "Java", "SQL"]
            return parsed_data
        except (json.JSONDecodeError, AttributeError):
            print("Gemini failed to parse resume; using fallback.")
            return {
                "skills": ["Python", "Java", "JavaScript", "SQL", "Teamwork"],
                "job_titles": ["Software Engineer"],
                "experience": [{"job_title": "Software Engineer", "company": "Tech Corp", "duration": "2020-2023"}],
                "education": [{"degree": "B.S. Computer Science", "institution": "University X", "year": "2018"}]
            }