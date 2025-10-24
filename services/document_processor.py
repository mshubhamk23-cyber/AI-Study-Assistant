# """
# document_processor.py - Utility functions for processing uploaded documents
# """

# import os
# import logging
# from typing import Dict, Any, List, Optional
# import pdfplumber
# from docx import Document
# import markdown
# import re
# from pathlib import Path
# import warnings

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Suppress specific pdfminer warnings
# warnings.filterwarnings("ignore", category=UserWarning, module='pdfminer.pdfpage')

# def extract_text_from_pdf(file_path: str) -> str:
#     """
#     Extract text content from a PDF file

#     Args:
#         file_path: Path to the PDF file

#     Returns:
#         Extracted text as a string
#     """
#     try:
#         text_content = []
#         with pdfplumber.open(file_path) as pdf:
#             for page in pdf.pages:
#                 text = page.extract_text()
#                 if text:
#                     text_content.append(text)
#         return "\n\n".join(text_content)
#     except Exception as e:
#         logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
#         return f"Error processing PDF: {str(e)}"

# def extract_text_from_docx(file_path: str) -> str:
#     """
#     Extract text content from a DOCX file

#     Args:
#         file_path: Path to the DOCX file

#     Returns:
#         Extracted text as a string
#     """
#     try:
#         doc = Document(file_path)
#         text_content = []

#         for para in doc.paragraphs:
#             if para.text:
#                 text_content.append(para.text)

#         for table in doc.tables:
#             for row in table.rows:
#                 row_text = []
#                 for cell in row.cells:
#                     if cell.text:
#                         row_text.append(cell.text)
#                 if row_text:
#                     text_content.append(" | ".join(row_text))

#         return "\n\n".join(text_content)
#     except Exception as e:
#         logger.error(f"Error extracting text from DOCX {file_path}: {str(e)}")
#         return f"Error processing DOCX: {str(e)}"

# def extract_text_from_txt(file_path: str) -> str:
#     """
#     Extract text content from a TXT file

#     Args:
#         file_path: Path to the TXT file

#     Returns:
#         Extracted text as a string
#     """
#     try:
#         with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
#             return file.read()
#     except Exception as e:
#         logger.error(f"Error extracting text from TXT {file_path}: {str(e)}")
#         return f"Error processing TXT: {str(e)}"

# def extract_text_from_markdown(file_path: str) -> str:
#     """
#     Extract text content from a Markdown file

#     Args:
#         file_path: Path to the Markdown file

#     Returns:
#         Extracted text as a string (with markdown formatting removed)
#     """
#     try:
#         with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
#             md_content = file.read()

#         # Convert markdown to HTML
#         html_content = markdown.markdown(md_content)

#         # Remove HTML tags
#         clean_text = re.sub(r'<[^>]*>', '', html_content)

#         return clean_text
#     except Exception as e:
#         logger.error(f"Error extracting text from Markdown {file_path}: {str(e)}")
#         return f"Error processing Markdown: {str(e)}"

# def extract_document_text(file_path: str) -> Optional[str]:
#     """
#     Extract text from a document based on its file extension

#     Args:
#         file_path: Path to the document

#     Returns:
#         Extracted text as a string or None if the file type is not supported
#     """
#     file_extension = Path(file_path).suffix.lower()

#     if file_extension == '.pdf':
#         return extract_text_from_pdf(file_path)
#     elif file_extension == '.docx':
#         return extract_text_from_docx(file_path)
#     elif file_extension == '.txt':
#         return extract_text_from_txt(file_path)
#     elif file_extension == '.md':
#         return extract_text_from_markdown(file_path)
#     else:
#         logger.warning(f"Unsupported file type: {file_extension}")
#         return None

# def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
#     """
#     Split text into overlapping chunks for better search and context

#     Args:
#         text: The text to split
#         chunk_size: Maximum size of each chunk in characters
#         overlap: Number of overlapping characters between chunks

#     Returns:
#         List of text chunks
#     """
#     if not text:
#         return []

