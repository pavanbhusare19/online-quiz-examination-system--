
let quizzes = [];
let currentQuiz = null;
let questions = [];
let currentQuestion = 0;
let answers = {};
let timerInterval = null;
let timeLeft = 0;

const $ = (id) => document.getElementById(id);

async function api(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...options
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "Something went wrong");
    }

    return data;
}

function showToast(message) {
    const toast = $("toast");
    if (!toast) return;

    toast.textContent = message;
    toast.classList.add("show");

    setTimeout(() => toast.classList.remove("show"), 2500);
}

function showPage(pageId) {
    document.querySelectorAll(".page").forEach(page => {
        page.classList.add("hidden");
    });

    const page = $(pageId);
    if (page) page.classList.remove("hidden");

    document.querySelectorAll(".nav-link").forEach(link => {
        link.classList.toggle(
            "active",
            link.dataset.page === pageId.replace("Page", "")
        );
    });

    if (pageId === "resultsPage") loadResults();
    if (pageId === "allQuizzesPage") renderQuizzes("allQuizGrid");
}

async function loadQuizzes() {
    try {
        quizzes = await api("/api/quizzes");

        renderQuizzes("dashboardQuizGrid", 3);

        const total = $("totalQuizzes");
        if (total) total.textContent = quizzes.length;

        await loadResults();
    } catch (error) {
        showToast(error.message);
    }
}

function renderQuizzes(containerId, limit = Infinity) {
    const container = $(containerId);
    if (!container) return;

    container.innerHTML = "";

    const icons = ["💻", "🌐", "🧠", "📚", "⚡"];

    quizzes.slice(0, limit).forEach((quiz, index) => {
        const card = document.createElement("article");
        card.className = "quiz-card";

        const icon = document.createElement("div");
        icon.className = "quiz-emoji";
        icon.textContent = icons[index % icons.length];

        const title = document.createElement("h3");
        title.textContent = quiz.title;

        const description = document.createElement("p");
        description.textContent = quiz.description;

        const meta = document.createElement("div");
        meta.className = "quiz-meta";
        meta.textContent =
            `${quiz.question_count} Questions · ${quiz.duration_minutes} Minutes`;

        const button = document.createElement("button");
        button.className = "primary-btn";
        button.textContent = "Start Quiz";
        button.addEventListener("click", () => startQuiz(quiz.id));

        card.append(icon, title, description, meta, button);
        container.appendChild(card);
    });
}

async function startQuiz(quizId) {
    try {
        currentQuiz = quizzes.find(q => q.id === quizId);

        const data = await api(`/api/quizzes/${quizId}`);

        questions = data.questions;
        currentQuestion = 0;
        answers = {};
        timeLeft = currentQuiz.duration_minutes * 60;

        showPage("quizPage");
        $("quizTitle").textContent = currentQuiz.title;

        renderQuestion();
        startTimer();
    } catch (error) {
        showToast(error.message);
    }
}

function renderQuestion() {
    const question = questions[currentQuestion];

    $("questionNumber").textContent =
        `Question ${currentQuestion + 1} of ${questions.length}`;

    $("questionText").textContent = question.text;

    $("progressBar").style.width =
        `${((currentQuestion + 1) / questions.length) * 100}%`;

    const container = $("optionsContainer");
    container.innerHTML = "";

    question.options.forEach((option, index) => {
        const label = document.createElement("label");
        label.className = "option";

        if (answers[question.id] === index) {
            label.classList.add("selected");
        }

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "quizOption";
        radio.value = index;
        radio.checked = answers[question.id] === index;

        radio.addEventListener("change", () => {
            answers[question.id] = index;
            renderQuestion();
        });

        const text = document.createElement("span");
        text.textContent = option;

        label.append(radio, text);
        container.appendChild(label);
    });

    $("previousBtn").disabled = currentQuestion === 0;

    $("nextBtn").classList.toggle(
        "hidden",
        currentQuestion === questions.length - 1
    );

    $("submitBtn").classList.toggle(
        "hidden",
        currentQuestion !== questions.length - 1
    );
}

function startTimer() {
    clearInterval(timerInterval);
    updateTimer();

    timerInterval = setInterval(() => {
        timeLeft--;
        updateTimer();

        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            submitQuiz(true);
        }
    }, 1000);
}

function updateTimer() {
    const minutes = Math.floor(timeLeft / 60);
    const seconds = timeLeft % 60;

    $("timer").textContent =
        `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function nextQuestion() {
    if (currentQuestion < questions.length - 1) {
        currentQuestion++;
        renderQuestion();
    }
}

function previousQuestion() {
    if (currentQuestion > 0) {
        currentQuestion--;
        renderQuestion();
    }
}

async function submitQuiz(autoSubmit = false) {
    if (!autoSubmit) {
        const unanswered = questions.filter(
            q => answers[q.id] === undefined
        ).length;

        if (unanswered > 0) {
            const confirmed = confirm(
                `${unanswered} question(s) are unanswered. Submit anyway?`
            );

            if (!confirmed) return;
        } else if (!confirm("Are you sure you want to submit your quiz?")) {
            return;
        }
    }

    clearInterval(timerInterval);
    $("submitBtn").disabled = true;

    try {
        const result = await api("/api/submit", {
            method: "POST",
            body: JSON.stringify({
                quiz_id: currentQuiz.id,
                answers
            })
        });

        $("resultScore").textContent =
            `${result.percentage}%`;

        $("resultDetails").textContent =
            `You answered ${result.correct} out of ${result.total} questions correctly.`;

        $("resultMessage").textContent =
            result.percentage >= 80
                ? "Excellent work! 🎉"
                : result.percentage >= 50
                    ? "Good effort! Keep practicing."
                    : "Keep learning and try again!";

        $("submitBtn").disabled = false;

        showPage("resultPage");
        await loadResults();
    } catch (error) {
        $("submitBtn").disabled = false;
        showToast(error.message);
    }
}

async function loadResults() {
    try {
        const results = await api("/api/results");

        const completed = $("completedQuizzes");
        const average = $("averageScore");

        if (completed) completed.textContent = results.length;

        if (average) {
            const avg = results.length
                ? results.reduce((sum, r) => sum + r.percentage, 0) / results.length
                : 0;

            average.textContent = `${Math.round(avg)}%`;
        }

        const table = $("resultsTable");
        if (!table) return;

        table.innerHTML = "";

        if (results.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 4;
            cell.textContent = "No quiz results yet. Take your first quiz!";
            row.appendChild(cell);
            table.appendChild(row);
            return;
        }

        results.forEach(result => {
            const row = document.createElement("tr");

            [
                result.quiz_title,
                `${result.score}/${result.total}`,
                `${result.percentage}%`,
                result.date
            ].forEach(value => {
                const cell = document.createElement("td");
                cell.textContent = value;
                row.appendChild(cell);
            });

            table.appendChild(row);
        });
    } catch (error) {
        showToast(error.message);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".nav-link").forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();
            showPage(link.dataset.page + "Page");
        });
    })

    $("previousBtn")?.addEventListener("click", previousQuestion);
    $("nextBtn")?.addEventListener("click", nextQuestion);
    $("submitBtn")?.addEventListener("click", () => submitQuiz());

    $("backDashboardBtn")?.addEventListener("click", () => {
        showPage("dashboardPage");
    });

    $("viewAllBtn")?.addEventListener("click", () => {
        showPage("allQuizzesPage");
    });

    loadQuizzes();
});

