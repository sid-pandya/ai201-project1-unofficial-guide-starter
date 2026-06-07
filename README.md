# The Unofficial Guide — Project 1

A Retrieval-Augmented Generation (RAG) system that answers plain-language
questions about life as a **Cal State East Bay (CSUEB)** student, grounded only
in real r/CSUEB and East Bay student forum threads.

**Pipeline:** `documents/` → clean + chunk ([ingest.py](ingest.py)) → embed with
all-MiniLM-L6-v2 + store in ChromaDB ([embed.py](embed.py)) → retrieve top-k →
grounded answer from Groq llama-3.3-70b ([query.py](query.py)) → Gradio UI
([app.py](app.py)).

```bash
python embed.py     # build the vector store + run a retrieval smoke test
python app.py       # launch the web UI at http://localhost:7860
python evaluate.py  # run the 5 evaluation questions end-to-end
```

---

## Domain

**The Hayward Commuter & Lifestyle Matrix** — hyper-local survival knowledge for
CSUEB students: off-campus living, transit optimization (BART, AC Transit, the
campus shuttle), campus life, and vegetarian-friendly dining around the East Bay.

This knowledge is valuable because official university pages don't capture the
daily reality of commuting _up the hill_ by public transit, which surrounding
cities are actually affordable, or which nearby restaurants students rate. It
lives scattered across Reddit threads, where the useful facts are buried among
jokes, ads, and contradictory opinions.

---

## Document Sources

10 Reddit threads, saved as cleaned `.txt` files in [documents/](documents/).

| #   | Source (file)                                      | Type             | URL                                                                                                 |
| --- | -------------------------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------- |
| 1   | Students debating gas vs. shuttle & AC transit     | Reddit r/bayarea | https://www.reddit.com/r/bayarea/comments/19dvftz/better_to_bart_or_to_drive/                       |
| 2   | How's commuting by BART?                           | Reddit r/CSUEB   | https://www.reddit.com/r/CSUEB/comments/1ppuyb1/hows_commuting_by_bart/                             |
| 3   | The Hayward BART Shuttle Experience                | Reddit r/CSUEB   | https://www.reddit.com/r/CSUEB/comments/15zewmy/hayward_bart_shuttle/                               |
| 4   | Commuting from Surrounding Cities                  | Reddit r/eastbay | https://www.reddit.com/r/eastbay/comments/1orv92m/transferring_for_school/                          |
| 5   | What's it actually like living near campus?        | Reddit r/CSUEB   | https://www.reddit.com/r/CSUEB/comments/1qbocxu/for_students_that_live_near_campus_whats_it_like/   |
| 6   | Honest Reviews of CSUEB Housing & Dorms            | Reddit r/CSUEB   | https://www.reddit.com/r/CSUEB/comments/1gjhjcl/housing/                                            |
| 7   | Honest Opinion about CSUEB Campus Life             | Reddit r/CSUEB   | https://www.reddit.com/r/CSUEB/comments/1t1c8ky/what_is_your_honest_opinion_about_csueb/            |
| 8   | Vegetarian-Friendly Family Restaurants in East Bay | Reddit r/eastbay | https://www.reddit.com/r/eastbay/comments/1thgd6b/best_smaller_familyowned_vegetarianfriendly_type/ |
| 9   | The Best Vegetarian Spots in the Bay Area          | Reddit r/bayarea | https://www.reddit.com/r/bayarea/comments/1qv3nyo/what_are_the_very_best_vegetarianfriendly_bay/    |
| 10  | Favorite Vegan/Vegetarian Eats Around Town         | Reddit r/eastbay | https://www.reddit.com/r/eastbay/comments/1b9atub/favorite_veganvegetarian_eats/                    |

---

## Chunking Strategy

**Chunk size:** 500 characters
**Overlap:** 100 characters
**Final chunk count:** 52 chunks across 10 documents

**Preprocessing (before chunking).** Reddit pastes are full of UI noise, so
[ingest.py](ingest.py) strips: vote buttons (`Upvote`/`Downvote`/`Reply`/
`Award`/`Share`), navigation (`Go to comments`, `Sort by:`, `Comments Section`),
timestamps (`6mo ago`, `2y ago`), `u/...` / `avatar` lines, bare vote counts,
ad domains, and entire **promoted-ad blocks** (everything from a `Promoted`
marker to the trailing domain/thumbnail line). It also pops the bare brand
username that sits just above `Promoted` (e.g. `Heineken_US`). It deliberately
does **not** strip all standalone usernames, because real one-word comments
("Hayward", "Drive", "Mazra") are genuine content.

