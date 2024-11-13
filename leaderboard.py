import sqlite3
from datetime import datetime
import sys
import os

# Database initialization
base_path = getattr(sys, "_MEIPASS", os.path.abspath(".")).replace(
    "Frameworks", "Resources"
)
DATABASE_FILE = os.path.join(base_path, "leaderboard.db")


def initialize_database():
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    # Create players table if it doesn't exist
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS players (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    """
    )

    # Create sessions table if it doesn't exist
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            session_start TIMESTAMP NOT NULL,
            session_end TIMESTAMP NOT NULL,
            email TEXT NOT NULL,
            score1 INTEGER NOT NULL,
            score2 INTEGER NOT NULL,
            score3 INTEGER NOT NULL,
            FOREIGN KEY (email) REFERENCES players (email)
        )
    """
    )

    conn.commit()
    conn.close()


# Initialize the database (create tables if they don't exist)
initialize_database()


# Function to add a player if they don't already exist
def add_player(email, name):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    # Check if the player already exists
    c.execute("SELECT * FROM players WHERE email = ?", (email,))
    if c.fetchone() is None:
        # Insert the player into the database
        c.execute("INSERT INTO players (email, name) VALUES (?, ?)", (email, name))

    conn.commit()
    conn.close()


# Function to log a session with scores
def log_session(email, session_start, session_end, scores):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    # Insert the session into the database
    c.execute(
        """
        INSERT INTO sessions (session_start, session_end, email, score1, score2, score3)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (session_start, session_end, email, scores[0], scores[1], scores[2]),
    )

    conn.commit()
    conn.close()


# Function to get the player's name by their email address
def get_player_name(email):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    # Get the player's name by their email
    c.execute("SELECT name FROM players WHERE email = ?", (email,))
    result = c.fetchone()
    conn.close()

    if result:
        return result[0]  # Return the name
    return None  # If the player doesn't exist


# Function to check if a score is the top score
def is_high_score(score):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    c.execute("select max(max(score1), max(score2), max(score3)) from sessions")

    # Fetch the results
    top_score = c.fetchone()[0]
    return top_score and score == top_score


# Function to get the top N scores across all sessions
def get_leaderboard(count=10):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    # Query to get top N scores, allowing multiple scores from the same player
    c.execute(
        """
        SELECT p.name, s.score1, s.score2, s.score3, s.session_end
        FROM sessions s
        JOIN players p ON s.email = p.email
        ORDER BY
            CASE
                WHEN s.score1 >= s.score2 AND s.score1 >= s.score3 THEN s.score1
                WHEN s.score2 >= s.score1 AND s.score2 >= s.score3 THEN s.score2
                ELSE s.score3
            END DESC
        LIMIT ?
    """,
        (count,),
    )

    # Fetch the results
    rows = c.fetchall()

    # Flatten the results, and keep only top 'count' number of scores
    leaderboard_entries = []
    for row in rows:
        name = row[0]
        scores = [row[1], row[2], row[3]]
        session_end = row[4]

        # Extract each score individually and add it to leaderboard_entries
        for score in scores:
            leaderboard_entries.append((name, score, session_end))

    # Sort all the scores by the score value and keep top 'count' entries
    leaderboard_entries = sorted(
        leaderboard_entries, key=lambda x: x[1], reverse=True
    )[:count]

    conn.close()
    return leaderboard_entries
