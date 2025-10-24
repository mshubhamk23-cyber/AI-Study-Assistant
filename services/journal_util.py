# """
# journal_utils.py - Utilities for managing and extracting information for memory journals
# """

# import logging
# import re
# from typing import Dict, Any, List, Optional
# import datetime

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# class JournalExtractor:
#     """Class for extracting important information from conversations for memory journals"""

#     # Keywords that might indicate important information to save
#     IMPORTANT_KEYWORDS = [
#         "remember", "don't forget", "important", "note", "save",
#         "my name is", "I am", "I'm", "I like", "I need", "I want",
#         "I have to", "I must", "my goal is", "my preference is",
#         "key concept", "crucial", "essential", "vital", "significant",
#         "critical", "fundamental", "key point", "deadline", "due date",
#         "exam", "test", "quiz", "assignment", "project", "paper",
#         "remember that", "keep in mind", "make sure to"
#     ]

#     # AI-specific keywords that indicate information worth saving from AI responses
#     AI_IMPORTANT_KEYWORDS = [
#         "key concept", "important to remember", "critical point",
#         "essential information", "remember that", "don't forget",
#         "make note of", "take note", "helpful tip", "important formula",
#         "key definition", "fundamental principle", "crucial detail",
#         "this is important", "mark this", "highlight this"
#     ]

#     # Information patterns to look for in text
#     INFORMATION_PATTERNS = [
#         r"(?:my name is|I am|I'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # Name
#         r"(?:I|my) (?:have|need|want) to\s+(.+?)(?:\.|$)",  # Task/need
#         r"(?:deadline|due date).*?(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)",  # Date pattern
#         r"(?:I|my) (?:preference|like) (?:is|for)\s+(.+?)(?:\.|$)",  # Preference
#         r"(?:my goal is|trying to)\s+(.+?)(?:\.|$)"  # Goal
#     ]

#     @staticmethod
#     def should_save_ai_response(info: Dict[str, Any]) -> bool:
#         """
#         Determine if information from an AI response should be saved to the journal

#         Args:
#             info: Dictionary containing extracted information

#         Returns:
#             Boolean indicating whether to save this information
#         """
#         # Check if there's content to save
#         if not info or 'content' not in info:
#             return False

#         content = info.get('content', '').lower()

#         # Skip very short content or generic negative responses
#         if len(content.split()) < 5 or content.startswith("i don't know") or "no information" in content:
#             return False

#         # Check for AI-specific important keywords (high priority)
#         for keyword in JournalExtractor.AI_IMPORTANT_KEYWORDS:
#             if keyword.lower() in content:
#                 logger.info(f"Saving AI response with important keyword: {keyword}")
#                 return True

#         # Check for educational content markers (high priority)
#         educational_markers = [
#             "definition:", "formula:", "equation:", "theorem:", "principle:",
#             "concept:", "method:", "approach:", "technique:", "strategy:",
#             "rule:", "law:", "theory:", "hypothesis:", "conclusion:", "example:",
#             "step 1", "step 2", "first,", "second,", "third,", "finally,",
#             "remember:", "note:", "tip:", "hint:"
#         ]

#         for marker in educational_markers:
#             if marker in content:
#                 logger.info(f"Saving AI response with educational marker: {marker}")
#                 return True

#         # Check for sentences with factual statements (medium priority)
#         factual_indicators = [
#             " is ", " are ", " was ", " were ", " has ", " have ",
#             " can ", " will ", " should ", " must ", " means ", " refers to ",
#             " consists of ", " contains ", " includes ", " represents ",
#             " equals ", " equals to ", " is equal to ", " is defined as "
#         ]

#         # If it's a relatively long, possibly detailed explanation
#         # that contains factual indicators, save it
#         if len(content.split()) > 15:
#             for indicator in factual_indicators:
#                 if indicator in content:
#                     logger.info(f"Saving longer AI response with factual indicator: {indicator}")
#                     return True

#         # Check if the content has a keyword from the regular important keywords list
#         for keyword in JournalExtractor.IMPORTANT_KEYWORDS:
#             if keyword.lower() in content:
#                 logger.info(f"Saving AI response with general keyword: {keyword}")
#                 return True

#         # Additional heuristic: Save content that appears to be structured knowledge
#         if any(char in content for char in [':', '-', '•', '*', '1.', '2.']):
#             if len(content.split('\n')) > 1 or len(content.split()) > 20:
#                 logger.info("Saving AI response with structured content")
#                 return True

