from flask import Flask, render_template, request, redirect, url_for, send_file, g, jsonify, session
import os, requests, socket
from datetime import datetime
from gtts import gTTS
import oracledb
from predict import summarize
from preprocing import get

# ===========================
# Flask App
# ===========================
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Required for session management

# ===========================
# Oracle DB Config
# ===========================
DB_USER = "proj_user"
DB_PASSWORD = "project123"
DB_DSN = "localhost:1521/XEPDB1"

def get_db():
    if 'db' not in g:
        g.db = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=DB_DSN
        )
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            db.close()
        except oracledb.InterfaceError:
            # Ignore "not connected" error
            pass



# ===========================
# Routes
# ===========================

@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("Home.html")


# -------- Fetch News API --------
@app.route("/fetch-news")
def fetch_news():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    api_key = "pub_72436a42dfa02a50ea760fffcbce61fb0179e"
    lang = request.args.get("lang", "en")
    url = f"https://newsdata.io/api/1/news?apikey={api_key}&language={lang}&country=in"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        articles = []
        if data.get("results"):
            conn = get_db()
            cursor = conn.cursor()

            # Delete old records for this user to keep only latest news
            cursor.execute("DELETE FROM news_articles WHERE user_id = :1", (session["user_id"],))

            for article in data["results"][:30]:  # Limit to 30
                title = article.get("title")
                source = article.get("source_id", "Unknown")
                link = article.get("link", "#")
                description = article.get("description", "")
                lang = article.get("language", "en")

                if not title or not description:
                    continue

                cursor.execute("""
                    INSERT INTO news_articles (title, source, url, language, user_id)
                    VALUES (:1, :2, :3, :4, :5)
                """, (title, source, link, lang, session["user_id"]))

                articles.append({
                    "title": title,
                    "source": source,
                    "url": link,
                    "summary": description,
                    "language": lang
                })

            conn.commit()
            cursor.close()
            conn.close()

        return jsonify({"articles": articles})

    except Exception as e:
        print("Error in /fetch-news:", e)
        return jsonify({"error": str(e), "articles": []})




# -------- Text Input --------
@app.route("/text")
def input_text():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("text.html")


# -------- Summarize Output --------
@app.route("/output", methods=["POST"])
def output():
    if "user" not in session:
        return redirect(url_for("login"))

    text = request.form.get("text")
    summary = summarize(paragraph=text)
    output_text = ' '.join(summary)

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO summaries (user_id, original_text, summarized_text) 
        VALUES (:1, :2, :3)
    """, (session["user_id"], text, output_text))
    conn.commit()
    c.close()

    # Create audio
    audio_dir = os.path.join("static", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    audio_filename = f"output_{timestamp}.mp3"
    audio_path = os.path.join(audio_dir, audio_filename)

    tts = gTTS(text=output_text, lang='en')
    tts.save(audio_path)

    return render_template("output.html", original=text, summary=output_text, audio_file=f"audio/{audio_filename}")


# -------- History --------
@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT original_text, summarized_text, timestamp 
        FROM summaries 
        WHERE user_id=:1 
        ORDER BY timestamp DESC
    """, (session["user_id"],))
    summaries = c.fetchall()
    c.close()

    return render_template("history.html", summaries=summaries)


# -------- Generate Audio --------
@app.route('/generate-audio', methods=['POST'])
def generate_audio():
    data = request.json
    text = data.get("text", "")
    language = data.get("language", "en")

    if not text.strip():
        return jsonify({"error": "No text provided"}), 400

    try:
        audio_dir = os.path.join("static", "audio")
        os.makedirs(audio_dir, exist_ok=True)

        tts = gTTS(text=text, lang=language)
        audio_path = os.path.join(audio_dir, "audio.mp3")
        tts.save(audio_path)
        return send_file(audio_path, mimetype="audio/mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -------- Login --------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, username FROM users WHERE username=:1 AND password=:2", (username, password))
        user = c.fetchone()
        c.close()

        if user:
            session["user"] = user[1]
            session["user_id"] = user[0]
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password. Try again."

    return render_template("login.html", error=error)


# -------- Signup --------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role_id = 2  # default role: User

        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, role_id) VALUES (:1, :2, :3)",
                      (username, password, role_id))
            conn.commit()
        except oracledb.IntegrityError:
            error = "Username already exists."
        finally:
            c.close()

        if not error:
            return redirect(url_for("login"))

    return render_template("signup.html", error=error)


# -------- Logout --------
@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("user_id", None)
    return redirect(url_for("login"))


# ===========================
# Run App
# ===========================
if __name__ == "__main__":
    app.run(debug=True)
