# services/rag_service.py
import os, io, re, threading
from datetime import date
from typing import List, Tuple, Dict, Any, Optional

from dotenv import load_dotenv
load_dotenv()

# ---------------- Config ----------------
# Where per-subject vector stores will live:
VD_ROOT = os.getenv("VD_ROOT", os.path.join("vectorstores", "subjects"))  # e.g., C:\...\vd_subjects
os.makedirs(VD_ROOT, exist_ok=True)

# Where uploads are stored (your app already uses uploads/<subject_id>/)
UPLOADS_ROOT = os.getenv("UPLOAD_FOLDER", "uploads")

EMBED_MODEL   = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OPENAI_MODEL  = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
LLM_MODE      = os.getenv("LLM_MODE", "").lower()  # "", "none" -> offline only

MIN_RELEVANCE = float(os.getenv("MIN_RELEVANCE", "0.35"))
K_INITIAL     = int(os.getenv("K_INITIAL", "24"))
K_FINAL       = int(os.getenv("K_FINAL", "12"))
EXCERPT_CHAR_LIMIT = int(os.getenv("EXCERPT_CHAR_LIMIT", "2000"))

# OCR toggles (no Poppler needed)
ENABLE_OCR = os.getenv("ENABLE_OCR", "1") == "1"    # enable pytesseract OCR for scanned PDFs/images
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()  # set if tesseract is not on PATH (e.g., C:\Program Files\Tesseract-OCR\tesseract.exe)

# ---------------- Deps ----------------
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

import faiss
import chardet
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
try:
    from langchain_openai import ChatOpenAI
    _OPENAI_OK = True
except Exception:
    from langchain.chat_models import ChatOpenAI as _LegacyChatOpenAI  # pragma: no cover
    _OPENAI_OK = False

# Configure Tesseract if provided
if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ---------------- State / caches ----------------
_emb_lock = threading.Lock()
_emb_cache: Optional[HuggingFaceEmbeddings] = None
_splitter: Optional[RecursiveCharacterTextSplitter] = None
_llm: Optional[Any] = None
_use_openai = False

def _get_embeddings() -> HuggingFaceEmbeddings:
    global _emb_cache
    if _emb_cache is None:
        with _emb_lock:
            if _emb_cache is None:
                _emb_cache = HuggingFaceEmbeddings(model_name=EMBED_MODEL)
    return _emb_cache

def _get_splitter() -> RecursiveCharacterTextSplitter:
    global _splitter
    if _splitter is None:
        _splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    return _splitter

def _init_llm_if_any():
    global _llm, _use_openai
    if _llm is not None:
        return
    if OPENAI_API_KEY and LLM_MODE != "none":
        try:
            if _OPENAI_OK:
                _llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.3, openai_api_key=OPENAI_API_KEY)
            else:
                _llm = _LegacyChatOpenAI(temperature=0.3, model=OPENAI_MODEL, openai_api_key=OPENAI_API_KEY)
            _use_openai = True
        except Exception:
            _llm = None
            _use_openai = False
    else:
        _llm = None
        _use_openai = False

# ---------------- Paths ----------------
def _subject_vd_dir(subject_id: str) -> str:
    p = os.path.join(VD_ROOT, subject_id)
    os.makedirs(p, exist_ok=True)
    return p

def _subject_uploads_dir(subject_id: str) -> str:
    p = os.path.join(UPLOADS_ROOT, subject_id)
    os.makedirs(p, exist_ok=True)
    return p

# ---------------- Vector store IO ----------------
def _faiss_dim_at(path: str) -> int:
    idx = faiss.read_index(os.path.join(path, "index.faiss"))
    return idx.d

def _load_store_for_subject(subject_id: str) -> Optional[FAISS]:
    vd = _subject_vd_dir(subject_id)
    if not os.path.isfile(os.path.join(vd, "index.faiss")):
        return None
    emb = _get_embeddings()
    # dim guard
    faiss_d = _faiss_dim_at(vd)
    emb_d = len(emb.embed_query("probe"))
    if faiss_d != emb_d:
        raise RuntimeError(
            f"[{subject_id}] Embedding dimension mismatch: index={faiss_d}, model={emb_d}. "
            f"Rebuild this subject's index with EMBED_MODEL={EMBED_MODEL}."
        )
    return FAISS.load_local(vd, emb, allow_dangerous_deserialization=True)

def _save_store_for_subject(subject_id: str, store: FAISS):
    vd = _subject_vd_dir(subject_id)
    store.save_local(vd)

# def _ensure_empty_store(subject_id: str) -> FAISS:
#     store = _load_store_for_subject(subject_id)
#     if store is None:
#         store = FAISS.from_documents([], _get_embeddings())
#         _save_store_for_subject(subject_id, store)
#     return store

