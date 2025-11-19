from flask import Flask, render_template, request, redirect, url_for, send_file, g, jsonify, session
import os, requests
from datetime import datetime
from gtts import gTTS
import psycopg2
from psycopg2.extras import DictCursor
from predict import summarize
from preprocing import get

app = Flask(__name__)
from dotenv import load_dotenv
load_dotenv()

app.secret_key = os.getenv("SECRET_KEY")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("DB_PORT", 5432)
}


def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()


# ============================
# ROUTES
# ============================
@app.route("/")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("Home.html")


# ============================
# FETCH NEWS
# ============================
@app.route("/fetch-news")
def fetch_news():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    api_key = os.getenv("NEWS_API_KEY")

    lang = request.args.get("lang", "en")
    url = f"https://newsdata.io/api/1/news?apikey={api_key}&language={lang}&country=in"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        articles = []
        if data.get("results"):
            conn = get_db()
            cur = conn.cursor(cursor_factory=DictCursor)

            # count existing records
            cur.execute("SELECT COUNT(*) FROM news_articles WHERE user_id = %s", (session["user_id"],))
            count = cur.fetchone()[0]

            # delete older if > 100
            if count > 100:
                to_delete = count - 100
                cur.execute("""
                    DELETE FROM news_articles
                    WHERE id IN (
                        SELECT id FROM news_articles
                        WHERE user_id = %s
                        ORDER BY published_date ASC
                        LIMIT %s
                    )
                """, (session["user_id"], to_delete))

            # insert new news (max 30)
            for article in data["results"][:30]:
                title = article.get("title")
                source = article.get("source_id", "Unknown")
                link = article.get("link", "#")
                description = article.get("description", "")
                lang = article.get("language", "en")

                if not title or not description:
                    continue

                cur.execute("""
                    INSERT INTO news_articles (title, source, url, language, summary, user_id, published_date)
                    VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE)
                """, (title, source, link, lang, description, session["user_id"]))

                articles.append({
                    "title": title,
                    "source": source,
                    "url": link,
                    "summary": description,
                    "language": lang
                })

            conn.commit()
            cur.close()

        return jsonify({"articles": articles})

    except Exception as e:
        print("Error in /fetch-news:", e)
        return jsonify({"error": str(e), "articles": []})


# ============================
# INPUT TEXT
# ============================
@app.route("/text")
def input_text():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("text.html")


# ============================
# OUTPUT SUMMARY
# ============================
@app.route("/output", methods=["POST"])
def output():
    if "user" not in session:
        return redirect(url_for("login"))

    text = request.form.get("text")
    summary = summarize(paragraph=text)
    output_text = " ".join(summary)

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO summaries (user_id, original_text, summarized_text, timestamp)
        VALUES (%s, %s, %s, NOW())
    """, (session["user_id"], text, output_text))

    conn.commit()
    cur.close()

    # audio
    audio_dir = os.path.join("static", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    audio_filename = f"output_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
    audio_path = os.path.join(audio_dir, audio_filename)

    tts = gTTS(text=output_text, lang="en")
    tts.save(audio_path)

    return render_template(
        "output.html",
        original=text,
        summary=output_text,
        audio_file=f"audio/{audio_filename}"
    )


# ============================
# HISTORY
# ============================
@app.route("/history")
def history():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cur = conn.cursor(cursor_factory=DictCursor)
    cur.execute("""
        SELECT original_text, summarized_text, timestamp
        FROM summaries
        WHERE user_id = %s
        ORDER BY timestamp DESC
    """, (session["user_id"],))

    summaries = cur.fetchall()
    cur.close()

    return render_template("history.html", summaries=summaries)


# ============================
# LOGIN
# ============================
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, username FROM users WHERE username=%s AND password=%s
        """, (username, password))

        user = cur.fetchone()
        cur.close()

        if user:
            session["user"] = user[1]
            session["user_id"] = user[0]
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password."

    return render_template("login.html", error=error)


# ============================
# SIGNUP
# ============================
@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO users (username, password, role_id)
                VALUES (%s, %s, 2)
            """, (username, password))
            conn.commit()
        except Exception:
            error = "Username already exists."
        finally:
            cur.close()

        if not error:
            return redirect(url_for("login"))

    return render_template("signup.html", error=error)


# ============================
# LOGOUT
# ============================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
