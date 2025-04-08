from flask import Flask, render_template, request, redirect, url_for, send_file, g, jsonify, session
import sqlite3
import os
import time
from predict import summarize
from preprocing import get
import requests
from gtts import gTTS
import socket

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

DATABASE = "database.db"

# Function to create or reset the database
def create_connection():
    if os.path.exists(DATABASE):
        try:
            conn = sqlite3.connect(DATABASE)
            c = conn.cursor()
            c.execute("PRAGMA integrity_check;")
            result = c.fetchone()
            if result[0] != "ok":
                print("Database corruption detected! Resetting database...")
                conn.close()
                os.remove(DATABASE)  # Delete the corrupted database
        except sqlite3.DatabaseError:
            print("Database error detected. Resetting database...")
            conn.close()
            os.remove(DATABASE)  # Delete the corrupted database

    # Create a fresh database
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL)''')

    # Summaries Table for history feature
    c.execute('''CREATE TABLE IF NOT EXISTS summaries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  original_text TEXT NOT NULL,
                  summarized_text TEXT NOT NULL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()

# Initialize the database
create_connection()

# Helper function to get a database connection
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
    return g.db

# Close database connection after each request
@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Home route (User must be logged in)
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("Home.html")

# Fetch news and summarize using PageRank
@app.route("/fetch-news")
def fetch_news():
    if "user" not in session:
        return jsonify({"error": "Unauthorized access"}), 403

    NEWS_API_URL = "https://newsdata.io/api/1/latest?apikey=pub_72436a42dfa02a50ea760fffcbce61fb0179e&language=hi,mr"

    try:
        response = requests.get(NEWS_API_URL)
        data = response.json()

        if data.get("status") != "success" or "results" not in data:
            return jsonify({"error": "Failed to fetch news"}), 500

        articles = []
        for article in data["results"][:30]:  # Get up to 30 articles
            title = article.get("title", "No title available")
            description = article.get("description", "No description available")
            source = article.get("source_id", "Unknown Source")
            url = article.get("link", "#")

            # Apply PageRank summarization
            summary_list = summarize(paragraph=description)
            summary = " ".join(summary_list) if summary_list else description  # Fallback to original text if summarization fails

            articles.append({
                "title": title,
                "summary": summary,  # Use summarized text
                "source": source,
                "url": url
            })

        return jsonify({"articles": articles})

    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return jsonify({"error": "Failed to connect to the news API"}), 500

# Route for text summarization
@app.route("/text", methods=["GET", "POST"])
def predict():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("text.html")

# Generate and save text summary

@app.route("/output", methods=["POST"])
def output():
    if "user" not in session:
        return redirect(url_for("login"))

    text = request.form.get("text")
    summary = summarize(paragraph=text)
    output = ' '.join(summary)

    # Save summary in database
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO summaries (username, original_text, summarized_text) VALUES (?, ?, ?)",
              (session["user"], text, output))
    conn.commit()

    # Generate and save audio
    tts = gTTS(text=output, lang='en')
    audio_path = os.path.join("static", "audio", "output.mp3")
    tts.save(audio_path)

    # Only play audio if running on localhost
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    if local_ip.startswith("127.") or local_ip == "localhost":
        try:
            os.system("start " + audio_path)
        except Exception as e:
            print("Audio play error:", e)

    return render_template("output.html", original=text, summary=output, audio_file=audio_path)
@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT original_text, summarized_text, timestamp FROM summaries WHERE username=? ORDER BY timestamp DESC",
              (session["user"],))
    summaries = c.fetchall()

    return render_template("history.html", summaries=summaries)

# Generate audio from a news summary
@app.route('/generate-audio', methods=['POST'])
def generate_audio():
    data = request.json
    text = data.get("text", "")
    language = data.get("language", "en")  # Default to English

    if not text.strip():
        return jsonify({"error": "No text provided"}), 400

    try:
        tts = gTTS(text=text, lang=language)
        audio_path = "static/audio.mp3"
        tts.save(audio_path)
        return send_file(audio_path, mimetype="audio/mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username  # Store user session
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password. Try again."

    return render_template("login.html", error=error)

# Signup route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = "user"  # Default role

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
            conn.commit()
        except sqlite3.IntegrityError:
            error = "Username already exists."
        finally:
            conn.close()

        if not error:
            return redirect(url_for("login"))

    return render_template("signup.html", error=error)

# Logout route
@app.route("/logout")
def logout():
    session.pop("user", None)  # Remove user from session
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
