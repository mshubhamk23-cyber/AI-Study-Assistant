# # # routes/subjects.py
# # import os
# # import re
# # from io import BytesIO
# # from typing import List, Dict, Any
# # from bson.objectid import ObjectId

# # from flask import (
# #     Blueprint, render_template, request, redirect, url_for,
# #     current_app, session, jsonify, flash
# # )
# # from werkzeug.utils import secure_filename

# # # Use your existing text extractors/chunker
# # from services.document_processor import prepare_document_for_indexing

# # # Optional: try the OpenAI SDK; fall back to requests if not installed
# # try:
# #     from openai import OpenAI
# #     _HAS_OPENAI = True
# # except Exception:
# #     import requests
# #     _HAS_OPENAI = False

# # subjects_bp = Blueprint("subjects_bp", __name__, url_prefix="/subjects")

# # ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md", ".markdown"}

# # def _require_login():
# #     if not session.get("user_id"):
# #         return redirect(url_for("auth.login"))

# # def _ensure_indexes(db):
# #     # text index for retrieval; compound with subject_id for fast filtering
# #     try:
# #         db.subject_chunks.create_index([("subject_id", 1)])
# #         db.subject_chunks.create_index([("content", "text")])
# #     except Exception:
# #         pass

# # def _allowed_file(filename: str) -> bool:
# #     return os.path.splitext(filename.lower())[1] in ALLOWED_EXTS

# # def _uploads_dir(subject_id: str) -> str:
# #     base = current_app.config.get("UPLOAD_FOLDER", "uploads")
# #     path = os.path.join(base, subject_id)
# #     os.makedirs(path, exist_ok=True)
# #     return path

# # # ---------- PAGES ----------

# # @subjects_bp.get("/")
# # def list_subjects():
# #     if not session.get("user_id"):
# #         return redirect(url_for("auth.login"))

# #     db = current_app.db
# #     subjects = list(db.subjects.find({}, {"name": 1, "documents": 1}).sort("name", 1))
# #     for s in subjects:
# #         s["_id"] = str(s["_id"])
# #         s["documents"] = s.get("documents", []) or []
# #     return render_template("subjects.html", subjects=subjects)

# # @subjects_bp.post("/add")
# # def add_subject():
# #     if not session.get("user_id"):
# #         return redirect(url_for("auth.login"))

# #     name = (request.form.get("subject_name") or "").strip()
# #     if not name:
# #         flash("Please enter a subject name.", "error")
# #         return redirect(url_for("subjects_bp.list_subjects"))

# #     db = current_app.db
# #     # prevent duplicates by name (optional)
# #     exists = db.subjects.find_one({"name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}})
# #     if exists:
# #         flash("Subject already exists.", "error")
# #         return redirect(url_for("subjects_bp.list_subjects"))

# #     res = db.subjects.insert_one({"name": name, "documents": []})
# #     flash("Subject created.", "success")
# #     return redirect(url_for("subjects_bp.subject_detail", subject_id=str(res.inserted_id)))

# # @subjects_bp.get("/<subject_id>")
# # def subject_detail(subject_id):
# #     if not session.get("user_id"):
# #         return redirect(url_for("auth.login"))

# #     db = current_app.db
# #     subj = db.subjects.find_one({"_id": ObjectId(subject_id)})
# #     if not subj:
# #         flash("Subject not found.", "error")
# #         return redirect(url_for("subjects_bp.list_subjects"))

# #     subj["_id"] = str(subj["_id"])
# #     docs = subj.get("documents", []) or []
# #     return render_template("subject_detail.html", subject=subj, documents=docs)

# # # ---------- UPLOAD ----------

# # @subjects_bp.post("/<subject_id>/upload")
# # def upload_files(subject_id):
# #     if not session.get("user_id"):
# #         return redirect(url_for("auth.login"))

# #     db = current_app.db
# #     subj = db.subjects.find_one({"_id": ObjectId(subject_id)})
# #     if not subj:
# #         flash("Subject not found.", "error")
# #         return redirect(url_for("subjects_bp.list_subjects"))

# #     _ensure_indexes(db)

# #     files = request.files.getlist("files")
# #     if not files:
# #         flash("No files selected.", "error")
# #         return redirect(url_for("subjects_bp.subject_detail", subject_id=subject_id))

# #     saved_docs = []
# #     base_dir = _uploads_dir(subject_id)

