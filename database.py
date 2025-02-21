# database.py
import sqlite3

class DatabaseManager:
    def __init__(self, db_path="job_agent.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._initialize_tables()

    def _initialize_tables(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users 
                     (email TEXT PRIMARY KEY, skills TEXT, job_title TEXT, location TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS matches 
                     (email TEXT, job_title TEXT, score REAL, redirect_url TEXT, description TEXT, 
                      company TEXT, location TEXT, salary_max REAL, 
                      FOREIGN KEY(email) REFERENCES users(email))''')
        self.conn.commit()

    def save_user(self, email, skills, job_title, location):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO users (email, skills, job_title, location) VALUES (?, ?, ?, ?)", 
                  (email, skills, job_title, location))
        self.conn.commit()

    def get_user(self, email):
        c = self.conn.cursor()
        c.execute("SELECT skills, job_title, location FROM users WHERE email = ?", (email,))
        return c.fetchone()

    def save_match(self, email, match_data):
        c = self.conn.cursor()
        c.execute('''INSERT INTO matches 
                     (email, job_title, score, redirect_url, description, company, location, salary_max) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                  (email, match_data["title"], match_data["score"], match_data["redirect_url"], 
                   match_data["description"], match_data["company"], match_data["location"], 
                   match_data["salary_max"]))
        self.conn.commit()

    def get_matches(self, email):
        c = self.conn.cursor()
        c.execute("SELECT job_title, score, redirect_url, description, company, location, salary_max FROM matches WHERE email = ? ORDER BY score DESC", (email,))
        return c.fetchall()

if __name__ == "__main__":
    # Test the module standalone
    db = DatabaseManager()
    db.save_user("test@example.com", "Python,Java", "Software Developer", "Remote")
    print(db.get_user("test@example.com"))