#     chunks = []

#     # Split by paragraphs first
#     paragraphs = text.split('\n\n')
#     current_chunk = ""

#     for paragraph in paragraphs:
#         # If adding this paragraph exceeds chunk size, save current chunk and start new one
#         if len(current_chunk) + len(paragraph) > chunk_size:
#             if current_chunk:
#                 chunks.append(current_chunk.strip())

#             # Start new chunk with overlap from previous chunk
#             if len(current_chunk) > overlap:
#                 current_chunk = current_chunk[-overlap:] + "\n\n" + paragraph
#             else:
#                 current_chunk = paragraph
#         else:
#             if current_chunk:
#                 current_chunk += "\n\n" + paragraph
#             else:
#                 current_chunk = paragraph

#     # Add the last chunk if it exists
#     if current_chunk:
#         chunks.append(current_chunk.strip())

#     return chunks

# def prepare_document_for_indexing(doc_info: Dict[str, Any], subject_name: str,
#                                   file_path: str) -> List[Dict[str, Any]]:
#     """
#     Prepare document for indexing in Azure AI Search

#     Args:
#         doc_info: Document information dictionary
#         subject_name: Name of the subject
#         file_path: Path to the document file

#     Returns:
#         List of document chunks ready for indexing
#     """
#     try:
#         # Extract text from document
#         document_text = extract_document_text(file_path)

#         if not document_text:
#             logger.warning(f"No text could be extracted from {file_path}")
#             return []

#         # Split text into chunks
#         text_chunks = chunk_text(document_text)

#         # Create indexable documents
#         documents = []
#         for i, chunk in enumerate(text_chunks):
#             # Create a unique ID for each chunk
#             chunk_id = f"{doc_info['_id']}_{i}"

#             # Ensure field names match exactly with the index schema
#             document = {
#                 "id": chunk_id,
#                 "document_id": doc_info['_id'],
#                 "document_name": doc_info['filename'],
#                 "subject_id": doc_info.get('subject_id', ''),
#                 "subject_name": subject_name,
#                 "chunk_id": i,
#                 "content": chunk,
#                 "file_path": file_path
#             }

#             documents.append(document)

#         logger.info(f"Prepared {len(documents)} document chunks for indexing from {file_path}")
#         return documents

#     except Exception as e:
#         logger.error(f"Error preparing document for indexing: {str(e)}")
#         return []

"""
document_processor.py - Utility functions for processing uploaded documents
"""

import os
import logging
from typing import Dict, Any, List, Optional
import pdfplumber
from docx import Document
import markdown
import re
from pathlib import Path
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress specific pdfminer warnings
warnings.filterwarnings("ignore", category=UserWarning, module='pdfminer.pdfpage')


def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """
    Extract text content from a PDF file

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text as a string, or None on error
    """
    try:
        text_content: List[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
        return "\n\n".join(text_content).strip() if text_content else ""
    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_path}: {e}")
        return None


def extract_text_from_docx(file_path: str) -> Optional[str]:
    """
    Extract text content from a DOCX file

    Args:
        file_path: Path to the DOCX file

    Returns:
        Extracted text as a string, or None on error
    """
    try:
        doc = Document(file_path)
        text_content: List[str] = []

        for para in doc.paragraphs:
            if para.text:
                text_content.append(para.text)

        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text:
                        row_text.append(cell.text)
                if row_text:
                    text_content.append(" | ".join(row_text))

        return "\n\n".join(text_content).strip()
    except Exception as e:
        logger.error(f"Error extracting text from DOCX {file_path}: {e}")
        return None


def extract_text_from_txt(file_path: str) -> Optional[str]:
    """
    Extract text content from a TXT file

    Args:
        file_path: Path to the TXT file

    Returns:
        Extracted text as a string, or None on error
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error extracting text from TXT {file_path}: {e}")
        return None


def extract_text_from_markdown(file_path: str) -> Optional[str]:
    """
    Extract text content from a Markdown file

    Args:
        file_path: Path to the Markdown file

    Returns:
        Extracted plain text (markdown rendered to HTML, then tags stripped), or None on error
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            md_content = f.read()

        # Convert markdown to HTML
        html_content = markdown.markdown(md_content)

        # Remove HTML tags (simple stripper)
        clean_text = re.sub(r"<[^>]*>", "", html_content)
        return clean_text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from Markdown {file_path}: {e}")
        return None