# #     for f in files:
# #         if not f or not f.filename:
# #             continue

# #         if not _allowed_file(f.filename):
# #             flash(f"Unsupported file type: {f.filename}", "error")
# #             continue

# #         safe_name = secure_filename(f.filename)
# #         save_path = os.path.join(base_dir, safe_name)
# #         f.save(save_path)

# #         # Append to subject's doc list
# #         doc_rec = {"filename": safe_name, "storage_path": f"{subject_id}/{safe_name}"}
# #         saved_docs.append(doc_rec)

# #         # Index chunks
# #         chunks = prepare_document_for_indexing(
# #             doc_info={"_id": str(ObjectId()), "filename": safe_name, "subject_id": subject_id},
# #             subject_name=subj["name"],
# #             file_path=save_path
# #         )
# #         # Attach subject_id to each chunk so we can filter
# #         for c in chunks:
# #             c["subject_id"] = subject_id
# #         if chunks:
# #             db.subject_chunks.insert_many(chunks)

# #     if saved_docs:
# #         db.subjects.update_one(
# #             {"_id": ObjectId(subject_id)},
# #             {"$push": {"documents": {"$each": saved_docs}}}
# #         )
# #         flash(f"Uploaded {len(saved_docs)} file(s).", "success")
# #     else:
# #         flash("No files were uploaded.", "error")

# #     return redirect(url_for("subjects_bp.subject_detail", subject_id=subject_id))

# # # ---------- JSON APIs ----------

# # @subjects_bp.get("/api")
# # def api_get_all():
# #     if not session.get("user_id"):
# #         return jsonify({"error": "Unauthorized"}), 401

# #     db = current_app.db
# #     subjects = list(db.subjects.find({}, {"name": 1, "documents": 1}).sort("name", 1))
# #     for s in subjects:
# #         s["_id"] = str(s["_id"])
# #     return jsonify(subjects)

# # @subjects_bp.get("/api/<subject_id>")
# # def api_get_one(subject_id):
# #     if not session.get("user_id"):
# #         return jsonify({"error": "Unauthorized"}), 401

# #     db = current_app.db
# #     subj = db.subjects.find_one({"_id": ObjectId(subject_id)})
# #     if not subj:
# #         return jsonify({"error": "Not found"}), 404
# #     subj["_id"] = str(subj["_id"])
# #     return jsonify(subj)

# # # ---------- CHAT (retrieval-augmented) ----------

# # def _search_chunks(subject_id: str, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
# #     """
# #     Try full-text $text search first (requires text index).
# #     Fallback to case-insensitive regex if index not available.
# #     """
# #     db = current_app.db
# #     _ensure_indexes(db)

# #     try:
# #         # text score search
# #         cur = db.subject_chunks.find(
# #             {"subject_id": subject_id, "$text": {"$search": query}},
# #             {"score": {"$meta": "textScore"}, "content": 1, "document_name": 1}
# #         ).sort([("score", {"$meta": "textScore"})]).limit(top_k)
# #         res = list(cur)
# #         if res:
# #             return res
# #     except Exception:
# #         pass

# #     # Fallback: regex on content
# #     rx = re.compile(re.escape(query), re.IGNORECASE)
# #     res = list(
# #         db.subject_chunks.find(
# #             {"subject_id": subject_id, "content": {"$regex": rx}},
# #             {"content": 1, "document_name": 1}
# #         ).limit(top_k)
# #     )
# #     return res

# # def _build_context(chunks: List[Dict[str, Any]], max_chars: int = 4000) -> str:
# #     out = []
# #     size = 0
# #     for i, ch in enumerate(chunks, start=1):
# #         piece = ch.get("content", "") or ""
# #         name = ch.get("document_name", "doc")
# #         head = f"[{i}] {name}\n"
# #         take = max_chars - size - len(head)
# #         if take <= 0:
# #             break
# #         snippet = piece[:take]
# #         out.append(head + snippet)
# #         size += len(head) + len(snippet)
# #         if size >= max_chars:
# #             break
# #     return "\n\n".join(out)

# # def _openai_chat(messages: List[Dict[str, str]], model: str) -> str:
# #     api_key = os.getenv("OPENAI_API_KEY")
# #     if not api_key:
# #         return "OpenAI key not configured."

