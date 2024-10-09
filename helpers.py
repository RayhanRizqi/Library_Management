import os
import requests
import urllib.parse
import psycopg2

from flask import redirect, render_template, request, session
from functools import wraps

conn = psycopg2.connect(database="flask_db", user="postgres",
                        password="root", host="localhost", port="5432")

db = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

def apology(message, code=400):
    """Render message as an apology to user"""
    def escape(s):
        """
        Escape special characters

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code

def login_required(f):
    """
    Decorate routes to require login and verify that the user exists in the database.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        
        # If there's no user_id in session, redirect to login
        if user_id is None:
            return redirect("/login")
        
        # Check if the user_id exists in the users table
        db.execute("SELECT * FROM users WHERE uid = %s", (user_id,))
        user = db.fetchone()

        if user is None:
            # If user_id doesn't exist in the database, clear session and redirect to login
            session.clear()
            return redirect("/login")

        # If the user is valid, proceed with the original function
        return f(*args, **kwargs)
    
    return decorated_function