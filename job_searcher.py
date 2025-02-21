# job_searcher.py
import requests
from database import DatabaseManager

class JobSearcher:
    def __init__(self, app_id, app_key, matcher):
        self.app_id = app_id
        self.app_key = app_key
        self.matcher = matcher  # Job Matching Agent
        self.db = DatabaseManager()

    def search_jobs(self, email):
        """Search for jobs using Adzuna API and match them with LLM."""
        user_data = self.db.get_user(email)
        if not user_data:
            print(f"No user data for {email}")
            return []
        
        skills, job_title, location = user_data[0].split(","), user_data[1], user_data[2]
        print(f"Searching for: {job_title} in {location}, Skills: {skills}")
        
        url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
        params = {
            "app_id": self.app_id,
            "app_key": self.app_key,
            "what": job_title,
            "where": location,
            "results_per_page": 10,
            "content-type": "application/json"
        }
        
        try:
            response = requests.get(url, params=params)
            print(f"API Status Code: {response.status_code}")
            print(f"API Response (first 500 chars): {response.text[:500]}")
            response.raise_for_status()
            jobs = response.json().get("results", [])
            print(f"Found {len(jobs)} jobs")
        except requests.RequestException as e:
            print(f"Error fetching jobs: {e}")
            return []

        matches = []
        for job in jobs:
            desc = job["description"]
            print(f"Job: {job['title']}, Description: {desc[:200]}...")
            match_score = self.matcher.compute_match_score(desc, skills)  # Use LLM Agent
            print(f"Job: {job['title']}, Score: {match_score}")
            if match_score > 0.3:  # Threshold
                match_data = {
                    "title": job["title"],
                    "score": match_score,
                    "redirect_url": job.get("redirect_url", ""),
                    "description": job.get("description", ""),
                    "company": job["company"].get("display_name", ""),
                    "location": job["location"].get("display_name", ""),
                    "salary_max": job.get("salary_max", 0)
                }
                matches.append(match_data)
                self.db.save_match(email, match_data)
                print(f"Saved match: {job['title']} for {email}")
        return matches

if __name__ == "__main__":
    # Test the module standalone
    from job_matcher import JobMatcher
    matcher = JobMatcher()
    searcher = JobSearcher("8940cc9a", "0cf476c449a223260cd2e5f5a897e49e", matcher)
    # Requires a user in the DB to test; add manually for standalone testing