# #     if _HAS_OPENAI:
# #         client = OpenAI(api_key=api_key)
# #         resp = client.chat.completions.create(model=model, messages=messages, temperature=0.2)
# #         return resp.choices[0].message.content.strip()
# #     else:
# #         # Fallback via requests
# #         import requests
# #         headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
# #         payload = {"model": model, "messages": messages, "temperature": 0.2}
# #         r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
# #         r.raise_for_status()
# #         data = r.json()
# #         return data["choices"][0]["message"]["content"].strip()

# # @subjects_bp.post("/api/<subject_id>/chat")
# # def api_chat_subject(subject_id):
# #     if not session.get("user_id"):
# #         return jsonify({"error": "Unauthorized"}), 401

# #     data = request.get_json(force=True, silent=True) or {}
# #     user_msg = (data.get("message") or "").strip()
# #     if not user_msg:
# #         return jsonify({"error": "Message required"}), 400

# #     db = current_app.db
# #     subj = db.subjects.find_one({"_id": ObjectId(subject_id)})
# #     if not subj:
# #         return jsonify({"error": "Subject not found"}), 404

# #     # retrieve
# #     hits = _search_chunks(subject_id, user_msg, top_k=8)
# #     context = _build_context(hits, max_chars=4000)

# #     model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# #     system_prompt = (
# #         "You are a helpful study assistant. Answer the user based ONLY on the provided subject context. "
# #         "If the answer is not in the context, say you don't have enough information from the uploaded materials.\n\n"
# #         "Context:\n" + (context or "[no context available]")
# #     )

# #     messages = [
# #         {"role": "system", "content": system_prompt},
# #         {"role": "user", "content": user_msg},
# #     ]

# #     try:
# #         answer = _openai_chat(messages, model=model)
# #         return jsonify({"answer": answer, "chunks_used": len(hits)})
# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500


# # routes/subjects.py
# import os
# import re
# from typing import List, Dict, Any
# from bson.objectid import ObjectId
# from flask import (
#     Blueprint, render_template, request, redirect, url_for,
#     current_app, session, jsonify, flash
# )
# from werkzeug.utils import secure_filename

# from services.document_processor import prepare_document_for_indexing

# try:
#     from openai import OpenAI
#     _HAS_OPENAI = True
# except Exception:
#     import requests
#     _HAS_OPENAI = False

# subjects_bp = Blueprint("subjects_bp", __name__, url_prefix="/subjects")

# ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md", ".markdown"}

# # ---------- helpers ----------

# def _current_user_oid():
#     """Return current user's ObjectId (or None if not logged in/invalid)."""
#     uid = session.get("user_id")
#     try:
#         return ObjectId(uid) if uid else None
#     except Exception:
#         return None

# def _login_required_redirect():
#     if not session.get("user_id"):
#         return redirect(url_for("auth.login"))

# def _uploads_dir(subject_id: str) -> str:
#     base = current_app.config.get("UPLOAD_FOLDER", "uploads")
#     path = os.path.join(base, subject_id)
#     os.makedirs(path, exist_ok=True)
#     return path

# def _allowed_file(filename: str) -> bool:
#     return os.path.splitext(filename.lower())[1] in ALLOWED_EXTS

# def _ensure_indexes(db):
#     """
#     Helpful indexes (safe to call repeatedly).
#     - Subjects: (owner_id, name_lc) for quick listing by owner and duplicate checks.
#     - Chunks: (owner_id, subject_id) and text index on content for retrieval.
#     """
#     try:
#         db.subjects.create_index([("owner_id", 1), ("name_lc", 1)])
#     except Exception:
#         pass
#     try:
#         db.subject_chunks.create_index([("owner_id", 1), ("subject_id", 1)])
#         db.subject_chunks.create_index([("content", "text")])
#     except Exception:
#         pass

# def _search_chunks(owner_id: ObjectId, subject_id: str, query: str, top_k: int = 8) -> List[Dict[str, Any]]:
#     """Try $text search first; fallback to regex. Always filter by owner + subject."""
#     db = current_app.db
#     _ensure_indexes(db)

#     try:
#         cur = db.subject_chunks.find(
#             {"owner_id": owner_id, "subject_id": subject_id, "$text": {"$search": query}},
#             {"score": {"$meta": "textScore"}, "content": 1, "document_name": 1}
#         ).sort([("score", {"$meta": "textScore"})]).limit(top_k)
#         res = list(cur)
#         if res:
#             return res
#     except Exception:
#         pass