#         return False

#     @staticmethod
#     def extract_important_information(text: str) -> List[Dict[str, Any]]:
#         """
#         Extract important information from text

#         Args:
#             text: Text to analyze

#         Returns:
#             List of dictionaries containing extracted information
#         """
#         # Check if there's any text to analyze
#         if not text or len(text.strip()) == 0:
#             return []

#         extracted_info = []

#         # Check for keywords
#         for keyword in JournalExtractor.IMPORTANT_KEYWORDS:
#             if keyword.lower() in text.lower():
#                 # Find the sentence containing the keyword
#                 sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)

#                 for sentence in sentences:
#                     if keyword.lower() in sentence.lower():
#                         # Clean up the sentence
#                         clean_sentence = sentence.strip()

#                         # Create an entry
#                         entry = {
#                             "content": clean_sentence,
#                             "keyword": keyword,
#                             "extracted_at": datetime.datetime.utcnow()
#                         }

#                         extracted_info.append(entry)

#         # Check for information patterns
#         for pattern in JournalExtractor.INFORMATION_PATTERNS:
#             matches = re.findall(pattern, text, re.IGNORECASE)

#             for match in matches:
#                 if match:
#                     # Get the context (full sentence containing the match)
#                     sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
#                     context = ""

#                     for sentence in sentences:
#                         if match.lower() in sentence.lower():
#                             context = sentence.strip()
#                             break

#                     entry = {
#                         "content": context if context else f"Information: {match}",
#                         "matched_text": match,
#                         "pattern": pattern,
#                         "extracted_at": datetime.datetime.utcnow()
#                     }

#                     extracted_info.append(entry)

#         return extracted_info

#     @staticmethod
#     def get_memory_context(journal_entries: List[Dict[str, Any]], max_entries: int = 5) -> str:
#         """
#         Convert journal entries to context for AI model

#         Args:
#             journal_entries: List of journal entries
#             max_entries: Maximum number of entries to include

#         Returns:
#             Context string for AI prompt
#         """
#         if not journal_entries:
#             return ""

#         # Limit the number of entries
#         limited_entries = journal_entries[:max_entries]

#         # Format entries into context string
#         context_parts = []

#         for entry in limited_entries:
#             timestamp = entry.get('timestamp', entry.get('extracted_at'))
#             date_str = timestamp.strftime('%Y-%m-%d') if timestamp else 'Unknown date'

#             content = entry.get('content', '')
#             if content:
#                 context_parts.append(f"[{date_str}] {content}")

#         return "\n".join(context_parts)

#     @staticmethod
#     def prepare_journal_entry(text: str, session_id: Optional[str] = None, user_id: Optional[str] = None, subject_id: Optional[str] = None) -> Dict[str, Any]:
#         """
#         Prepare a journal entry from text

#         Args:
#             text: Text to save in journal
#             session_id: Optional Session ID
#             user_id: Optional User ID
#             subject_id: Optional subject ID for subject journal

#         Returns:
#             Journal entry dictionary
#         """
#         entry = {
#             "content": text,
#             "timestamp": datetime.datetime.utcnow()
#         }

#         if session_id:
#             entry["session_id"] = session_id

#         if user_id:
#             entry["user_id"] = user_id

#         if subject_id:
#             entry["subject_id"] = subject_id

#         return entry


"""
journal_utils.py - Utilities for managing and extracting information for memory journals
"""

import logging
import re
from typing import Dict, Any, List, Optional, Union
import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _is_str(x: Any) -> bool:
    return isinstance(x, str)


def _split_sentences(text: str) -> List[str]:
    """
    A simple sentence splitter that handles '.', '?', '!' and newlines.
    (Still lightweight; avoids heavy NLP deps.)
    """
    # Normalize whitespace a bit
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Split on end punctuation followed by whitespace/newline
    parts = re.split(r'(?<=[\.\?\!])\s+(?=[A-Z0-9\"\'])', text)
    # If the text has no clear sentence boundaries, fall back to lines
    if len(parts) == 1:
        parts = [p.strip() for p in re.split(r'\n+', text) if p.strip()]
    return [p.strip() for p in parts if p and p.strip()]