**Why these choices fit the documents.** The corpus is short, opinionated
comments (1–4 sentences, ~200–400 chars each), not long-form guides. A 500-char
chunk usually holds one complete opinion plus a little surrounding context,
without blurring several unrelated comments into one diluted embedding. The
100-char overlap is a safety net: when a comment is split across a boundary, the
shared text keeps the key fact intact in at least one chunk. We confirmed 52
chunks sits comfortably in the healthy 50–2000 range (we planned to drop to ~400
chars if it had come out under 50, but it didn't).

### Sample chunks (5, with source)

1. **The Hayward BART Shuttle Experience.txt** — _"...how's the experience like getting to and from campus back to Hayward BART?--it's been unreliable at times... how long does it take to make it to campus from BART.--20 minutes... how long does it take to make it BACK to BART from campus--Same, 20 minutes."_
2. **Commuting from Surrounding Cities.txt** — _"...It's in Hayward which is one of the cheaper areas of the Bay ... The campus is in Hayward. Hayward, San Leandro, Union City, and Castro Valley are the surrounding cities/towns. Oakland and Berkeley are farther but close by."_
3. **Honest Reviews of CSUEB Housing & Dorms.txt** — _"When I dormed it was alright. My building was respectful of noise in general but some of the other ones were not. Some dorms held parties and got pretty loud and even had ambulances called out... The internet is extremely bad here and the AC/heating d[oesn't work]."_
4. **The Best Vegetarian Spots in the Bay Area.txt** — _"Greens in SF and Millennium in Oakland are both kinda 'upscale' but delicious. Veggie Lee in Hayward is a vegan chinese restaurant that is delicious... Falafelle in Belmont is an excellent quick falafel sandwich. Flavor of India in San Lorenzo is good North Indian food."_
5. **What's it actually like living near campus?.txt** — _"...for every commuter there's also a small percentage that live near campus too. There's some dorms by the hill and apartments on Carlos Bee... I don't know if people go down to Hayward to eat or look around downtown."_

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` (sentence-transformers, 384-dim), run locally
— no API key, no rate limits, fast on CPU. Embeddings are L2-normalized and the
ChromaDB collection uses cosine distance (`hnsw:space: cosine`) so scores fall
in a 0–1 range (lower = more similar).

**Production tradeoff reflection.** For a real deployment with no cost
constraint, I'd evaluate a larger API model such as OpenAI `text-embedding-3-large`
or Voyage AI. MiniLM is cheap and private but can fumble informal internet text —
local slang and abbreviations like "AC60", "the hill", "RAW", or "Carlos Bee".
The tradeoffs I'd weigh: **accuracy** on domain-specific/slangy text, **context
length** (MiniLM truncates at 256 tokens, fine for short comments but limiting
for long guides), **multilingual** support if the student body needs it, and
**latency vs. privacy** — a hosted API adds per-call latency and network
dependence but offloads compute; local inference is private and free but can
bottleneck under high traffic.

---

## Grounded Generation

**System prompt grounding instruction.** The model is told to answer _only_ from
the provided context, with an explicit refusal fallback (see [query.py](query.py)):

> Answer strictly from the context below. Do NOT use any outside or general
> knowledge. If the context does not contain enough information to answer, reply
> with exactly: "I don't have enough information on that." These are opinions
> from different students; if they disagree, say so rather than inventing a
> consensus.

Temperature is set to **0.1** to keep responses tied to the retrieved text. The
retrieved chunks are passed in a numbered, source-labeled context block.

**How source attribution is surfaced.** Two layers: (1) the prompt asks the model
to cite source filenames inline, and (2) the application appends the unique list
of source documents **programmatically** from chunk metadata, so attribution is
guaranteed regardless of what the model writes. On a refusal, the source list is
suppressed (nothing was actually used).

---

## Retrieval Test Results

Top chunks for 3 queries (cosine distance; lower = closer). Full runs:
`python embed.py`.

**Query: "Which bus line is best from Hayward BART to campus, and its main issue?"**

- `[0.273]` How's commuting by BART? — "...BART + AC transit ... AC Transit added a longer bus to the 60 line"
- `[0.299]` Commuting from Surrounding Cities; `[0.301]` gas-vs-shuttle ("AC60 takes an hour")
- _Relevant:_ every top chunk is about the BART→campus transit options, and chunk #4 contains the specific "AC60 takes an hour" fact the question targets.

**Query: "What vegetarian restaurant in Hayward do students recommend?"**

- `[0.328]`/`[0.371]` The Best Vegetarian Spots — chunk #2 contains "Veggie Lee in Hayward is a vegan chinese restaurant"
- `[0.376]`/`[0.416]` Vegetarian-Friendly Family Restaurants (Orinda–Dublin)
- _Relevant (but diluted):_ the right answer (Veggie Lee) is retrieved, but it's surrounded by Oakland/SF/Dublin recommendations — semantic search matches on "vegetarian," not on "in Hayward."

**Query: "Which nearby cities do students recommend for affordable housing?"**

- `[0.447]` Commuting from Surrounding Cities (the correct thread, on top)
- `[0.507]`/`[0.518]` What's it like living near campus
- _Relevant:_ the top result is the dedicated housing/relocation thread that names Hayward, Union City, and San Leandro.

---

## Example Responses

**1. In-scope, cited:**

> **Q:** Is the campus shuttle free for CSUEB students?
> **A:** Yes, the campus shuttle is free for CSUEB students. (source: Students debating the cost of gas vs. the time it takes to use the campus shuttle and AC transit.txt)
> **Sources:** Students debating…txt, How's commuting by BART?.txt, Honest Opinion about CSUEB Campus Life.txt

**2. In-scope, cited:**

> **Q:** What vegetarian restaurant in Hayward do students recommend?
> **A:** Veggie Lee, a vegan Chinese restaurant, is recommended by students in Hayward (The Best Vegetarian Spots in the Bay Area.txt).
> **Sources:** The Best Vegetarian Spots in the Bay Area.txt, …

**3. Out-of-scope (refusal):**

> **Q:** Which CSUEB professor gives the best feedback on essays?
> **A:** I don't have enough information on that.
> **Sources:** (none — refused)

The corpus contains nothing about professors, so the system declines rather than
fabricating an answer.

---

## Query Interface

A Gradio web UI ([app.py](app.py), `python app.py` → http://localhost:7860).

- **Input:** a single text box for a plain-language question (plus clickable
  example questions).
- **Output:** three fields — **Answer** (grounded response), **Sources**
  (documents used), and **Retrieved chunks** (the raw evidence with distance
  scores, so a viewer can see what the answer was built from).

**Sample interaction:**

> **Input:** _"How long does the Hayward BART shuttle take?"_
> **Answer:** _"It takes about 20 minutes from BART to campus and 20 minutes back, though students note it can be unreliable and sometimes doesn't show up (The Hayward BART Shuttle Experience.txt)."_
> **Sources:** • The Hayward BART Shuttle Experience.txt
> **Retrieved chunks:** `[1] The Hayward BART Shuttle Experience.txt (distance 0.30) ...20 minutes... Same, 20 minutes...`

---

## Evaluation Report

Run with `python evaluate.py`. Retrieval k = 5.

| #   | Question                                               | Expected answer                                                      | System response (summarized)                                                                                                                            | Retrieval          | Accuracy               |
| --- | ------------------------------------------------------ | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ---------------------- |
| 1   | Best bus line from Hayward BART to campus + main issue | AC Transit Line 60; slow (~an hour), fills up quickly                | Identified the **60 line**, but cited the main issue as "wait time about the same as before" rather than the stronger "takes an hour / fills up" detail | Relevant           | **Partially accurate** |
| 2   | How can students reduce transit fare costs?            | Clipper START Card (50% off, income-qualified); free AC Transit card | Correctly gave **Clipper START, 50% off**; **missed** the free AC Transit card                                                                          | Partially relevant | **Partially accurate** |
| 3   | Is the campus shuttle free for students?               | Yes, free for students                                               | "Yes, the campus shuttle is free for CSUEB students," cited                                                                                             | Relevant           | **Accurate**           |
| 4   | Nearby cities for affordable housing                   | Hayward, Union City (E of 880), San Leandro; avoid north             | Hayward, San Leandro, Union City, Castro Valley; missed "avoid north"                                                                                   | Relevant           | **Accurate**           |
| 5   | Vegetarian restaurant in Hayward                       | Veggie Lee (vegan Chinese)                                           | "Veggie Lee, a vegan Chinese restaurant... in Hayward," cited                                                                                           | Relevant (diluted) | **Accurate**           |

---

## Failure Case Analysis

**Question that failed:** _"How can CSUEB students reduce their transit fare costs?"_ (Q2)

**What the system returned:** Only the Clipper START Card (50% off for
income-qualified students). It **missed** a second valid answer — the **free AC
Transit card** that students can pick up.

**Root cause (retrieval / embedding stage).** The "free AC Transit card" fact
appears in the _"What's it actually like living near campus?"_ thread, embedded
in a comment about **playing video games**: _"i just stay in my room and play
video games but there's always the RAW and university union gaming room... Though
i did pick up my free AC Transit card."_ In embedding space, a query about
"reducing transit fare costs" is far from a comment dominated by gaming and
campus-life vocabulary, so that chunk ranked well below the top 5 and never
reached the LLM. With no such context, the model couldn't include it — the
generation was correct _given_ what it received; the gap was upstream in
retrieval. (Q1 is a secondary partial: there, the relevant "AC60 takes an hour"
chunk _was_ retrieved at rank 4, but the model anchored on the highest-ranked
chunk's weaker phrasing — a generation-stage issue, not retrieval.)

**What I would change to fix it.** Either (a) increase k or add a re-ranking
pass so lower-ranked-but-relevant chunks get a second look, (b) add **hybrid
search** (BM25 keyword + semantic) so the literal phrase "AC Transit card" can
surface even when the surrounding text is off-topic, or (c) chunk by comment so
the fare-card sentence isn't diluted by the gaming context around it.

---

## Spec Reflection

**One way the spec helped me.** Writing the Chunking Strategy and Anticipated
Challenges sections _before_ coding paid off directly. The chunking section gave
[ingest.py](ingest.py) an exact target (500 chars / 100 overlap, word-boundary
aware), so there was no guessing during implementation. And the "geographic
dilution" risk I named in planning turned out to predict the system's real
behavior almost exactly — the vegetarian queries retrieve restaurants from all
over the Bay Area, not just Hayward, which is precisely what I'd flagged.

**One way my implementation diverged from the spec, and why.** Two divergences.
First, the planned interface was `gradio>=6.9.0`, but this machine's venv runs
Python 3.9 and Gradio 6.x requires 3.10+, so I pinned **gradio 4.44.1** (last
3.9-compatible release; identical `gr.Blocks` API). Second, I changed evaluation
**Q2** during implementation: the original expected answer (pay with a
contactless card vs. single tickets) wasn't actually supported anywhere in the
corpus, so grading against it would have been meaningless. I rewrote it around
the Clipper START / free AC Transit card facts that the documents really contain.

---

## AI Usage

**Instance 1 — Ingestion + cleaning ([ingest.py](ingest.py)).**

- _What I gave the AI:_ my Documents and Chunking Strategy sections from
  planning.md, plus a raw sample of a pasted Reddit thread showing the noise
  (vote buttons, promoted ads, timestamps).
- _What it produced:_ an `ingest.py` with a boilerplate blocklist, regex drops
  for timestamps/usernames/ad domains, a promoted-ad-block skipper, and a
  word-boundary-aware 500/100 chunker.
- _What I changed/directed:_ after inspecting the output, ad-brand usernames like
  `Heineken_US` were still leaking, so I directed a targeted rule to pop the bare
  username line directly above each `Promoted` marker. I also explicitly decided
  **not** to strip all standalone usernames, because that would have deleted real
  one-word recommendations ("Hayward", "Drive", "Mazra").

**Instance 2 — Embedding + retrieval ([embed.py](embed.py)).**

- _What I gave the AI:_ my Retrieval Approach section and the architecture diagram.
- _What it produced:_ an `embed.py` that embeds chunks with all-MiniLM-L6-v2 and
  stores them in ChromaDB with source metadata, plus a `retrieve(query, k)`
  function.
- _What I changed/overrode:_ I overrode the default distance metric to **cosine**
  (`hnsw:space: cosine`) and normalized the embeddings, so distance scores land in
  the 0–1 range the rubric describes, instead of ChromaDB's default squared-L2 —
  which made the retrieval scores actually interpretable when judging quality.

  # The Unofficial Guide — Project 1

🎥 **[Click here to watch the video demonstration](https://www.youtube.com/watch?v=WKoYSEeL1HU)**
