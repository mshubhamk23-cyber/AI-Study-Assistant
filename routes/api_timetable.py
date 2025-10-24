import os
from flask import Blueprint, request, jsonify, current_app, session, send_file
from services.timetable_agent import TimetableAgentSystem
from bson.objectid import ObjectId
from io import BytesIO

api_timetable = Blueprint("api_timetable", __name__)

def _guard_json():
    if not session.get("user_id"):
        return jsonify({"error": "Unauthorized"}), 401

def _agent():
    return TimetableAgentSystem(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    )

@api_timetable.route("/api/timetable/extract_topics", methods=["POST"])
def extract_topics():
    g = _guard_json()
    if g: return g

    data = request.get_json(force=True)
    subject_id = data.get("subject_id")
    scope = data.get("scope", "").strip()

    if not subject_id:
        return jsonify({"error": "subject_id required"}), 400

    # Fetch subject & its documents (adjust to your schema)
    subject = current_app.db.subjects.find_one({"_id": ObjectId(subject_id)})
    if not subject:
        return jsonify({"error": "Subject not found"}), 404

    docs = []
    for d in subject.get("documents", []):
        # expected fields: storage_path, filename, _id
        if isinstance(d, dict) and "storage_path" in d and "filename" in d:
            docs.append({
                "storage_path": d["storage_path"],
                "filename": d["filename"],
                "_id": str(d.get("_id", "")) or d.get("id", "")
            })

    agent = _agent()
    upload_folder = os.getenv("UPLOAD_FOLDER", "uploads")
    topics = agent.extract_topics_from_documents(docs, upload_folder, scope)

    return jsonify({"extraction_results": topics})

@api_timetable.route("/api/timetable/generate", methods=["POST"])
def generate():
    g = _guard_json()
    if g: return g

    data = request.get_json(force=True)
    subject_id = data.get("subject_id")
    extracted_topics = data.get("extracted_topics")  # pass-through of previous API result
    timeframe = data.get("timeframe")

    if not (subject_id and extracted_topics and timeframe):
        return jsonify({"error": "subject_id, extracted_topics, timeframe required"}), 400

    # Get recent journal entries for the user (adjust to your schema)
    user_id = session.get("user_id")
    journal_entries = list(current_app.db.journals.find({"user_id": user_id}).sort("created_at", -1).limit(50))
    for j in journal_entries:
        j["_id"] = str(j["_id"])

    agent = _agent()
    plan = agent.generate_timetable(extracted_topics, journal_entries, timeframe)

    # Optionally include commitments used (from analyze_journal_entries) if your agent returns them
    # Here we just return whatever the agent produced.
    return jsonify({"timetable_results": plan})

@api_timetable.route("/api/timetable/download", methods=["POST"])
def download():
    g = _guard_json()
    if g: return g

    data = request.get_json(force=True)
    timetable_data = data.get("timetable_data")
    subject = data.get("subject", {})
    if not timetable_data:
        return jsonify({"error": "timetable_data required"}), 400

    agent = _agent()
    ics_bytes = agent.generate_ics_calendar(timetable_data)

    subject_name = (subject.get("name") or "Study").replace(" ", "_")
    file_name = f"{subject_name}_Timetable.ics"

    return send_file(BytesIO(ics_bytes),
                     mimetype="text/calendar",
                     as_attachment=True,
                     download_name=file_name)