#     rx = re.compile(re.escape(query), re.IGNORECASE)
#     return list(
#         db.subject_chunks.find(
#             {"owner_id": owner_id, "subject_id": subject_id, "content": {"$regex": rx}},
#             {"content": 1, "document_name": 1}
#         ).limit(top_k)
#     )

# def _build_context(chunks: List[Dict[str, Any]], max_chars: int = 4000) -> str:
#     out, size = [], 0
#     for i, ch in enumerate(chunks, start=1):
#         piece = ch.get("content") or ""
#         name = ch.get("document_name") or "doc"
#         head = f"[{i}] {name}\n"
#         take = max_chars - size - len(head)
#         if take <= 0: break
#         snippet = piece[:take]
#         out.append(head + snippet)
#         size += len(head) + len(snippet)
#         if size >= max_chars: break
#     return "\n\n".join(out)

# def _openai_chat(messages: List[Dict[str, str]], model: str) -> str:
#     api_key = os.getenv("OPENAI_API_KEY")
#     if not api_key:
#         return "OpenAI key not configured."

#     if _HAS_OPENAI:
#         client = OpenAI(api_key=api_key)
#         resp = client.chat.completions.create(model=model, messages=messages, temperature=0.2)
#         return resp.choices[0].message.content.strip()
#     else:
#         import requests
#         headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
#         payload = {"model": model, "messages": messages, "temperature": 0.2}
#         r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=60)
#         r.raise_for_status()
#         data = r.json()
#         return data["choices"][0]["message"]["content"].strip()

# # ---------- pages ----------

# @subjects_bp.get("/")
# def list_subjects():
#     if not session.get("user_id"):
#         return redirect(url_for("auth.login"))

#     owner_id = _current_user_oid()
#     if not owner_id:
#         return redirect(url_for("auth.login"))

#     db = current_app.db
#     _ensure_indexes(db)

#     subjects = list(
#         db.subjects.find(
#             {"owner_id": owner_id},
#             {"name": 1, "documents": 1}
#         ).sort("name_lc", 1)
#     )
#     for s in subjects:
#         s["_id"] = str(s["_id"])
#         s["documents"] = s.get("documents", []) or []
#     return render_template("subjects.html", subjects=subjects)

# @subjects_bp.post("/add")
# def add_subject():
#     if not session.get("user_id"):
#         return redirect(url_for("auth.login"))

#     owner_id = _current_user_oid()
#     if not owner_id:
#         return redirect(url_for("auth.login"))

#     name = (request.form.get("subject_name") or "").strip()
#     if not name:
#         flash("Please enter a subject name.", "error")
#         return redirect(url_for("subjects_bp.list_subjects"))

#     name_lc = name.lower()

#     db = current_app.db
#     _ensure_indexes(db)

#     # prevent duplicates per user
#     exists = db.subjects.find_one({"owner_id": owner_id, "name_lc": name_lc})
#     if exists:
#         flash("Subject already exists.", "error")
#         return redirect(url_for("subjects_bp.list_subjects"))

#     res = db.subjects.insert_one({
#         "owner_id": owner_id,
#         "name": name,
#         "name_lc": name_lc,
#         "documents": []
#     })
#     flash("Subject created.", "success")
#     return redirect(url_for("subjects_bp.subject_detail", subject_id=str(res.inserted_id)))

# @subjects_bp.get("/<subject_id>")
# def subject_detail(subject_id):
#     if not session.get("user_id"):
#         return redirect(url_for("auth.login"))

#     owner_id = _current_user_oid()
#     if not owner_id:
#         return redirect(url_for("auth.login"))

#     db = current_app.db
#     subj = db.subjects.find_one({"_id": ObjectId(subject_id), "owner_id": owner_id})
#     if not subj:
#         flash("Subject not found.", "error")
#         return redirect(url_for("subjects_bp.list_subjects"))

#     subj["_id"] = str(subj["_id"])
#     docs = subj.get("documents", []) or []
#     return render_template("subject_detail.html", subject=subj, documents=docs)

# # ---------- upload ----------

# @subjects_bp.post("/<subject_id>/upload")
# def upload_files(subject_id):
#     if not session.get("user_id"):
#         return redirect(url_for("auth.login"))

#     owner_id = _current_user_oid()
#     if not owner_id:
#         return redirect(url_for("auth.login"))

