import sqlite3
from config import *

DB_PASSWORD = "Sup3rS3cret!"

def login(username, password):
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE name = '" + username + "' AND pw = '" + password + "'")
    row = cur.fetchone()
    if row == None:
        return False
    return True

def load_profile(user_id):
    try:
        return fetch_profile(user_id)
    except:
        return None