def _parse_timestamp(ts: Any) -> Optional[datetime.datetime]:
    """
    Accepts datetime, or ISO string; returns naive UTC datetime (best effort).
    """
    if isinstance(ts, datetime.datetime):
        return ts
    if _is_str(ts):
        try:
            # Handle common ISO forms
            return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            return None
    return None


class JournalExtractor:
    """Class for extracting important information from conversations for memory journals"""

    # Keywords that might indicate important information to save
    IMPORTANT_KEYWORDS = [
        "remember", "don't forget", "important", "note", "save",
        "my name is", "I am", "I'm", "I like", "I need", "I want",
        "I have to", "I must", "my goal is", "my preference is",
        "key concept", "crucial", "essential", "vital", "significant",
        "critical", "fundamental", "key point", "deadline", "due date",
        "exam", "test", "quiz", "assignment", "project", "paper",
        "remember that", "keep in mind", "make sure to"
    ]

    # AI-specific keywords that indicate information worth saving from AI responses
    AI_IMPORTANT_KEYWORDS = [
        "key concept", "important to remember", "critical point",
        "essential information", "remember that", "don't forget",
        "make note of", "take note", "helpful tip", "important formula",
        "key definition", "fundamental principle", "crucial detail",
        "this is important", "mark this", "highlight this"
    ]

    # Information patterns to look for in text
    # 1) Names, 2) tasks/needs, 3) numeric date, 4) preference, 5) goal.
    # Added: 3b) "Month 12, 2025" style date (optional enhancement).
    INFORMATION_PATTERNS = [
        r"(?:my name is|I am|I'm)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # Name
        r"(?:I|my)\s+(?:have|need|want)\s+to\s+(.+?)(?:\.|$)",          # Task/need
        r"(?:deadline|due date).*?(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)", # Numeric date
        r"(?:I|my)\s+(?:preference|like)\s+(?:is|for)\s+(.+?)(?:\.|$)", # Preference
        r"(?:my goal is|trying to)\s+(.+?)(?:\.|$)",                    # Goal
        # Month-name date like "March 12, 2025" or "12 March 2025"
        r"(?:deadline|due date).*?(?:on\s+)?((?:\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
        r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b"
        r"\s+\d{1,2},?\s+\d{2,4})|(\d{1,2}\s+\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
        r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b\s+\d{2,4}))"
    ]

    # Max characters to include in memory context (to protect token budget)
    MAX_CONTEXT_CHARS = 4000

    @staticmethod
    def should_save_ai_response(info: Dict[str, Any]) -> bool:
        """
        Determine if information from an AI response should be saved to the journal.

        Args:
            info: Dictionary containing extracted information. Expected key: 'content' (str)

        Returns:
            Boolean indicating whether to save this information
        """
        if not info:
            return False

        content = info.get("content", "")
        if not _is_str(content):
            try:
                content = str(content)
            except Exception:
                return False

        content_l = content.strip().lower()

        # Skip very short content or generic negatives
        if len(content_l.split()) < 5 or content_l.startswith("i don't know") or "no information" in content_l:
            return False

        # AI-specific important keywords
        for keyword in JournalExtractor.AI_IMPORTANT_KEYWORDS:
            if keyword.lower() in content_l:
                logger.info(f"Saving AI response with important keyword: {keyword}")
                return True

        # Educational markers
        educational_markers = [
            "definition:", "formula:", "equation:", "theorem:", "principle:",
            "concept:", "method:", "approach:", "technique:", "strategy:",
            "rule:", "law:", "theory:", "hypothesis:", "conclusion:", "example:",
            "step 1", "step 2", "first,", "second,", "third,", "finally,",
            "remember:", "note:", "tip:", "hint:"
        ]
        for marker in educational_markers:
            if marker in content_l:
                logger.info(f"Saving AI response with educational marker: {marker}")
                return True

        # Factual indicators (longer content)
        factual_indicators = [
            " is ", " are ", " was ", " were ", " has ", " have ",
            " can ", " will ", " should ", " must ", " means ", " refers to ",
            " consists of ", " contains ", " includes ", " represents ",
            " equals ", " equals to ", " is equal to ", " is defined as "
        ]
        if len(content_l.split()) > 15:
            for indicator in factual_indicators:
                if indicator in content_l:
                    logger.info(f"Saving longer AI response with factual indicator: {indicator}")
                    return True

        # General important keywords
        for keyword in JournalExtractor.IMPORTANT_KEYWORDS:
            if keyword.lower() in content_l:
                logger.info(f"Saving AI response with general keyword: {keyword}")
                return True

        # Structured content heuristic
        if any(tok in content for tok in (":", "-", "•", "*", "1.", "2.")):
            sentences_or_lines = content.split("\n")
            if len(sentences_or_lines) > 1 or len(content.split()) > 20:
                logger.info("Saving AI response with structured content")
                return True

        return False

    @staticmethod
    def extract_important_information(text: str) -> List[Dict[str, Any]]:
        """
        Extract important information from text.

        Args:
            text: Text to analyze

        Returns:
            List of dictionaries containing extracted information
        """
        if not text or not str(text).strip():
            return []

        text = str(text)
        sentences = _split_sentences(text)
        results: List[Dict[str, Any]] = []

        seen_norm: set = set()  # to de-duplicate by normalized sentence

        # Keyword-based extraction (keep sentence containing the keyword)
        for keyword in JournalExtractor.IMPORTANT_KEYWORDS:
            kw_l = keyword.lower()
            for s in sentences:
                if kw_l in s.lower():
                    norm = s.strip().lower()
                    if norm not in seen_norm:
                        results.append({
                            "content": s.strip(),
                            "keyword": keyword,
                            "extracted_at": datetime.datetime.utcnow()
                        })
                        seen_norm.add(norm)

        # Pattern-based extraction (capture value + provide context sentence)
        for pattern in JournalExtractor.INFORMATION_PATTERNS:
            for m in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
                matched = m.group(1) if m.groups() else m.group(0)
                matched_str = matched.strip() if _is_str(matched) else str(matched)

                # Find a sentence that contains the matched span
                context = ""
                start, end = m.span()
                for s in sentences:
                    # Rough check: if any overlap of substring
                    if matched_str and matched_str.lower() in s.lower():
                        context = s.strip()
                        break
                    # fallback: if sentence boundaries enclose the span
                    if start >= text.find(s) and end <= (text.find(s) + len(s)):
                        context = s.strip()
                        break

                norm = context.lower() if context else matched_str.lower()
                if norm not in seen_norm:
                    results.append({
                        "content": context or f"Information: {matched_str}",
                        "matched_text": matched_str,
                        "pattern": pattern,
                        "extracted_at": datetime.datetime.utcnow()
                    })
                    seen_norm.add(norm)

        return results

    @staticmethod
    def get_memory_context(journal_entries: List[Dict[str, Any]], max_entries: int = 5) -> str:
        """
        Convert journal entries to context for AI model.

        Args:
            journal_entries: List of journal entries (dicts)
            max_entries: Maximum number of entries to include

        Returns:
            Context string for AI prompt
        """
        if not journal_entries:
            return ""

        limited = journal_entries[:max_entries]

        parts: List[str] = []
        total_len = 0

        for entry in limited:
            # Accept multiple timestamp keys
            ts = entry.get("timestamp") or entry.get("extracted_at") or entry.get("created_at")
            dt_obj = _parse_timestamp(ts)
            date_str = dt_obj.strftime("%Y-%m-%d") if dt_obj else "Unknown date"

            content = entry.get("content", "")
            if not _is_str(content):
                content = str(content)

            line = f"[{date_str}] {content.strip()}"
            # Enforce global character cap to protect token budget
            if total_len + len(line) + 1 > JournalExtractor.MAX_CONTEXT_CHARS:
                break
            parts.append(line)
            total_len += len(line) + 1

        return "\n".join(parts)

    @staticmethod
    def prepare_journal_entry(
        text: Union[str, Any],
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        subject_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare a journal entry from text.

        Args:
            text: Text to save in journal
            session_id: Optional Session ID
            user_id: Optional User ID
            subject_id: Optional subject ID for subject journal

        Returns:
            Journal entry dictionary
        """
        now = datetime.datetime.utcnow()
        content = text if _is_str(text) else str(text)

        entry: Dict[str, Any] = {
            "content": content,
            "timestamp": now,      # kept for backward compatibility
            "created_at": now      # commonly used in your DB queries
        }

        if session_id:
            entry["session_id"] = session_id
        if user_id:
            entry["user_id"] = user_id
        if subject_id:
            entry["subject_id"] = subject_id

        return entry