#     db = current_app.db
#     subj = db.subjects.find_one({"_id": ObjectId(subject_id), "owner_id": owner_id})
#     if not subj:
#         flash("Subject not found.", "error")
#         return redirect(url_for("subjects_bp.list_subjects"))

#     _ensure_indexes(db)

#     files = request.files.getlist("files")
#     if not files:
#         flash("No files selected.", "error")
#         return redirect(url_for("subjects_bp.subject_detail", subject_id=subject_id))

#     saved_docs = []
#     base_dir = _uploads_dir(subject_id)

#     for f in files:
#         if not f or not f.filename:
#             continue
#         if not _allowed_file(f.filename):
#             flash(f"Unsupported file type: {f.filename}", "error")
#             continue

#         safe_name = secure_filename(f.filename)
#         save_path = os.path.join(base_dir, safe_name)
#         f.save(save_path)

#         doc_rec = {"filename": safe_name, "storage_path": f"{subject_id}/{safe_name}"}
#         saved_docs.append(doc_rec)

#         # index chunks tagged with both subject_id and owner_id
#         chunks = prepare_document_for_indexing(
#             doc_info={"_id": str(ObjectId()), "filename": safe_name, "subject_id": subject_id},
#             subject_name=subj["name"],
#             file_path=save_path
#         )
#         for c in chunks:
#             c["subject_id"] = subject_id
#             c["owner_id"] = owner_id
#         if chunks:
#             db.subject_chunks.insert_many(chunks)

#     if saved_docs:
#         db.subjects.update_one(
#             {"_id": ObjectId(subject_id), "owner_id": owner_id},
#             {"$push": {"documents": {"$each": saved_docs}}}
#         )
#         flash(f"Uploaded {len(saved_docs)} file(s).", "success")
#     else:
#         flash("No files were uploaded.", "error")

#     return redirect(url_for("subjects_bp.subject_detail", subject_id=subject_id))

# # ---------- JSON APIs ----------

# @subjects_bp.get("/api")
# def api_get_all():
#     if not session.get("user_id"):
#         return jsonify({"error": "Unauthorized"}), 401
#     owner_id = _current_user_oid()
#     if not owner_id:
#         return jsonify({"error": "Unauthorized"}), 401

#     db = current_app.db
#     subs = list(db.subjects.find({"owner_id": owner_id}, {"name": 1, "documents": 1}).sort("name_lc", 1))
#     for s in subs:
#         s["_id"] = str(s["_id"])
#     return jsonify(subs)

# @subjects_bp.get("/api/<subject_id>")
# def api_get_one(subject_id):
#     if not session.get("user_id"):
#         return jsonify({"error": "Unauthorized"}), 401
#     owner_id = _current_user_oid()
#     if not owner_id:
#         return jsonify({"error": "Unauthorized"}), 401

#     db = current_app.db
#     subj = db.subjects.find_one({"_id": ObjectId(subject_id), "owner_id": owner_id})
#     if not subj:
#         return jsonify({"error": "Not found"}), 404
#     subj["_id"] = str(subj["_id"])
#     return jsonify(subj)

# # ---------- chat (RAG) ----------

# @subjects_bp.post("/api/<subject_id>/chat")
# def api_chat_subject(subject_id):
#     if not session.get("user_id"):
#         return jsonify({"error": "Unauthorized"}), 401
#     owner_id = _current_user_oid()
#     if not owner_id:
#         return jsonify({"error": "Unauthorized"}), 401

#     db = current_app.db
#     subj = db.subjects.find_one({"_id": ObjectId(subject_id), "owner_id": owner_id})
#     if not subj:
#         return jsonify({"error": "Subject not found"}), 404

#     data = request.get_json(force=True, silent=True) or {}
#     user_msg = (data.get("message") or "").strip()
#     if not user_msg:
#         return jsonify({"error": "Message required"}), 400

#     hits = _search_chunks(owner_id, subject_id, user_msg, top_k=8)
#     context = _build_context(hits, max_chars=4000)
#     model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

#     system_prompt = (
#         "You are a helpful study assistant. Answer the user based ONLY on the provided subject context. "
#         "If the answer is not in the context, say you don't have enough information from the uploaded materials.\n\n"
#         "Context:\n" + (context or "[no context available]")
#     )
#     messages = [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": user_msg},
#     ]

#     try:
#         answer = _openai_chat(messages, model=model)
#         return jsonify({"answer": answer, "chunks_used": len(hits)})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500




