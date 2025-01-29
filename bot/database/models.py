import sqlite3
import json
from datetime import datetime

def init_db():
    conn = sqlite3.connect('bot/database/bot.db')
    cursor = conn.cursor()
    
    # Create bot_activity table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bot_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        tweet_id TEXT,
        tweet_text TEXT,
        detected_fallacies TEXT,
        response_text TEXT,
        confidence_score REAL,
        is_sandbox INTEGER DEFAULT 0
    )
    ''')
    
    # Create sandbox_tweets table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sandbox_tweets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tweet_text TEXT,
        expected_fallacies TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()

def log_activity(tweet_id, tweet_text, fallacies, response, confidence, is_sandbox=0):
    conn = sqlite3.connect('bot/database/bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO bot_activity 
    (tweet_id, tweet_text, detected_fallacies, response_text, confidence_score, is_sandbox)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        tweet_id,
        tweet_text,
        json.dumps(fallacies),
        response,
        confidence,
        is_sandbox
    ))
    
    conn.commit()
    conn.close()

def save_sandbox_tweet(tweet_text, expected_fallacies):
    conn = sqlite3.connect('bot/database/bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO sandbox_tweets (tweet_text, expected_fallacies)
    VALUES (?, ?)
    ''', (tweet_text, json.dumps(expected_fallacies)))
    
    conn.commit()
    conn.close()

def get_recent_activity(limit=50):
    conn = sqlite3.connect('bot/database/bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM bot_activity 
    ORDER BY timestamp DESC 
    LIMIT ?
    ''', (limit,))
    
    activities = cursor.fetchall()
    conn.close()
    
    return activities

def get_sandbox_tweets():
    conn = sqlite3.connect('bot/database/bot.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM sandbox_tweets ORDER BY created_at DESC')
    tweets = cursor.fetchall()
    conn.close()
    
    return tweets
