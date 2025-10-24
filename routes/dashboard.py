# routes/dashboard.py
from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, current_app, render_template, session, redirect, url_for

dashboard_bp = Blueprint("dashboard_bp", __name__)

def _oid():
    uid = session.get("user_id")
    try:
        return ObjectId(uid) if uid else None
    except Exception:
        return None

def _fmt(dtobj):
    if isinstance(dtobj, datetime):
        return dtobj.strftime("%b %d, %Y %I:%M %p")
    return None

@dashboard_bp.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    owner_id = _oid()
    if not owner_id:
        return redirect(url_for("auth.login"))

    db = current_app.db

    subjects_view = []
    cursor = db.subjects.find(
        {"owner_id": owner_id},
        {"name": 1, "documents": 1, "created_at": 1}
    ).sort([("name", 1)])

    for s in cursor:
        # Subject created_at: prefer explicit, else _id timestamp
        created_at = s.get("created_at")
        if not isinstance(created_at, datetime):
            created_at = s["_id"].generation_time  # Mongo ObjectId embeds time (UTC)

        docs = []
        latest = created_at

        for d in (s.get("documents") or []):
            fname = d.get("filename") or "file"
            uploaded_at = d.get("uploaded_at")
            # fallbacks: try ObjectId in docs (if you stored one), else subject creation time
            if not isinstance(uploaded_at, datetime):
                did = d.get("_id") or d.get("id")
                try:
                    uploaded_at = ObjectId(str(did)).generation_time
                except Exception:
                    uploaded_at = created_at
            if uploaded_at and uploaded_at > latest:
                latest = uploaded_at

            docs.append({
                "filename": fname,
                "uploaded_str": _fmt(uploaded_at) or "—"
            })

        subjects_view.append({
            "_id": str(s["_id"]),
            "name": s.get("name", "Untitled"),
            "created_str": _fmt(created_at) or "—",
            "last_updated_str": _fmt(latest) or "—",
            "files_count": len(docs),
            "files": docs
        })

    full_name = session.get("full_name", "Student")
    return render_template("dashboard.html",
                           full_name=full_name,
                           subjects=subjects_view)
