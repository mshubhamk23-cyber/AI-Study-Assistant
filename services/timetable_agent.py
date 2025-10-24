"""
timetable_agent.py - Multi-agent workflow for timetable generation feature (OpenAI API version)
"""

import logging
import os
import json
from typing import Dict, Any, List, Optional
import datetime
import calendar
import re
from .document_processor import extract_document_text
from .journal_util import JournalExtractor
import requests
from icalendar import Calendar, Event
from datetime import datetime as dt, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimetableAgentSystem:
    """Multi-agent system for timetable generation (OpenAI API version)"""

    def __init__(
        self,
        openai_api_key: str,
        openai_model: str = "gpt-4o-mini",
        openai_endpoint: str = "https://api.openai.com/v1",
        document_intelligence_endpoint: str = None,
        document_intelligence_key: str = None
    ):
        """
        Initialize the timetable agent system (OpenAI API)

        Args:
            openai_api_key: OpenAI API key (Bearer)
            openai_model: Chat model name (e.g., "gpt-4o-mini", "gpt-4.1")
            openai_endpoint: Base OpenAI API endpoint (default /v1)
            document_intelligence_endpoint: (optional) keep for compatibility
            document_intelligence_key: (optional) keep for compatibility
        """
        self.openai_api_key = openai_api_key
        self.openai_model = openai_model
        self.openai_endpoint = openai_endpoint.rstrip("/")
        self.document_intelligence_endpoint = document_intelligence_endpoint
        self.document_intelligence_key = document_intelligence_key

    # ----------------------------
    # OpenAI helper (JSON output)
    # ----------------------------
    def _chat_json(
        self,
        system_message: str,
        user_message: str,
        *,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: int = 60
    ) -> dict:
        """
        Call OpenAI Chat Completions and return parsed JSON.
        Uses response_format={"type":"json_object"} to force valid JSON.
        """
        url = f"{self.openai_endpoint}/chat/completions"

        payload = {
            "model": self.openai_model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_api_key}",
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # Guaranteed JSON because of response_format
        return json.loads(content)

    # ---------------------------------------
    # Agent 1: Topic extraction from documents
    # ---------------------------------------
    def extract_topics_from_documents(
        self,
        documents: List[Dict[str, Any]],
        upload_folder: str,
        scope: str
    ) -> Dict[str, Any]:
        """
        Extract topics from uploaded documents based on user scope.
        """
        logger.info(f"Extracting topics from {len(documents)} documents with scope: {scope}")

        all_document_text = []
        documents_info = []

        for doc in documents:
            try:
                file_path = os.path.join(upload_folder, doc["storage_path"])
                filename = doc["filename"]

                doc_info = {"filename": filename, "id": doc["_id"]}

                document_text = extract_document_text(file_path)
                if document_text:
                    all_document_text.append({
                        "filename": filename,
                        "text": document_text[:10000],  # limit size
                        "info": doc_info,
                    })
                documents_info.append(doc_info)
            except Exception as e:
                logger.error(f"Error processing document {doc.get('filename','unknown')}: {e}")

        extracted_topics = self._extract_topics_with_ai(all_document_text, scope)

        return {
            "documents": documents_info,
            "topics": extracted_topics,  # { main_topics, subtopics, key_terms }
            "extraction_timestamp": datetime.datetime.utcnow().isoformat(),
            "scope": scope,
        }

    def _extract_topics_with_ai(self, document_texts: List[Dict[str, Any]], scope: str) -> Dict[str, Any]:
        """
        Call OpenAI to extract main topics, subtopics, and key terms.
        """
        if not document_texts:
            logger.warning("No document texts provided for topic extraction")
            return {
                "main_topics": ["No documents provided"],
                "subtopics": {},
                "key_terms": {},
                "error": "No document content available",
            }

        # Concatenate document samples
        combined_text = ""
        for doc in document_texts:
            sample = doc["text"][:5000]
            if len(doc["text"]) > 5000:
                sample += "..."
            combined_text += f"\n\n## Document: {doc['filename']}\n{sample}"

        system_message = """
        You are a Topic Extraction Agent specialized in educational content.
        Return a JSON object with:
          - main_topics: string[]
          - subtopics: { [main_topic: string]: string[] }
          - key_terms: { [main_topic: string]: string[] }
        Focus on the provided scope and keep lists concise but relevant.
        """
        user_message = f"""
        USER SCOPE: {scope}

        DOCUMENT CONTENT:
        {combined_text}
        """

        try:
            return self._chat_json(system_message, user_message, max_tokens=2000, temperature=0.3)
        except Exception as e:
            logger.error(f"OpenAI topic extraction error: {e}")
            return {
                "main_topics": ["Error in topic extraction"],
                "subtopics": {},
                "key_terms": {},
                "error": str(e),
            }

    # -----------------------------------------
    # Agent 3: Analyze journal for commitments
    # -----------------------------------------
    def analyze_journal_entries(self, journal_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract structured time commitments from journal entries.
        """
        logger.info(f"Analyzing {len(journal_entries) if journal_entries else 0} journal entries for commitments")

        if not journal_entries:
            return {
                "commitments": [],
                "analysis_timestamp": datetime.datetime.utcnow().isoformat(),
                "message": "No journal entries provided for analysis",
            }

        journal_context = JournalExtractor.get_memory_context(journal_entries, max_entries=30)

        system_message = """
        You are a Journal Analysis Agent. Identify concrete time-specific commitments.
        Return JSON:
        {
          "commitments": [
            {
              "description": string,
              "date": "YYYY-MM-DD" | null,
              "start_time": "HH:MM" | null,
              "end_time": "HH:MM" | null,
              "duration": number | null,
              "priority": "high" | "medium" | "low",
              "location": string | null,
              "notes": string | null
            }
          ]
        }
        Only include items with a specific date. Use null where details are unknown.
        Today's date for inference: {today}
        """.format(today=datetime.datetime.now().strftime("%Y-%m-%d"))

        user_message = f"JOURNAL ENTRIES:\n{journal_context}"

        try:
            result = self._chat_json(system_message, user_message, max_tokens=2000, temperature=0.3)
            result["analysis_timestamp"] = datetime.datetime.utcnow().isoformat()
            return result
        except Exception as e:
            logger.error(f"OpenAI journal analysis error: {e}")
            return {"error": str(e), "commitments": [], "message": "Error analyzing journal entries."}

    # -------------------------------------------------
    # Orchestrator: run analysis + generate timetable
    # -------------------------------------------------
    def generate_timetable(
        self,
        extracted_topics: Dict[str, Any],
        journal_entries: List[Dict[str, Any]],
        timeframe: str
    ) -> Dict[str, Any]:
        """
        Full workflow:
          1) Analyze journals -> commitments
          2) Parse timeframe -> start/end
          3) Generate timetable -> conflict-aware
        """
        logger.info("Starting multi-agent timetable generation workflow")

        try:
            # 1) Analyze journal entries
            commitments_data = self.analyze_journal_entries(journal_entries)

            # 2) Calculate study timeframe (start tomorrow)
            start_date = datetime.datetime.now() + datetime.timedelta(days=1)
            timeframe_info = self._calculate_timeframe(timeframe, start_date)

            # 3) Generate timetable
            timetable_data = self._generate_timetable_with_conflicts(
                extracted_topics=extracted_topics,
                commitments_data=commitments_data,
                timeframe=timeframe,
                timeframe_info=timeframe_info,
            )
            return timetable_data

        except Exception as e:
            logger.error(f"Error in timetable generation workflow: {e}")
            return {
                "error": str(e),
                "timetable": [],
                "overview": "There was an error generating your timetable.",
            }

    # --------------------------------------
    # Date parsing for natural timeframe text
    # --------------------------------------
    def _calculate_timeframe(self, timeframe_text: str, start_date: datetime.datetime) -> Dict[str, Any]:
        """
        Convert natural timeframe text to start/end/duration (days).
        """
        default_days = 7
        try:
            system_message = """
            You convert natural language timeframes to durations.
            Return: { "days": integer } where 1 <= days <= 90.
            Examples: "next 2 weeks" -> {"days":14}, "3 days" -> {"days":3}, "by Friday" -> {"days":X}
            """
            user_message = f'TIMEFRAME: "{timeframe_text}"\nTODAY: {start_date.strftime("%Y-%m-%d")} ({start_date.strftime("%A")})'
            data = self._chat_json(system_message, user_message, max_tokens=200, temperature=0.0)
            days = int(data.get("days", default_days))
            days = min(max(1, days), 90)
        except Exception as e:
            logger.error(f"OpenAI timeframe parse error: {e}")
            days = default_days

        end_date = start_date + datetime.timedelta(days=days)
        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "duration_days": (end_date - start_date).days,
            "start_day_name": start_date.strftime("%A"),
            "end_day_name": end_date.strftime("%A"),
        }

    # ------------------------------------------
    # Agent 2: Generate timetable with conflicts
    # ------------------------------------------
    def _generate_timetable_with_conflicts(
        self,
        extracted_topics: Dict[str, Any],
        commitments_data: Dict[str, Any],
        timeframe: str,
        timeframe_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a study timetable using topics and commitments (JSON).
        """
        logger.info("Generating timetable with conflict awareness")

        try:
            # Handle potential structure:
            # extracted_topics might already be {main_topics, subtopics, key_terms}
            # or wrapped as {"topics": {...}}
            topics_obj = extracted_topics.get("topics", extracted_topics)
            topics_text = json.dumps(topics_obj, indent=2)

            commitments = commitments_data.get("commitments", [])
            commitments_text = json.dumps(commitments, indent=2)

            system_message = f"""
            You create a JSON study timetable.
            Start: {timeframe_info['start_date']} ({timeframe_info['start_day_name']})
            End:   {timeframe_info['end_date']} ({timeframe_info['end_day_name']})

            Avoid user's commitments; if a conflict is unavoidable, set has_conflict=true and explain in conflict_details.

            Return JSON:
            {{
              "timetable": [
                {{
                  "day": string,
                  "date": "YYYY-MM-DD",
                  "time": string,
                  "start_time": "HH:MM",
                  "end_time": "HH:MM",
                  "topics": string | string[],
                  "activities": string | string[],
                  "duration": number,
                  "priority": "high" | "medium" | "low",
                  "has_conflict": boolean,
                  "conflict_details": string | null
                }}
              ],
              "overview": string,
              "suggestions": string | string[],
              "conflicts_summary": string
            }}
            """

            user_message = f"""
            TIMEFRAME (user): {timeframe}
            PERIOD (calc): {timeframe_info['start_date']} → {timeframe_info['end_date']} ({timeframe_info['duration_days']} days)

            TOPICS:
            {topics_text}

            COMMITMENTS:
            {commitments_text}
            """

            data = self._chat_json(system_message, user_message, max_tokens=3000, temperature=0.7)
            data["generated_at"] = datetime.datetime.utcnow().isoformat()
            data["timeframe"] = timeframe
            data["study_start_date"] = timeframe_info["start_date"]
            data["study_end_date"] = timeframe_info["end_date"]
            return data

        except Exception as e:
            logger.error(f"OpenAI timetable generation error: {e}")
            return {
                "error": str(e),
                "timetable": [],
                "overview": "Error generating timetable.",
            }

    # ---------------------------------------
    # Export: generate an iCalendar (.ics) file
    # ---------------------------------------
    def generate_ics_calendar(self, timetable_data: Dict[str, Any]) -> bytes:
        """
        Generate an iCalendar (.ics) file from the timetable data.
        """
        logger.info("Generating iCalendar file from timetable data")

        try:
            # Create a calendar
            cal = Calendar()
            cal.add("prodid", "-//Student AI Assistant//Timetable Generator//EN")
            cal.add("version", "2.0")
            cal.add("calscale", "GREGORIAN")
            cal.add("method", "PUBLISH")
            cal.add("x-wr-calname", "Study Timetable")
            cal.add("x-wr-timezone", "UTC")

            timetable = timetable_data.get("timetable", [])
            for session in timetable:
                event = Event()

                session_date = session.get("date")
                start_time = session.get("start_time")
                end_time = session.get("end_time")

                default_start = dt.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
                default_duration = timedelta(hours=1)

                # Parse date/times with fallbacks
                try:
                    if session_date and start_time:
                        dt_start = dt.strptime(f"{session_date} {start_time}", "%Y-%m-%d %H:%M")
                    else:
                        # Fallback: parse from 'day' string + 'time'
                        day_str = session.get("day", "")
                        day_date_match = re.search(r"([A-Za-z]+, [A-Za-z]+ \d{1,2}, \d{4})", day_str)
                        if day_date_match:
                            try:
                                parsed_date = dt.strptime(day_date_match.group(1), "%A, %B %d, %Y")
                                time_str = session.get("time", "09:00 AM - 10:00 AM")
                                start_time_match = re.search(r"(\d{1,2}:\d{2} [AP]M)", time_str)
                                if start_time_match:
                                    dt_start = dt.strptime(
                                        f"{parsed_date.strftime('%Y-%m-%d')} {start_time_match.group(1)}",
                                        "%Y-%m-%d %I:%M %p"
                                    )
                                else:
                                    dt_start = parsed_date.replace(hour=9, minute=0)
                            except Exception:
                                dt_start = default_start
                        else:
                            dt_start = default_start

                    if session_date and end_time:
                        dt_end = dt.strptime(f"{session_date} {end_time}", "%Y-%m-%d %H:%M")
                    else:
                        duration_minutes = session.get("duration")
                        if duration_minutes and isinstance(duration_minutes, (int, float)):
                            dt_end = dt_start + timedelta(minutes=int(duration_minutes))
                        else:
                            time_str = session.get("time", "")
                            end_time_match = re.search(r"- (\d{1,2}:\d{2} [AP]M)", time_str)
                            if end_time_match:
                                try:
                                    dt_end = dt.strptime(
                                        f"{dt_start.strftime('%Y-%m-%d')} {end_time_match.group(1)}",
                                        "%Y-%m-%d %I:%M %p"
                                    )
                                except Exception:
                                    dt_end = dt_start + default_duration
                            else:
                                dt_end = dt_start + default_duration
                except Exception as e:
                    logger.error(f"Error parsing study session date/time: {e}")
                    dt_start = default_start
                    dt_end = dt_start + default_duration

                # Summary
                topics_val = session.get("topics")
                if isinstance(topics_val, list):
                    summary_topics = ", ".join(topics_val)
                else:
                    summary_topics = topics_val or "Study Session"

                event.add("summary", f"Study: {summary_topics}")
                event.add("dtstart", dt_start)
                event.add("dtend", dt_end)
                event.add("dtstamp", dt.now())

                # UID (semi-deterministic)
                uid_base = f"{dt_start.strftime('%Y%m%dT%H%M%S')}-{summary_topics}"
                event.add("uid", f"{abs(hash(uid_base))}@student-ai-assistant")

                # Description & status
                description_parts = []
                activities = session.get("activities")
                if activities:
                    if isinstance(activities, list):
                        description_parts.append("Activities: " + ", ".join(activities))
                    else:
                        description_parts.append(f"Activities: {activities}")

                description_parts.append(f"Priority: {session.get('priority', 'medium')}")

                if session.get("has_conflict"):
                    event.add("status", "TENTATIVE")
                    if session.get("conflict_details"):
                        description_parts.append(f"CONFLICT: {session.get('conflict_details')}")
                    else:
                        description_parts.append("CONFLICT: This session conflicts with another commitment")
                    # Note: Not all clients support color; kept as metadata.
                    event.add("class", "PRIVATE")
                else:
                    event.add("status", "CONFIRMED")
                    event.add("class", "PUBLIC")

                event.add("description", "\n".join(description_parts))
                cal.add_component(event)

            # Optional overview as all-day event on start date
            if timetable_data.get("overview"):
                overview_event = Event()
                overview_event.add("summary", "Study Plan Overview")
                start_date_str = timetable_data.get("study_start_date")
                try:
                    start_date = dt.strptime(start_date_str, "%Y-%m-%d") if start_date_str else dt.now()
                except Exception:
                    start_date = dt.now()
                overview_event.add("dtstart", start_date.date())
                overview_event.add("dtend", (start_date + timedelta(days=1)).date())  # end is exclusive
                overview_event.add("description", timetable_data.get("overview"))
                overview_event.add("uid", f"overview-{dt.now().strftime('%Y%m%dT%H%M%S')}@student-ai-assistant")
                overview_event.add("dtstamp", dt.now())
                cal.add_component(overview_event)

            return cal.to_ical()

        except Exception as e:
            logger.error(f"Error generating iCalendar file: {e}")
            # Minimal valid calendar on error
            cal = Calendar()
            cal.add("prodid", "-//Student AI Assistant//Timetable Generator Error//EN")
            cal.add("version", "2.0")
            error_event = Event()
            error_event.add("summary", "Error Generating Study Timetable")
            error_event.add("dtstart", dt.now())
            error_event.add("dtend", dt.now() + timedelta(hours=1))
            error_event.add("description", f"There was an error generating your study timetable: {str(e)}")
            error_event.add("uid", f"error-{dt.now().strftime('%Y%m%dT%H%M%S')}@student-ai-assistant")
            error_event.add("dtstamp", dt.now())
            cal.add_component(error_event)
            return cal.to_ical()
