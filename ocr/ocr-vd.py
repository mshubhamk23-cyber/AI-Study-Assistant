#!/usr/bin/env python3
"""
Fully automated FAISS index builder.
Just run:  python build_faiss.py
"""

import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# --------------------------------------------------------------------
# CONFIGURATION  (edit these 3 paths / parameters as needed)
# --------------------------------------------------------------------
INPUT_DIR = r"C:\Final LY_project\LY-proj-Flask\ocr\ocr_output"  # Directory containing .txt files (can have subfolders)
OUTPUT_BASE_DIR = "./output_vd"

# Embedding models to build indexes for
MODEL_NAMES = [
    "sentence-transformers/all-MiniLM-L6-v2",                      # English generalist
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # Multilingual
]

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
# --------------------------------------------------------------------


def build_faiss_indexes():
    print(f"[1/4] Scanning {INPUT_DIR} for .txt files...")
    documents = []
    processed_files = set()

    # Step 1: Load all .txt files
    for root, _, files in os.walk(INPUT_DIR):
        for fname in files:
            if not fname.lower().endswith(".txt"):
                continue
            path = os.path.join(root, fname)
            if path in processed_files:
                continue
            print(f"  - Loading: {path}")
            loader = TextLoader(path, autodetect_encoding=True)
            documents.extend(loader.load())
            processed_files.add(path)

    print(f"Loaded {len(documents)} documents from {len(processed_files)} files.")

    if not documents:
        raise ValueError("No .txt files found. Nothing to index.")

    # Step 2: Split documents into chunks
    print(f"[2/4] Splitting into chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(documents)
    print(f"Produced {len(chunks)} chunks.\n")

    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

    # Step 3: Build and save FAISS indexes
    print(f"[3/4] Building FAISS indexes for {len(MODEL_NAMES)} model(s)...")
    results = []

    for model_name in MODEL_NAMES:
        print(f"  - Using model: {model_name}")
        embeddings = HuggingFaceEmbeddings(model_name=model_name)

        # Build FAISS store
        store = FAISS.from_documents(documents=chunks, embedding=embeddings)

        # Safe folder name for saving
        safe_name = model_name.replace("/", "_")
        out_dir = os.path.join(OUTPUT_BASE_DIR, f"faiss_{safe_name}")
        os.makedirs(out_dir, exist_ok=True)

        print(f"    Saving index to: {out_dir}")
        store.save_local(out_dir)
        results.append((model_name, out_dir))

    # Step 4: Summary
    print("\n[4/4] Done. Indexes created successfully!\n")
    print(f"Scanned folder: {INPUT_DIR}")
    print(f"Output folder:  {OUTPUT_BASE_DIR}")
    print(f"Total documents: {len(documents)}")
    print(f"Total chunks:    {len(chunks)}\n")

    for model, path in results:
        print(f" → {model}\n    → {path}")

    print("\nAll FAISS indexes built and saved successfully.")


if __name__ == "__main__":
    build_faiss_indexes()