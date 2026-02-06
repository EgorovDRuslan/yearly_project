import sqlite3 

connection = sqlite3.connect("games.db")
cursor = connection.cursor()

sql_command ="""
CREATE TABLE IF NOT EXISTS games(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    genre TEXT NOT NULL,
    description TEXT NOT NULL,
    date_of_publishing TEXT,
    tags TEXT NOT NULL,
    tba INTEGER NOT NULL,
    rating REAL,
    ratings TEXT,
    ratings_count INTEGER,
    review_text_count INTEGER, 
    added_by_status TEXT,
    metacritic REAL,
    playtime INTEGER,
    updated TEXT,
    dominant_color TEXT,
    platforms TEXT,
    stores TEXT,
    esrb_rating TEXT
);"""

cursor.execute(sql_command)
connection.close()
