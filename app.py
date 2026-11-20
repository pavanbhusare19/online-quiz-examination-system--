
from flask import Flask, request, jsonify, send_from_directory
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "quiz.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            options TEXT NOT NULL,
            correct_option INTEGER NOT NULL,
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            percentage INTEGER NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
        )
    """)

    quiz_count = cursor.execute(
        "SELECT COUNT(*) FROM quizzes"
    ).fetchone()[0]

    if quiz_count == 0:
        sample_quizzes = [
            (
                "Python Programming Basics",
                "Test your knowledge of Python fundamentals.",
                "Programming",
                5
            ),
            (
                "Web Development",
                "Explore HTML, CSS and JavaScript concepts.",
                "Technology",
                5
            ),
            (
                "General Knowledge",
                "Challenge yourself with general knowledge questions.",
                "General",
                5
            )
        ]

        cursor.executemany("""
            INSERT INTO quizzes
            (title, description, category, duration_minutes)
            VALUES (?, ?, ?, ?)
        """, sample_quizzes)

        sample_questions = [
            (1, "Which keyword is used to define a function in Python?",
             ["func", "def", "function", "define"], 1),
            (1, "Which data type stores True or False?",
             ["String", "Integer", "Boolean", "List"], 2),
            (1, "Which symbol is used for comments in Python?",
             ["//", "#", "/*", "--"], 1),
            (1, "Which function displays output in Python?",
             ["echo()", "show()", "print()", "display()"], 2),
            (1, "Which collection stores key-value pairs?",
             ["List", "Tuple", "Set", "Dictionary"], 3),

            (2, "What does HTML stand for?",
             ["Hyper Text Markup Language", "High Text Machine Language",
              "Hyper Transfer Markup Language", "Home Tool Markup Language"], 0),
            (2, "Which CSS property changes text color?",
             ["font-style", "color", "background", "text-size"], 1),
            (2, "Which language adds interactivity to web pages?",
             ["HTML", "CSS", "JavaScript", "SQL"], 2),
            (2, "Which HTML tag creates a hyperlink?",
             ["<link>", "<a>", "<href>", "<url>"], 1),
            (2, "Which symbol starts an ID selector in CSS?",
             [".", "#", "*", "&"], 1),

            (3, "What is the capital of India?",
             ["Mumbai", "New Delhi", "Kolkata", "Chennai"], 1),
            (3, "Which planet is known as the Red Planet?",
             ["Venus", "Jupiter", "Mars", "Saturn"], 2),
            (3, "How many days are there in a leap year?",
             ["364", "365", "366", "367"], 2),
            (3, "Which is the largest ocean?",
             ["Atlantic", "Indian", "Arctic", "Pacific"], 3),
            (3, "What is the national animal of India?",
             ["Lion", "Tiger", "Elephant", "Peacock"], 1)
        ]

        import json

        cursor.executemany("""
            INSERT INTO questions
            (quiz_id, question_text, options, correct_option)
            VALUES (?, ?, ?, ?)
        """, [
            (quiz_id, question, json.dumps(options), correct)
            for quiz_id, question, options, correct in sample_questions
        ])

    conn.commit()
    conn.close()
    print("Quiz database initialized successfully!")


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    if filename in {"app.py", "quiz.db"}:
        return "Not found", 404

    return send_from_directory(BASE_DIR, filename)


@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "database": "connected",
        "application": "QuizMaster"
    })


@app.route("/api/quizzes")
def get_quizzes():
    conn = get_db()

    rows = conn.execute("""
        SELECT q.id, q.title, q.description, q.category,
               q.duration_minutes,
               COUNT(questions.id) AS question_count
        FROM quizzes q
        LEFT JOIN questions ON q.id = questions.quiz_id
        GROUP BY q.id
        ORDER BY q.id
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/quizzes/<int:quiz_id>")
def get_quiz(quiz_id):
    import json

    conn = get_db()

    quiz = conn.execute(
        "SELECT id, title FROM quizzes WHERE id = ?",
        (quiz_id,)
    ).fetchone()

    if not quiz:
        conn.close()
        return jsonify({"error": "Quiz not found"}), 404

    rows = conn.execute("""
        SELECT id, question_text, options
        FROM questions
        WHERE quiz_id = ?
        ORDER BY id
    """, (quiz_id,)).fetchall()

    conn.close()

    questions = [
        {
            "id": row["id"],
            "text": row["question_text"],
            "options": json.loads(row["options"])
        }
        for row in rows
    ]

    return jsonify({
        "quiz": dict(quiz),
        "questions": questions
    })


@app.route("/api/submit", methods=["POST"])
def submit_quiz():
    data = request.get_json(silent=True) or {}

    quiz_id = data.get("quiz_id")
    answers = data.get("answers", {})

    if not isinstance(quiz_id, int) or not isinstance(answers, dict):
        return jsonify({"error": "Invalid submission data"}), 400

    conn = get_db()

    quiz = conn.execute(
        "SELECT id FROM quizzes WHERE id = ?",
        (quiz_id,)
    ).fetchone()

    if not quiz:
        conn.close()
        return jsonify({"error": "Quiz not found"}), 404

    questions = conn.execute("""
        SELECT id, correct_option
        FROM questions
        WHERE quiz_id = ?
    """, (quiz_id,)).fetchall()

    if not questions:
        conn.close()
        return jsonify({"error": "No questions available"}), 400

    correct = 0

    for question in questions:
        submitted = answers.get(str(question["id"]))

        if submitted is None:
            submitted = answers.get(question["id"])

        if submitted == question["correct_option"]:
            correct += 1

    total = len(questions)
    percentage = round((correct / total) * 100)

    cursor = conn.execute("""
        INSERT INTO results
        (quiz_id, score, total, percentage, date)
        VALUES (?, ?, ?, ?, ?)
    """, (
        quiz_id,
        correct,
        total,
        percentage,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    result_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "result_id": result_id,
        "score": correct,
        "total": total,
        "correct": correct,
        "percentage": percentage
    })


@app.route("/api/results")
def get_results():
    conn = get_db()

    rows = conn.execute("""
        SELECT results.id, quizzes.title AS quiz_title,
               results.score, results.total,
               results.percentage, results.date
        FROM results
        JOIN quizzes ON quizzes.id = results.quiz_id
        ORDER BY results.id DESC
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    initialize_database()
    print("QuizMaster backend starting...")
    app.run(host="127.0.0.1", port=5001, debug=False)
