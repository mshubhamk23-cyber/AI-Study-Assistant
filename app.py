# import os
# from datetime import timedelta
# from flask import Flask, render_template, redirect, url_for, session
# from dotenv import load_dotenv
# from db.mongo import init_db
# from routes.auth import auth
# from routes.tools import tools
# from routes.api_timetable import api_timetable
# from routes.subjects import subjects_bp

# load_dotenv()

# def create_app():
#     app = Flask(__name__)
#     app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
#     app.permanent_session_lifetime = timedelta(days=30)

#     # DB
#     db = init_db()
#     app.db = db

#     # Blueprints
#     app.register_blueprint(auth)
#     app.register_blueprint(tools, url_prefix="/tools") 
#     app.register_blueprint(api_timetable)
#     app.register_blueprint(subjects_bp) 

#     @app.route("/")
#     def index():
#         if session.get("user_id"):
#             return redirect(url_for("dashboard"))
#         return redirect(url_for("auth.login"))

#     @app.route("/dashboard")
#     def dashboard():
#         if not session.get("user_id"):
#             return redirect(url_for("auth.login"))
#         return render_template("dashboard.html", full_name=session.get("full_name"))

#     return app

# if __name__ == "__main__":
#     app = create_app()
#     app.run(debug=True)

#Final revised code:

# import os
# from datetime import timedelta, datetime
# from bson.objectid import ObjectId

# from flask import (
#     Flask, render_template, redirect, url_for, session, current_app
# )
# from dotenv import load_dotenv

# from db.mongo import init_db
# from routes.auth import auth
# from routes.tools import tools
# from routes.api_timetable import api_timetable
# from routes.subjects import subjects_bp

# load_dotenv()

# def create_app():
#     app = Flask(__name__)
#     app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
#     app.permanent_session_lifetime = timedelta(days=30)

#     # DB
#     db = init_db()
#     app.db = db

#     # Blueprints
#     app.register_blueprint(auth)
#     app.register_blueprint(tools, url_prefix="/tools")
#     app.register_blueprint(api_timetable)
#     app.register_blueprint(subjects_bp)

#     @app.route("/")
#     def index():
#         if session.get("user_id"):
#             return redirect(url_for("dashboard"))
#         return redirect(url_for("auth.login"))

#     @app.route("/dashboard")
#     def dashboard():
#         if not session.get("user_id"):
#             return redirect(url_for("auth.login"))

#         # Parse current user ObjectId safely
#         try:
#             owner_id = ObjectId(session["user_id"])
#         except Exception:
#             return redirect(url_for("auth.login"))

#         db = current_app.db

#         subjects_view = []
#         cursor = db.subjects.find(
#             {"owner_id": owner_id},
#             {"name": 1, "documents": 1, "created_at": 1}
#         ).sort([("name", 1)])

#         def fmt(dtobj):
#             if isinstance(dtobj, datetime):
#                 return dtobj.strftime("%b %d, %Y %I:%M %p")
#             return "—"

#         for s in cursor:
#             # Subject created time: explicit or fallback to ObjectId time
#             created_at = s.get("created_at")
#             if not isinstance(created_at, datetime):
#                 created_at = s["_id"].generation_time  # UTC

#             docs = []
#             latest = created_at

#             for d in (s.get("documents") or []):
#                 fname = d.get("filename") or "file"
#                 uploaded_at = d.get("uploaded_at")
#                 if not isinstance(uploaded_at, datetime):
#                     # Try fallback to the document's ObjectId timestamp if present
#                     did = d.get("_id") or d.get("id")
#                     try:
#                         uploaded_at = ObjectId(str(did)).generation_time
#                     except Exception:
#                         uploaded_at = created_at
#                 if uploaded_at and uploaded_at > latest:
#                     latest = uploaded_at

#                 docs.append({
#                     "filename": fname,
#                     "uploaded_str": fmt(uploaded_at),
#                 })

#             subjects_view.append({
#                 "_id": str(s["_id"]),
#                 "name": s.get("name", "Untitled"),
#                 "created_str": fmt(created_at),
#                 "last_updated_str": fmt(latest),
#                 "files_count": len(docs),
#                 "files": docs,
#             })

#         return render_template(
#             "dashboard.html",
#             full_name=session.get("full_name", "Student"),
#             subjects=subjects_view,
#         )

#     return app


# if __name__ == "__main__":
#     app = create_app()
#     app.run(debug=True)


import os
from datetime import timedelta, datetime
from bson.objectid import ObjectId

from flask import (
    Flask, render_template, redirect, url_for, session, current_app, jsonify
)
from dotenv import load_dotenv

from db.mongo import init_db
from routes.auth import auth
from routes.tools import tools
from routes.api_timetable import api_timetable
from routes.subjects import subjects_bp

# ⬇️ optional: show service config on /health
try:
    from services.rag_services import get_config_snapshot
except Exception:
    get_config_snapshot = None

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
    app.permanent_session_lifetime = timedelta(days=30)

    # ===== App Config (important) =====
    # Make sure this matches what services/rag_service.py expects.
    # In rag_service.py, UPLOADS_ROOT defaults to os.getenv("UPLOAD_FOLDER", "uploads")
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)  # ensure exists

    # DB
    db = init_db()
    app.db = db

    # Blueprints
    app.register_blueprint(auth)
    app.register_blueprint(tools, url_prefix="/tools")
    app.register_blueprint(api_timetable)
    app.register_blueprint(subjects_bp)

    @app.route("/health")
    def health():
        """Optional: quick status of vector/LLM settings."""
        cfg = get_config_snapshot() if get_config_snapshot else {}
        return jsonify({"ok": True, "cfg": cfg})

    @app.route("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("auth.login"))

    @app.route("/dashboard")
    def dashboard():
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))

        # Parse current user ObjectId safely
        try:
            owner_id = ObjectId(session["user_id"])
        except Exception:
            return redirect(url_for("auth.login"))

        db = current_app.db

        subjects_view = []
        cursor = db.subjects.find(
            {"owner_id": owner_id},
            {"name": 1, "documents": 1, "created_at": 1}
        ).sort([("name", 1)])

        def fmt(dtobj):
            if isinstance(dtobj, datetime):
                return dtobj.strftime("%b %d, %Y %I:%M %p")
            return "—"

        for s in cursor:
            # Subject created time: explicit or fallback to ObjectId time
            created_at = s.get("created_at")
            if not isinstance(created_at, datetime):
                created_at = s["_id"].generation_time  # UTC

            docs = []
            latest = created_at

            for d in (s.get("documents") or []):
                fname = d.get("filename") or "file"
                uploaded_at = d.get("uploaded_at")
                if not isinstance(uploaded_at, datetime):
                    # Try fallback to the document's ObjectId timestamp if present
                    did = d.get("_id") or d.get("id")
                    try:
                        uploaded_at = ObjectId(str(did)).generation_time
                    except Exception:
                        uploaded_at = created_at
                if uploaded_at and uploaded_at > latest:
                    latest = uploaded_at

                docs.append({
                    "filename": fname,
                    "uploaded_str": fmt(uploaded_at),
                })

            subjects_view.append({
                "_id": str(s["_id"]),
                "name": s.get("name", "Untitled"),
                "created_str": fmt(created_at),
                "last_updated_str": fmt(latest),
                "files_count": len(docs),
                "files": docs,
            })

        return render_template(
            "dashboard.html",
            full_name=session.get("full_name", "Student"),
            subjects=subjects_view,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    # Set host/port via env if you like
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "8000"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
