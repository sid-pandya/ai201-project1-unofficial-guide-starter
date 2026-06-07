"""
Milestone 3: Document ingestion + chunking.

Loads the raw Reddit threads from documents/, strips the Reddit UI boilerplate
(vote buttons, promoted ads, timestamps, usernames, etc.), and splits each
cleaned document into ~500-character chunks with 100 characters of overlap,
snapping to word boundaries so we never cut a word in half.

Run directly to inspect the output:
    python ingest.py
"""

import glob
import os
import random
import re

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

# Lines that are pure Reddit chrome. Matched case-insensitively against the
# whole (stripped) line. These appear after almost every comment.
BOILERPLATE_LINES = {
    "upvote", "downvote", "reply", "award", "share", "go to comments",
    "join the conversation", "sort by:", "best", "search comments",
    "expand comment search", "comments section", "promoted", "learn more",
    "shop now", "order now", "collapse video player", "0:00 / 0:00",
    "op", "•", "cake icon", "[deleted]", "comment removed by moderator",
}

# Regex patterns for lines to drop entirely.
DROP_PATTERNS = [
    re.compile(r"^\d+$"),                       # bare vote counts: "8", "16"
    re.compile(r"^\d+\s*(mo|y|d|h|m)\s*ago$", re.I),   # "6mo ago", "2y ago"
    re.compile(r"^edited\s+\d+\s*(mo|y|d|h|m)\s*ago$", re.I),
    re.compile(r"^u/.*", re.I),                 # "u/Spectrum_Official avatar"
    re.compile(r".*\savatar$", re.I),           # "<name> avatar"
    re.compile(r"^\d+\s+more repl(y|ies)$", re.I),   # "1 more reply"
    re.compile(r"^(thumbnail image|clickable image).*", re.I),
    re.compile(r"^profile badge.*", re.I),
    re.compile(r"^top \d+% commenter$", re.I),
    re.compile(r"^[a-z0-9.\-]+\.(com|org|net|gov)\b.*$", re.I),  # ad domain lines
]

# Marketing copy that slips through because it reads like a sentence. We detect
# promoted ad *blocks* instead of listing every brand: once we see "Promoted",
# skip until the block clearly ends (a domain line, thumbnail, or video marker).
AD_BLOCK_END = re.compile(
    r"(\.(com|org|net)\b|thumbnail image|clickable image|collapse video player|0:00 / 0:00)",
    re.I,
)


def clean_text(raw: str) -> str:
    """Strip Reddit UI noise and promoted ads, keep the substantive text."""
    lines = raw.splitlines()
    kept = []
    skipping_ad = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            kept.append("")          # preserve paragraph breaks between comments
            continue

        # We're inside a promoted-ad block: drop lines until the block ends.
        if skipping_ad:
            if AD_BLOCK_END.search(stripped):
                skipping_ad = False
            continue

        low = stripped.lower()

        # "Promoted" marks the start of an ad; the username/avatar lines just
        # above it are already dropped by DROP_PATTERNS.
        if low == "promoted":
            skipping_ad = True
            continue

        if low in BOILERPLATE_LINES:
            continue
        if any(p.match(stripped) for p in DROP_PATTERNS):
            continue

        kept.append(stripped)

    # Collapse 3+ blank lines down to a single blank line.
    text = "\n".join(kept)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def load_documents(directory: str = DOCUMENTS_DIR):
    """Load every .txt file. Returns list of dicts with source, title, text."""
    docs = []
    for path in sorted(glob.glob(os.path.join(directory, "*.txt"))):
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        source = os.path.basename(path)
        title = raw.splitlines()[0].strip() if raw.strip() else source
        docs.append({"source": source, "title": title, "text": clean_text(raw)})
    return docs


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    """Sliding-window chunks of ~`size` chars with `overlap`, on word boundaries."""
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = start + size
        if end < n:
            # extend forward to the next space so we don't cut a word
            space = text.find(" ", end)
            end = space if space != -1 else n
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        # step back `overlap` chars, then snap to a word boundary
        start = end - overlap
        prev_space = text.rfind(" ", 0, start)
        if prev_space != -1 and prev_space > 0:
            start = prev_space + 1

    return chunks


def build_chunks(directory: str = DOCUMENTS_DIR):
    """Full pipeline: load -> clean -> chunk. Returns flat list of chunk dicts."""
    all_chunks = []
    for doc in load_documents(directory):
        for i, chunk in enumerate(chunk_text(doc["text"])):
            all_chunks.append({
                "id": f"{doc['source']}::chunk_{i}",
                "text": chunk,
                "source": doc["source"],
                "title": doc["title"],
                "chunk_index": i,
            })
    return all_chunks


if __name__ == "__main__":
    docs = load_documents()
    chunks = build_chunks()

    print(f"Loaded {len(docs)} documents.")
    print(f"Produced {len(chunks)} chunks "
          f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}).\n")

    print("Chunks per document:")
    for doc in docs:
        count = sum(1 for c in chunks if c["source"] == doc["source"])
        print(f"  {count:3d}  {doc['source']}")

    print("\n" + "=" * 70)
    print("5 RANDOM SAMPLE CHUNKS (read these — are they clean & self-contained?)")
    print("=" * 70)
    for c in random.sample(chunks, min(5, len(chunks))):
        print(f"\n[{c['id']}]  ({len(c['text'])} chars)")
        print(c["text"])
        print("-" * 70)
