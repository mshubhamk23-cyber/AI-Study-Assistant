#!/usr/bin/env python3
# =========================================================
# Study Assistant (Single FAISS Index, Document-Only RAG)
# - Loads ONE FAISS index from VD/
# - Answers ONLY from your materials; else says:
#   "I don't know based on your materials."
# - Shows used sources with relevance scores
# - Modes:
#   * OpenAI mode (if OPENAI_API_KEY is set)
#   * Offline Extractive mode (no key or LLM_MODE=none)
# - .env support
# =========================================================

import os
import re
import time
import faiss
from typing import List, Tuple
from datetime import date
from dotenv import load_dotenv

# ---------- .env ----------
load_dotenv()

# ---------- Config (env or defaults) ----------
# Point this to the SINGLE FAISS index directory that has index.faiss + index.pkl
VD = os.getenv(
    "VD",
    r"C:\Final LY_project\LY-proj-Flask\ocr\output_vd\faiss_sentence-transformers_all-MiniLM-L6-v2"
)
# Default model set to L6-v2 to match the path name above. Change if you built with another model.
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MIN_RELEVANCE = float(os.getenv("MIN_RELEVANCE", "0.35"))  # 0..1; raise to be stricter
K_INITIAL = int(os.getenv("K_INITIAL", "24"))
K_FINAL = int(os.getenv("K_FINAL", "12"))
EXCERPT_CHAR_LIMIT = int(os.getenv("EXCERPT_CHAR_LIMIT", "2000"))

STREAM_TYPING = os.getenv("STREAM_TYPING", "1") == "1"
TYPE_SPEED_SEC = float(os.getenv("TYPE_SPEED_SEC", "0.0025"))

LLM_MODE = os.getenv("LLM_MODE", "").lower()  # "", "none" -> offline even if key exists
API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# ---------- LangChain / OpenAI ----------
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

USE_OPENAI = False
LLM = None
if API_KEY and LLM_MODE != "none":
    try:
        from langchain_openai import ChatOpenAI  # modern import
        LLM = ChatOpenAI(model=OPENAI_MODEL, temperature=0.3, openai_api_key=API_KEY)
        USE_OPENAI = True
    except Exception:
        USE_OPENAI = False
        LLM = None

# ---------- Helpers ----------
def ensure_single_index_dir(root: str):
    if not os.path.isdir(root):
        raise RuntimeError(f"VD does not exist: {root}")
    if not os.path.isfile(os.path.join(root, "index.faiss")):
        raise RuntimeError(
            f"No index.faiss found in VD: {root}\n"
            "Place your single FAISS index here (index.faiss and index.pkl)."
        )

def read_faiss_dim(index_dir: str) -> int:
    idx_path = os.path.join(index_dir, "index.faiss")
    index = faiss.read_index(idx_path)
    return index.d

def load_store(root: str):
    # Embeddings
    emb = HuggingFaceEmbeddings(model_name=EMBED_MODEL)

    # Dim guard
    faiss_d = read_faiss_dim(root)
    emb_d = len(emb.embed_query("probe"))
    if faiss_d != emb_d:
        raise RuntimeError(
            f"Embedding dimension mismatch: index={faiss_d}, model={emb_d}\n"
            f"Rebuild FAISS with EMBED_MODEL={EMBED_MODEL} or set EMBED_MODEL to the one you used."
        )

    store = FAISS.load_local(root, emb, allow_dangerous_deserialization=True)
    return store, emb

def similarity_with_relevance(store: FAISS, query: str, k: int):
    try:
        return store.similarity_search_with_relevance_scores(query, k=k)
    except Exception:
        docs_scores = store.similarity_search_with_score(query, k=k)
        return [(doc, 1.0 / (1.0 + float(dist))) for doc, dist in docs_scores]

def build_context(hits, limit_chars: int) -> str:
    out, size = [], 0
    for i, (doc, score) in enumerate(hits, 1):
        meta = doc.metadata or {}
        src = meta.get("source") or meta.get("file_path") or meta.get("document_name") or "Unknown"
        head = f"[{i}] {src}  (relevance: {score:.2f})\n"
        take = limit_chars - size - len(head)
        if take <= 0:
            break
        snippet = (doc.page_content or "")[:take]
        out.append(head + snippet)
        size += len(head) + len(snippet)
        if size >= limit_chars:
            break
    return "\n\n".join(out)

def type_out(text: str, delay: float = TYPE_SPEED_SEC):
    if not STREAM_TYPING:
        print(text, end="", flush=True)
        return
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(0 if ch.isspace() else delay)

def build_prompt(query: str, context_block: str) -> str:
    today = date.today().isoformat()
    return (
        "You are a helpful study assistant. You must answer the user "
        "strictly and only from the provided context. If the answer is not present "
        "in the context, respond exactly with: \"I don't know based on your materials.\"\n\n"
        "Write clearly with short steps or bullet points when useful. Do not invent facts.\n\n"
        f"**As of:** {today}\n\n"
        f"**Question:** {query}\n\n"
        f"**Context:**\n{context_block}\n"
    )

# ---------- Offline Extractive Answer (no LLM) ----------
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')

def extractive_answer_from_context(context_block: str, max_sentences: int = 6) -> str:
    text = context_block.strip()
    if not text:
        return "I don't know based on your materials."
    # Strip headers like [1] source ...
    stripped = re.sub(r'\[\d+\]\s+[^\n]+\n', '', text)
    sentences = _SENTENCE_SPLIT.split(stripped)
    bullets = []
    for s in sentences:
        s = s.strip()
        if len(s) < 8:
            continue
        bullets.append(f"- {s}")
        if len(bullets) >= max_sentences:
            break
    if not bullets:
        return "I don't know based on your materials."
    return "Here’s what your materials say:\n\n" + "\n".join(bullets)

# ---------- Main ----------
def main():
    print("🎓 Single-Index RAG — Document-Only Study Assistant")
    print(f"Vector root (VD): {VD}")
    print(f"Answering mode: {'OpenAI mode' if USE_OPENAI else 'Offline extractive mode'}\n")

    ensure_single_index_dir(VD)
    store, _ = load_store(VD)
    print("Loaded FAISS index.\nType your question, or 'exit' to quit.\n")

    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not q:
            continue
        if q.lower() in {"exit", "quit"}:
            print("Bye.")
            break

        # Retrieve
        raw = similarity_with_relevance(store, q, k=K_INITIAL)
        hits = [(d, s) for (d, s) in raw if s is not None and s >= MIN_RELEVANCE][:K_FINAL]

        if not hits:
            print("\n---\n")
            type_out("I don't know based on your materials.\n")
            print("\n---\n")
            continue

        context_block = build_context(hits, EXCERPT_CHAR_LIMIT)

        if USE_OPENAI and LLM is not None:
            prompt = build_prompt(q, context_block)
            resp = LLM.invoke([{"role": "user", "content": prompt}])
            answer = (resp.content or "").strip()
            if not answer:
                answer = "I don't know based on your materials."
        else:
            answer = extractive_answer_from_context(context_block)

        # Display
        print("\n---\n")
        type_out(answer + "\n")

        # Show brief sources
        print("\n### Sources used")
        for i, (doc, score) in enumerate(hits, 1):
            meta = doc.metadata or {}
            src = meta.get("source") or meta.get("file_path") or meta.get("document_name") or "Unknown"
            print(f"- [{i}] {src}  (relevance: {score:.2f})")
        print("\n---\n")

if __name__ == "__main__":
    main()