def _ensure_empty_store(subject_id):
    """
    Safely initialize an empty FAISS index. 
    FAISS requires at least one embedding to know the dimension.
    We'll create a single dummy embedding vector if no documents exist yet.
    """
    embeddings = _get_embeddings()
    dummy_text = ["init"]  # one dummy string
    try:
        store = FAISS.from_texts(dummy_text, embeddings)
        store.delete(ids=["0"])  # remove dummy vector
        return store
    except Exception as e:
        print(f"[WARN] Could not create FAISS index: {e}")
        return FAISS.from_texts(["temporary"], embeddings)

# ---------------- File reading / OCR ----------------
_IMG_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
_TXT_EXT = {".txt", ".md", ".markdown"}
_DOCX_EXT = {".docx"}
_PDF_EXT = {".pdf"}

def _read_text_txt(path: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    enc = chardet.detect(raw).get("encoding") or "utf-8"
    return raw.decode(enc, errors="ignore")

def _read_text_docx(path: str) -> str:
    try:
        import docx
    except Exception:
        return ""
    d = docx.Document(path)
    return "\n".join(p.text for p in d.paragraphs if p.text)

def _ocr_pil_image(img: Image.Image) -> str:
    if not ENABLE_OCR:
        return ""
    try:
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

def _read_text_pdf_with_fitz(path: str) -> str:
    """Extract text; if too little, render pages to images and OCR (no Poppler)."""
    text_pages: List[str] = []
    ocr_pages: List[str] = []
    try:
        doc = fitz.open(path)
    except Exception:
        return ""

    # First pass: text layer
    for p in doc:
        text_pages.append(p.get_text("text") or "")

    text = "\n".join(text_pages).strip()
    # If text is sparse and OCR enabled, do OCR
    if ENABLE_OCR and len(text) < 50:
        for p in doc:
            # Render page to image (RGB)
            pix = p.get_pixmap(dpi=300)  # higher dpi for OCR
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
            ocr_pages.append(_ocr_pil_image(img))
        text = "\n".join(ocr_pages).strip()

    doc.close()
    return text

def _read_text_image(path: str) -> str:
    if not ENABLE_OCR:
        return ""
    try:
        img = Image.open(path).convert("RGB")
        return _ocr_pil_image(img)
    except Exception:
        return ""

def ocr_and_chunk_file(subject_id: str, file_path: str, filename: Optional[str] = None) -> List[Document]:
    """
    Reads a file, optionally OCRs, returns LangChain Documents with metadata.
    """
    filename = filename or os.path.basename(file_path)
    ext = os.path.splitext(filename.lower())[1]

    if ext in _TXT_EXT:
        text = _read_text_txt(file_path)
    elif ext in _DOCX_EXT:
        text = _read_text_docx(file_path)
    elif ext in _PDF_EXT:
        text = _read_text_pdf_with_fitz(file_path)
    elif ext in _IMG_EXT:
        text = _read_text_image(file_path)
    else:
        text = ""

    text = (text or "").strip()
    if not text:
        return []

    splitter = _get_splitter()
    chunks = splitter.split_text(text)
    docs: List[Document] = []
    for ch in chunks:
        if ch.strip():
            docs.append(Document(
                page_content=ch,
                metadata={
                    "subject_id": subject_id,
                    "document_name": filename,
                    "source": file_path
                }
            ))
    return docs

# ---------------- Build / Update index ----------------
def create_subject_index(subject_id: str, subject_name: str) -> Dict[str, Any]:
    """
    Build (or rebuild) this subject's FAISS from all files under uploads/<subject_id>/.
    If no files yet, creates an empty index.
    """
    uploads_dir = _subject_uploads_dir(subject_id)
    files = []
    for root, _, names in os.walk(uploads_dir):
        for n in names:
            files.append(os.path.join(root, n))

    emb = _get_embeddings()
    all_docs: List[Document] = []
    for fp in files:
        all_docs.extend(ocr_and_chunk_file(subject_id, fp, filename=os.path.basename(fp)))

    if all_docs:
        store = FAISS.from_documents(all_docs, emb)
        _save_store_for_subject(subject_id, store)
        return {"ok": True, "chunks_indexed": len(all_docs), "created_empty": False}
    else:
        _ensure_empty_store(subject_id)
        return {"ok": True, "chunks_indexed": 0, "created_empty": True}

def index_new_files(subject_id: str, subject_name: str, file_paths: List[str]) -> Dict[str, Any]:
    """
    Incrementally index *newly uploaded* files into this subject's FAISS.
    """
    store = _ensure_empty_store(subject_id)
    emb = _get_embeddings()

    new_docs: List[Document] = []
    for fp in file_paths:
        new_docs.extend(ocr_and_chunk_file(subject_id, fp, filename=os.path.basename(fp)))

    if new_docs:
        store.add_documents(new_docs)
        _save_store_for_subject(subject_id, store)
        return {"ok": True, "chunks_added": len(new_docs)}
    else:
        return {"ok": True, "chunks_added": 0}

# ---------------- Retrieval + Answering (per subject) ----------------
def _similarity_with_relevance(store: FAISS, query: str, k: int):
    try:
        return store.similarity_search_with_relevance_scores(query, k=k)
    except Exception:
        docs_scores = store.similarity_search_with_score(query, k=k)
        return [(doc, 1.0 / (1.0 + float(dist))) for doc, dist in docs_scores]

def _build_context(hits, limit_chars: int) -> str:
    out, size = [], 0
    for i, (doc, score) in enumerate(hits, 1):
        meta = doc.metadata or {}
        src = meta.get("source") or meta.get("document_name") or "doc"
        head = f"[{i}] {src}  (relevance: {score:.2f})\n"
        take = limit_chars - size - len(head)
        if take <= 0: break
        snippet = (doc.page_content or "")[:take]
        out.append(head + snippet)
        size += len(head) + len(snippet)
        if size >= limit_chars: break
    return "\n\n".join(out)

def _build_prompt(question: str, context_block: str) -> str:
    return (
        "You are a helpful study assistant. You MUST answer strictly and only from the provided Context.\n"
        "If the answer is not present in the Context, reply exactly with:\n"
        "\"I don't know based on your materials.\"\n\n"
        "Write clearly. Prefer short paragraphs or bullets when useful.\n"
        "If your direct answer would be short, add a brief elaboration (key points or a micro-example), "
        "but DO NOT add outside knowledge. Stay inside the Context at all times.\n"
        "Target length: about 80–140 words. Do not exceed 180 words.\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context_block}\n"
    )

_SENT_SPLIT = re.compile(r'(?<=[.!?])\s+')

def _extractive_answer(context_block: str, max_sentences: int = 6) -> str:
    text = (context_block or "").strip()
    if not text:
        return "I don't know based on your materials."
    stripped = re.sub(r'\[\d+\]\s+[^\n]+\n', '', text)
    sents = _SENT_SPLIT.split(stripped)
    bullets = []
    for s in sents:
        s = s.strip()
        if len(s) < 8: continue
        bullets.append(f"- {s}")
        if len(bullets) >= max_sentences: break
    if not bullets:
        return "I don't know based on your materials."
    return "Here’s what your materials say:\n\n" + "\n".join(bullets)

def answer_question_subject(subject_id: str, question: str) -> Dict[str, Any]:
    """
    Answer using ONLY the subject's index at VD_ROOT/<subject_id>.
    """
    _init_llm_if_any()
    store = _load_store_for_subject(subject_id)
    if store is None:
        return {"answer": "I don't know based on your materials.", "mode": ("openai" if _use_openai else "offline"), "sources": []}

    raw = _similarity_with_relevance(store, question, k=K_INITIAL)
    hits = [(d, s) for (d, s) in raw if s is not None and s >= MIN_RELEVANCE][:K_FINAL]
    if not hits:
        return {"answer": "I don't know based on your materials.", "mode": ("openai" if _use_openai else "offline"), "sources": []}

    context = _build_context(hits, EXCERPT_CHAR_LIMIT)

    if _use_openai and _llm is not None:
        try:
            resp = _llm.invoke([{"role": "user", "content": _build_prompt(question, context)}])
            answer = (resp.content or "").strip() or "I don't know based on your materials."
            mode = "openai"
        except Exception as e:
            answer = _extractive_answer(context)
            mode = f"offline (OpenAI error: {e})"
    else:
        answer = _extractive_answer(context)
        mode = "offline"

    sources = []
    for i, (doc, score) in enumerate(hits, 1):
        meta = doc.metadata or {}
        sources.append({
            "rank": i,
            "source": meta.get("source") or meta.get("document_name") or "doc",
            "relevance": round(float(score), 2)
        })
    return {"answer": answer, "mode": mode, "sources": sources}

# -------------- Convenience for routes --------------
def get_config_snapshot() -> Dict[str, Any]:
    return {
        "VD_ROOT": VD_ROOT,
        "UPLOADS_ROOT": UPLOADS_ROOT,
        "EMBED_MODEL": EMBED_MODEL,
        "OPENAI_MODEL": OPENAI_MODEL,
        "LLM_MODE": ("openai" if (_use_openai and _llm is not None) else "offline"),
        "MIN_RELEVANCE": MIN_RELEVANCE,
        "K_INITIAL": K_INITIAL,
        "K_FINAL": K_FINAL,
        "ENABLE_OCR": ENABLE_OCR,
    }