import os
import re
from typing import List, Dict, Any
from bson.objectid import ObjectId
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    current_app, session, jsonify, flash
)
from werkzeug.utils import secure_filename

# ✅ Use the new RAG/OCR service
from services.rag_services import (
    create_subject_index,
    index_new_files,
    answer_question_subject,
)

subjects_bp = Blueprint("subjects_bp", __name__, url_prefix="/subjects")

# Support more types (images for OCR as well)
ALLOWED_EXTS = {
    ".pdf", ".docx", ".txt", ".md", ".markdown",
    ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"
}

# ---------- helpers ----------

def _current_user_oid():
    """Return current user's ObjectId (or None if not logged in/invalid)."""
    uid = session.get("user_id")
    try:
        return ObjectId(uid) if uid else None
    except Exception:
        return None

def _login_required_redirect():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

def _uploads_dir(subject_id: str) -> str:
    base = current_app.config.get("UPLOAD_FOLDER", "uploads")
    path = os.path.join(base, subject_id)
    os.makedirs(path, exist_ok=True)
    return path

def _allowed_file(filename: str) -> bool:
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTS

def _ensure_indexes(db):
    """
    Helpful indexes (safe to call repeatedly).
    - Subjects: (owner_id, name_lc) for quick listing by owner and duplicate checks.
    """
    try:
        db.subjects.create_index([("owner_id", 1), ("name_lc", 1)])
    except Exception:
        pass

# ---------- pages ----------

@subjects_bp.get("/")
def list_subjects():
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    owner_id = _current_user_oid()
    if not owner_id:
        return redirect(url_for("auth.login"))

    db = current_app.db
    _ensure_indexes(db)

    subjects = list(
        db.subjects.find(
            {"owner_id": owner_id},
            {"name": 1, "documents": 1}
        ).sort("name_lc", 1)
    )
    for s in subjects:
        s["_id"] = str(s["_id"])
        s["documents"] = s.get("documents", []) or []
    return render_template("subjects.html", subjects=subjects)

@subjects_bp.post("/add")
def add_subject():
    """
    Create subject in Mongo (for UI) AND initialize its per-subject FAISS index.
    OCR + index any already-present files under uploads/<subject_id>/ if exist,
    otherwise create an empty index for this subject.
    """
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    owner_id = _current_user_oid()
    if not owner_id:
        return redirect(url_for("auth.login"))

    name = (request.form.get("subject_name") or "").strip()
    if not name:
        flash("Please enter a subject name.", "error")
        return redirect(url_for("subjects_bp.list_subjects"))

    name_lc = name.lower()

    db = current_app.db
    _ensure_indexes(db)

    # prevent duplicates per user
    exists = db.subjects.find_one({"owner_id": owner_id, "name_lc": name_lc})
    if exists:
        flash("Subject already exists.", "error")
        return redirect(url_for("subjects_bp.list_subjects"))

    res = db.subjects.insert_one({
        "owner_id": owner_id,
        "name": name,
        "name_lc": name_lc,
        "documents": [],
        "created_at": datetime.utcnow(),
    })

    subject_id = str(res.inserted_id)

    # ✅ Build (or empty-init) the FAISS index for this subject
    try:
        ix = create_subject_index(subject_id, name)
        if ix.get("created_empty"):
            flash("Subject created. (Vector DB initialized empty.)", "success")
        else:
            flash(f"Subject created. Indexed {ix.get('chunks_indexed', 0)} chunks.", "success")
    except Exception as e:
        current_app.logger.exception("Failed to initialize subject index")
        flash(f"Subject created, but index initialization failed: {e}", "error")

    return redirect(url_for("subjects_bp.subject_detail", subject_id=subject_id))

@subjects_bp.get("/<subject_id>")
def subject_detail(subject_id):
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    owner_id = _current_user_oid()
    if not owner_id:
        return redirect(url_for("auth.login"))

    db = current_app.db
    subj = db.subjects.find_one({"_id": ObjectId(subject_id), "owner_id": owner_id})
    if not subj:
        flash("Subject not found.", "error")
        return redirect(url_for("subjects_bp.list_subjects"))

    subj["_id"] = str(subj["_id"])
    docs = subj.get("documents", []) or []
    return render_template("subject_detail.html", subject=subj, documents=docs)

# ---------- upload ----------

