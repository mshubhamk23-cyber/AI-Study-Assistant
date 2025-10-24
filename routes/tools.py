# from flask import Blueprint, render_template, session, redirect, url_for

# tools = Blueprint("tools", __name__)

# def _guard():
#     if not session.get("user_id"):
#         return redirect(url_for("auth.login"))

# @tools.route("/summarize")
# def summarize():
#     g = _guard()
#     if g: return g
#     return render_template("tool_page.html", title="Summarizing the result", desc="Paste content and get a concise summary.")

# @tools.route("/timetable")
# def timetable():
#     g = _guard()
#     if g: return g
#     return render_template("tool_page.html", title="Smart timetable generator", desc="Generate a personalized study schedule.")

# @tools.route("/notes")
# def notes():
#     g = _guard()
#     if g: return g
#     return render_template("tool_page.html", title="Notes Q&A", desc="Ask questions over your notes and get answers.")

# @tools.route("/assignments")
# def assignments():
#     g = _guard()
#     if g: return g
#     return render_template("tool_page.html", title="Assignment tracker", desc="Track deadlines and progress.")

# @tools.route("/exam")
# def exam():
#     g = _guard()
#     if g: return g
#     return render_template("tool_page.html", title="Exam prep quiz", desc="Quick quizzes to prepare for exams.")

from flask import Blueprint, render_template, session, redirect, url_for, current_app

tools = Blueprint("tools", __name__)

def _guard():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

@tools.route("/summarize")
def summarize():
    g = _guard()
    if g: return g
    return render_template("tool_page.html", title="Summarizing the result", desc="Paste content and get a concise summary.")

@tools.route("/timetable")
def timetable():
    g = _guard()
    if g: return g

    # Example subjects from DB. Adapt to your schema.
    subjects = list(current_app.db.subjects.find({}, {"name": 1, "documents": 1}))
    for s in subjects:
        s["_id"] = str(s["_id"])
        s["documents"] = s.get("documents", []) or []
    return render_template("tools/timetable.html", subjects=subjects)

@tools.route("/notes")
def notes():
    g = _guard()
    if g: return g
    return render_template("tool_page.html", title="Notes Q&A", desc="Ask questions over your notes.")

@tools.route("/assignments")
def assignments():
    g = _guard()
    if g: return g
    return render_template("tool_page.html", title="Assignment tracker", desc="Track deadlines and progress.")

@tools.route("/exam")
def exam():
    g = _guard()
    if g: return g
    return render_template("tool_page.html", title="Exam prep quiz", desc="Quick quizzes to prepare for exams.")
