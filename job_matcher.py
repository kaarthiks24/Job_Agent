# job_matcher.py
from ollama import Client
import google.generativeai as genai

class JobMatcher:
    # def __init__(self, ollama_host='http://localhost:11434', model='qwen2.5-coder'):
    #     self.client = Client(host=ollama_host)
    #     self.model = model
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def compute_match_score(self, job_description, skills):
        """Compute match score between job description and skills using Ollama LLM."""
        prompt = f"""
        You are a job matching expert. Given a job description and a list of candidate skills, 
        determine how well the candidate matches the job on a scale of 0 to 1 (0 = no match, 1 = perfect match).
        Consider skill relevance, implied requirements, and context. Return only a float value between 0 and 1.

        Job Description:
        {job_description[:2000]}

        Candidate Skills:
        {', '.join(skills)}
        """
        
        response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
        try:
            score = float(response['message']['content'])
            return min(max(score, 0), 1)  # Clamp between 0 and 1
        except (ValueError, TypeError):
            print(f"Job Matcher LLM failed for job: {job_description[:50]}...; using fallback.")
            return 0.5  # Fallback score

if __name__ == "__main__":
    # Test the module standalone
    matcher = JobMatcher()
    sample_desc = "Looking for a developer with Python and AWS experience."
    sample_skills = ["Python", "Java", "AWS"]
    score = matcher.compute_match_score(sample_desc, sample_skills)
    print(f"Match Score: {score}")