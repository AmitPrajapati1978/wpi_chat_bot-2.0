# WPI AI Navigation Assistant
### An Agentic RAG System for Intelligent University Website Navigation

---

## 1. Project Overview

This project is an AI-powered question-answering assistant built specifically for the Worcester Polytechnic Institute (WPI) website (`wpi.edu`). A student can ask any natural language question about WPI — tuition, dining, research, events, sports — and the system navigates the website in real time to find and return a grounded, accurate answer.

The system does **not** rely on pre-stored knowledge or a static database. Every answer is derived from live content retrieved directly from WPI's website at the time of the question.

---

## 2. System Architecture

The pipeline consists of four sequential stages:

```
User Question
     │
     ▼
┌─────────────────────────────┐
│  Stage 1: Section Selector  │  → Claude Haiku identifies top 3 relevant
│                             │    sections from WPI's navigation menu
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│  Stage 2: Link Explorer     │  → Fetches pages in parallel, uses Claude
│  (Hierarchical Beam Search) │    Haiku to rank links at each depth level
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│  Stage 3: Page Fetcher      │  → Fetches final pages in parallel,
│                             │    extracts clean text content
└─────────────────────────────┘
     │
     ▼
┌─────────────────────────────┐
│  Stage 4: Answer Generator  │  → Groq (Llama 3.3 70B) synthesizes
│                             │    a friendly, formatted answer
└─────────────────────────────┘
```

### Technology Stack

| Component | Technology |
|---|---|
| Section & Link Ranking | Claude Haiku 4.5 (Anthropic) |
| Answer Generation | Llama 3.3 70B (Groq — free tier) |
| Web Scraping | Python `requests` + `BeautifulSoup4` |
| Parallelism | `concurrent.futures.ThreadPoolExecutor` |
| Frontend | Streamlit |
| Environment | Python 3.9, virtualenv |

---

## 3. How It Works — Step by Step

### Stage 1 — Section Selector
The system maintains a dictionary of ~40 WPI website sections, each with a key, description, and URL (e.g., `housing_and_dining`, `graduate_studies`, `research`). Claude Haiku reads the user's question and selects the **top 3 most relevant sections** to explore, returning a ranked JSON array.

### Stage 2 — Link Explorer (Hierarchical Beam Search)
Starting from the 3 section URLs, the system explores the website **depth-by-depth** up to a configurable depth (default: 3):

- **All pages at the same depth are fetched in parallel** using a thread pool
- **All links from all pages at a given depth are aggregated** into a single batch
- **One Claude Haiku call per depth level** ranks and selects the top-N most relevant links to follow
- This continues until max depth is reached or no new links are found
- A **final ranking call** selects the top 5 candidate pages across all depths

### Stage 3 — Page Fetcher
The top 5 pages are fetched in parallel. HTML boilerplate (nav, header, footer, scripts) is stripped and clean main content text is extracted. Content is trimmed to 3,000 characters per page to keep the final prompt manageable.

### Stage 4 — Answer Generator
All retrieved page content is passed to Llama 3.3 70B via Groq with a carefully crafted system prompt. The model is instructed to answer only from the provided content, use a conversational tone, and include source URLs.

---

## 4. How This Differs from Typical RAG

Standard Retrieval-Augmented Generation (RAG) works like this:

```
Documents → Chunked → Embedded into Vector DB → Query → Similarity Search → LLM Answer
```

This project uses a fundamentally different approach:

| Dimension | Traditional RAG | This System (Agentic RAG) |
|---|---|---|
| **Knowledge storage** | Pre-built vector database | No database — live website |
| **Retrieval method** | Semantic similarity search | Active web navigation |
| **Navigation** | None — direct lookup | Hierarchical, multi-depth exploration |
| **Freshness** | Stale (needs re-indexing) | Always up-to-date |
| **Setup cost** | High (crawl, chunk, embed) | Zero — no pre-processing |
| **Decision-making** | Embedding cosine distance | LLM reasoning at every step |
| **Scope** | Fixed at index time | Dynamic — follows links |
| **Infrastructure** | Vector DB required | No external storage needed |

The key insight is: **instead of asking "what documents are similar to this query?", the system asks "where on this website would a human researcher look?"**

---

## 5. Advantages of This Approach

### ✅ Always Fresh
Because the system navigates the live website at query time, there is no risk of serving outdated information. If WPI updates their tuition page today, the bot reflects that immediately.