@subjects_bp.post("/<subject_id>/upload")
def upload_files(subject_id):
    """
    Save files to uploads/<subject_id>/ and incrementally OCR + append to this subject's FAISS index.
    """
    if not session.get("user_id"):
        return redirect(url_for("auth.login"))

    owner_id = _current_user_oid()
    if not owner_id:
        return redirect(url_for("auth.login"))

    db = current_app.db
    subj = db.subjects.find_one({"_id": ObjectId(subject_id), "owner_id": owner_id})
    if not subj:
        flash("Subject not found.", "error")
        return redirect(url_for("subjects_bp.list_subjects"))

    _ensure_indexes(db)

    files = request.files.getlist("files")
    if not files:
        flash("No files selected.", "error")
        return redirect(url_for("subjects_bp.subject_detail", subject_id=subject_id))

    saved_docs = []
    saved_paths = []
    base_dir = _uploads_dir(subject_id)

    for f in files:
        if not f or not f.filename:
            continue
        if not _allowed_file(f.filename):
            flash(f"Unsupported file type: {f.filename}", "error")
            continue

        safe_name = secure_filename(f.filename)
        save_path = os.path.join(base_dir, safe_name)
        f.save(save_path)

        saved_docs.append({
            "_id": ObjectId(),
            "filename": safe_name,
            "storage_path": f"{subject_id}/{safe_name}",
            "uploaded_at": datetime.utcnow(),
        })
        saved_paths.append(save_path)

    if saved_docs:
        # store file metadata for UI
        db.subjects.update_one(
            {"_id": ObjectId(subject_id), "owner_id": owner_id},
            {"$push": {"documents": {"$each": saved_docs}}}
        )
        # ✅ OCR + append to this subject's vector DB
        try:
            ix_res = index_new_files(subject_id, subj["name"], saved_paths)
            flash(
                f"Uploaded {len(saved_docs)} file(s). "
                f"Indexed {ix_res.get('chunks_added', 0)} new chunks into {subj['name']}.",
                "success"
            )
        except Exception as e:
            current_app.logger.exception("Index append failed")
            flash(f"Files saved, but indexing failed: {e}", "error")
    else:
        flash("No files were uploaded.", "error")

    return redirect(url_for("subjects_bp.subject_detail", subject_id=subject_id))

# ---------- JSON APIs ----------

@subjects_bp.get("/api")
def api_get_all():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401
    owner_id = _current_user_oid()
    if not owner_id:
        return jsonify({"error": "Unauthorized"}), 401

    db = current_app.db
    subs = list(db.subjects.find({"owner_id": owner_id}, {"name": 1, "documents": 1}).sort("name_lc", 1))
    for s in subs:
        s["_id"] = str(s["_id"])
    return jsonify(subs)

@subjects_bp.get("/api/<subject_id>")
def api_get_one(subject_id):
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401
    owner_id = _current_user_oid()
    if not owner_id:
        return jsonify({"error": "Unauthorized"}), 401

    db = current_app.db
    subj = db.subjects.find_one({"_id": ObjectId(subject_id), "owner_id": owner_id})
    if not subj:
        return jsonify({"error": "Not found"}), 404
    subj["_id"] = str(subj["_id"])
    return jsonify(subj)

# ---------- chat (RAG via per-subject FAISS) ----------

@subjects_bp.post("/api/<subject_id>/chat")
def api_chat_subject(subject_id):
    """
    Answer strictly from the FAISS index for this subject.
    If nothing relevant, returns: "I don't know based on your materials."
    """
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401
    owner_id = _current_user_oid()
    if not owner_id:
        return jsonify({"error": "Unauthorized"}), 401

    db = current_app.db
    subj = db.subjects.find_one({"_id": ObjectId(subject_id), "owner_id": owner_id})
    if not subj:
        return jsonify({"error": "Subject not found"}), 404

    data = request.get_json(force=True, silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    if not user_msg:
        return jsonify({"error": "Message required"}), 400

    try:
        # ✅ Use per-subject FAISS index (no Mongo text search)
        res = answer_question_subject(subject_id, user_msg)
        # Keep response shape similar to your old API
        out = {
            "answer": res.get("answer") or "I don't know based on your materials.",
            "mode": res.get("mode", "offline"),
            "sources": res.get("sources", []),
            "chunks_used": len(res.get("sources", [])),
        }
        return jsonify(out)
    except Exception as e:
        current_app.logger.exception("Subject chat failed")
        return jsonify({"error": str(e)}), 500