def extract_document_text(file_path: str) -> Optional[str]:
    """
    Extract text from a document based on its file extension

    Args:
        file_path: Path to the document

    Returns:
        Extracted text as a string, "" for empty doc, or None if the file type is unsupported or an error occurs
    """
    file_extension = Path(file_path).suffix.lower()

    if file_extension == ".pdf":
        return extract_text_from_pdf(file_path)
    elif file_extension == ".docx":
        return extract_text_from_docx(file_path)
    elif file_extension == ".txt":
        return extract_text_from_txt(file_path)
    elif file_extension in (".md", ".markdown"):
        return extract_text_from_markdown(file_path)
    else:
        logger.warning(f"Unsupported file type: {file_extension}")
        return None


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Split text into overlapping chunks for better search and context

    Args:
        text: The text to split
        chunk_size: Maximum size of each chunk in characters
        overlap: Number of overlapping characters between chunks

    Returns:
        List of text chunks
    """
    if not text:
        return []

    # Normalize newlines a bit (keep paragraphs)
    paragraphs = text.split("\n\n")
    chunks: List[str] = []
    current = ""

    def flush_current():
        nonlocal current
        if current:
            chunks.append(current.strip())
            current = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # Case A: paragraph fits into remaining space
        if len(current) + (2 if current else 0) + len(paragraph) <= chunk_size:
            current = (current + ("\n\n" if current else "") + paragraph)
            continue

        # Case B: paragraph doesn’t fit; flush current if it has content
        if current:
            flush_current()

        # Case C: paragraph is itself longer than chunk_size -> slice it with overlap
        if len(paragraph) > chunk_size:
            step = max(1, chunk_size - overlap)
            start = 0
            while start < len(paragraph):
                end = min(start + chunk_size, len(paragraph))
                slice_text = paragraph[start:end]
                chunks.append(slice_text.strip())
                if end >= len(paragraph):
                    break
                start = end - overlap  # slide with overlap
            current = ""  # nothing pending
        else:
            # Start a new chunk with this paragraph
            current = paragraph

    # Final flush
    if current:
        chunks.append(current.strip())

    return chunks


def prepare_document_for_indexing(
    doc_info: Dict[str, Any],
    subject_name: str,
    file_path: str
) -> List[Dict[str, Any]]:
    """
    Prepare a document for indexing in your search store

    Args:
        doc_info: Document information dictionary (expects at least '_id' and 'filename')
        subject_name: Name of the subject
        file_path: Path to the document file

    Returns:
        List of document chunks ready for indexing
    """
    try:
        # Extract text from document
        document_text = extract_document_text(file_path)

        if document_text is None:
            logger.warning(f"Skipping {file_path}: extraction failed or unsupported type.")
            return []

        if not document_text.strip():
            logger.warning(f"No textual content found in {file_path}")
            return []

        # Split text into chunks
        text_chunks = chunk_text(document_text)

        # Create indexable documents
        documents = []
        for i, chunk in enumerate(text_chunks):
            chunk_id = f"{doc_info['_id']}_{i}"
            document = {
                "id": chunk_id,
                "document_id": doc_info["_id"],
                "document_name": doc_info["filename"],
                "subject_id": doc_info.get("subject_id", ""),
                "subject_name": subject_name,
                "chunk_id": i,
                "content": chunk,
                "file_path": file_path,
            }
            documents.append(document)

        logger.info(f"Prepared {len(documents)} document chunks for indexing from {file_path}")
        return documents

    except Exception as e:
        logger.error(f"Error preparing document for indexing ({file_path}): {e}")
        return []
