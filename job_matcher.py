# job_matcher.py
import google.generativeai as genai

class JobMatcher:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def compute_match_score(self, job_description, skills):
        prompt = f"""
        You are a job matching expert. Given a job description and a list of candidate skills, 
        determine how well the candidate matches the job on a scale of 0 to 1 (0 = no match, 1 = perfect match).
        Consider skill relevance, implied requirements, and context. Return only a float value between 0 and 1.

        Job Description:
        {job_description[:2000]}

        Candidate Skills:
        {', '.join(skills)}
        """
        
        response = self.model.generate_content(prompt)
        try:
            score = float(response.text)
            return min(max(score, 0), 1)
        except (ValueError, AttributeError):
            print(f"Gemini failed to compute score for job: {job_description[:50]}...; using fallback.")
            return 0.5