### ✅ No Pre-processing Required
Traditional RAG requires crawling the entire website, chunking text, generating embeddings, and storing them in a vector database. This system requires zero setup — it works on any website out of the box.

### ✅ Intelligent Navigation
By using an LLM at each navigation step, the system understands intent, not just keywords. It navigates like a knowledgeable human researcher rather than a keyword matcher.

### ✅ Cost Efficient
By using Claude Haiku (cheap) for simple ranking tasks and Groq's free Llama 3.3 70B for answer generation, the cost per question is approximately **$0.005** — nearly free.

### ✅ Parallelism
HTTP fetches at each depth level are parallelized using thread pools. Link ranking across an entire depth is batched into a single LLM call. This reduces response time from ~2.5 minutes (sequential) to ~30 seconds.

---

## 6. Limitations and Flaws

### ⚠️ Latency (~30 seconds per question)
Even with parallelism, navigating 3 depth levels with multiple HTTP requests and LLM calls takes ~30 seconds. Traditional RAG with a vector DB returns answers in 2–5 seconds. This is a fundamental tradeoff of live navigation vs. pre-indexing.

### ⚠️ 403 / Access-Blocked Pages
Some WPI pages (e.g., `/students`) return HTTP 403 Forbidden to non-browser scrapers. The system skips these gracefully, but relevant content behind authentication walls is inaccessible.

### ⚠️ JavaScript-Rendered Content
The system uses standard HTTP requests. Pages that load content dynamically via JavaScript (React, Angular SPAs) may return empty or incomplete HTML, causing the system to miss relevant content.

### ⚠️ Link Drift at Depth 3
At deeper exploration levels, Claude occasionally selects generic navigation links (e.g., "About", "Contact") when pages don't contain more specific relevant links. A blocklist of common navigation paths partially mitigates this.

### ⚠️ No Conversation Memory
Each question is treated independently. The system has no memory of previous questions in the same session, so follow-up questions like "tell me more about that" won't work correctly.

### ⚠️ Content Truncation
Page content is capped at 3,000 characters per page to keep the final LLM prompt within limits. For very content-rich pages, important information near the bottom may be cut off.

### ⚠️ Rate Limits on Groq Free Tier
Groq's free tier has a rate limit of ~30 requests per minute. Under high concurrent usage, answer generation could be throttled or fail.

---

## 7. Possible Improvements

| Improvement | Impact |
|---|---|
| Add Redis/disk caching for page content | Faster repeated queries |
| Use `playwright` for JS-rendered pages | Access dynamic content |
| Add conversation memory | Support multi-turn Q&A |
| Stream the answer token by token | Better UX (feels faster) |
| Add a confidence score | Indicate when answer is uncertain |
| Hybrid approach: cache popular pages in a vector DB | Reduce latency for common queries |

---

## 8. Sample Outputs

*Screenshots to be added below*

### Q: "Where can I have food on campus?"
> *(Add screenshot here)*

### Q: "What are the tuition fees for graduate students?"
> *(Add screenshot here)*

### Q: "What fun things can I do at WPI?"
> *(Add screenshot here)*

### Q: "Does WPI have a robotics research lab?"
> *(Add screenshot here)*

---

## 9. Project File Structure

```
WPICHAT_BOT/
├── app.py                  # Streamlit frontend
├── section_selector.py     # Stage 1: identify top 3 sections
├── link_explorer.py        # Stage 2: hierarchical beam search
├── page_fetcher.py         # Stage 3: parallel page content extraction
├── answer_generator.py     # Stage 4: Groq LLM answer synthesis
├── main.py                 # CLI version of the full pipeline
├── resources/
│   ├── wpi.jpg             # Background image
│   ├── wpi_logo.jpeg       # WPI logo
│   └── wpi_bg.jpeg         # Alternate background
├── .env                    # API keys (not committed)
└── venv/                   # Python virtual environment
```

---

## 10. Summary

This project demonstrates that an intelligent AI assistant for a university website can be built **without any pre-indexing, vector databases, or infrastructure** — using only LLM reasoning and live web navigation. The architecture is a form of **Agentic RAG**, where an LLM agent actively explores the information space rather than passively retrieving from a pre-built index.

The tradeoff versus traditional RAG is **latency for freshness and simplicity** — a worthwhile tradeoff in contexts where up-to-date information matters and setup cost is a constraint.
