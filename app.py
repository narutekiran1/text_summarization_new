from flask import Flask, render_template, request, redirect, url_for, send_file, g, jsonify
import sqlite3
from predict import summarize
from preprocing import get
import requests
from gtts import gTTS
import os

app = Flask(__name__)

# Create database connection
def create_connection():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT, password TEXT)''')
    conn.commit()
    conn.close()

# Initialize the database on startup
create_connection()

# Helper function to get a database connection from Flask's global object `g`
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect('database.db')
    return g.db

# Close the database connection after each request
@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Home route that fetches news data
@app.route("/")
@app.route("/")
def home():
    # Include specific Indian news sources you want to fetch articles from
    URL = ("http://newsapi.org/v2/top-headlines?"
           "country=in&"
           "language=en&"
           "sources=bbc-news,times-now,hindustan-times,the-times-of-india&"
           "apiKey=2e0ec8c57e8e4da7aef1822653d387ec")
    
    try:
        r = requests.get(url=URL)
        r.raise_for_status()  # Raise an error if there's a bad status code
        data = r.json()
        if "articles" not in data or not data["articles"]:
            data = {"articles": []}  # Fallback to empty list if no articles are found
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        data = {"articles": []}  # Render with empty articles if there's an error
    return render_template("Home.html", data=data)

# Route for input text and summarization
@app.route("/text", methods=["GET", "POST"])
def predict():
    return render_template("text.html")


@app.route("/output", methods=["POST"])
def output():
    text = request.form.get("text")
    summary = summarize(paragraph=text)
    output = ' '.join(summary)
    tts = gTTS(text=output, lang='en')  
    tts.save("output.mp3")
    os.system("start output.mp3")

    return render_template("text.html", output=output)

# Route for generating audio from a summary of a news article
@app.route("/generate-audio", methods=["POST"])
def generate_audio():
    data = request.get_json()
    text = data.get("text")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Generate the audio from the text using gTTS
    tts = gTTS(text=text, lang='en')
    temp_file = "temp.mp3"
    tts.save(temp_file)

    # Return the audio file as a response
    return send_file(temp_file, as_attachment=False)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            return redirect(url_for('home'))
        else:
            return "Invalid username or password"
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template("signup.html")

if __name__ == "__main__":
    app.run(debug=True)

