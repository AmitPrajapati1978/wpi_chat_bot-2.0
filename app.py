import base64
import time
import uuid
import streamlit as st

def get_base64_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg_image = get_base64_image("resources/wpi.jpg")
from section_selector import select_sections
from link_explorer import explore
from page_fetcher import fetch_pages
from answer_generator import stream_answer
from semantic_cache import find_cached_answer
from guardrail import check_guardrail
from logger import log_interaction
from query_rewriter import rewrite_query


st.set_page_config(
    page_title="WPI AI Assistant",
    page_icon="🦙",
    layout="centered",
)

# ── WPI Theme ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* Full page background */
[data-testid="stAppViewContainer"] {
    background-image: url("PLACEHOLDER_BG");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    font-family: 'Inter', sans-serif;
}

[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0, 0, 0, 0.65);
    z-index: 0;
}

/* Remove card — full page chat layout */
[data-testid="stMainBlockContainer"] {
    position: relative;
    z-index: 1;
    background: transparent !important;
    padding: 1rem 2rem;
    max-width: 800px;
    margin: 0 auto;
}

html, body, [class*="css"], p, span, label, div {
    color: #ffffff !important;
}

h1, h2, h3 {
    color: #ffffff !important;
    font-weight: 700 !important;
}

.wpi-title {
    color: #AC2B37 !important;
    font-size: 2rem;
    font-weight: 700;
    text-shadow: 0 2px 8px rgba(0,0,0,0.4);
}

.wpi-subtitle {
    color: rgba(255,255,255,0.65) !important;
    font-size: 0.95rem;
    margin-bottom: 0.5rem;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    margin-bottom: 0.5rem !important;
    backdrop-filter: blur(8px) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}

/* Chat input bar at bottom */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div {
    background: rgba(0,0,0,0.6) !important;
    backdrop-filter: blur(12px) !important;
    border-top: none !important;
}

.stChatInputContainer,
.stChatInputContainer > div {
    background: transparent !important;
}

[data-testid="stChatInput"] textarea {
    background: rgba(30, 30, 30, 0.85) !important;
    border: 1px solid rgba(172, 43, 55, 0.6) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    caret-color: #ffffff !important;
    font-size: 1rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: rgba(255,255,255,0.45) !important;
}

[data-testid="stChatInput"] textarea:focus {
    border-color: #AC2B37 !important;
    box-shadow: 0 0 0 2px rgba(172,43,55,0.3) !important;
}

/* Expander */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
}

/* Status box */
[data-testid="stStatus"] {
    background: rgba(255,255,255,0.08) !important;
    border: 1px solid rgba(172,43,55,0.4) !important;
    border-radius: 10px !important;
}

hr { border-color: rgba(255,255,255,0.15) !important; }

#MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown(
    f'<style>[data-testid="stAppViewContainer"] {{ background-image: url("data:image/jpeg;base64,{bg_image}"); }}</style>',
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="wpi-title">🦙 WPI AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="wpi-subtitle">Your friendly guide to everything Worcester Polytechnic Institute</div>', unsafe_allow_html=True)

# ── Session state init ─────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "turn_number" not in st.session_state:
    st.session_state.turn_number = 0

# ── Meta answer ────────────────────────────────────────────────────────────────
META_KEYWORDS = ("what can you", "what do you know", "what domains", "what topics",
                 "what questions", "what can i ask", "help me", "what are you")

META_ANSWER = """Here's what I can help you with at WPI:

- **Degree programs** — every major, minor, and certificate (undergrad + grad)
- **Course catalog** — 1,320 courses with descriptions and prerequisites
- **Student clubs & orgs** — all 252 clubs from myWPI
- **Career outcomes** — average salaries by program, employment rates (Class of 2025)
- **Job & career outlook** — BLS data for 343 career paths linked to WPI degrees
- **Student voices** — first-hand stories from current and former students
- **Research areas** — AI, bioengineering, cybersecurity, sustainability, and more
- **Labs & facilities** — 1,000 campus labs, makerspaces, and research centers
- **IQP / MQP projects** — project titles, sponsors, and global project centers
- **Departments & offices** — all 39 departments and 63 campus offices

Things I **can't** reliably answer yet: tuition costs, housing/dining details, admissions deadlines, athletics, or news & events — those aren't in my data source yet.

Try asking something like:
- *"What is the average salary for a WPI CS graduate?"*
- *"What robotics clubs can I join?"*
- *"What does the AI master's program look like?"*"""

# ── Render chat history ────────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Chat input ─────────────────────────────────────────────────────────────────
if raw_input := st.chat_input("Ask me anything about WPI..."):

    # Show user message
    with st.chat_message("user"):
        st.markdown(raw_input)
    st.session_state.messages.append({"role": "user", "content": raw_input})

    # ── Meta check ────────────────────────────────────────────────────────────
    if any(kw in raw_input.strip().lower() for kw in META_KEYWORDS):
        with st.chat_message("assistant"):
            st.markdown(META_ANSWER)
        st.session_state.messages.append({"role": "assistant", "content": META_ANSWER})
        st.stop()

    start_time = time.time()

    # ── Rewrite query if follow-up ─────────────────────────────────────────────
    history_so_far = st.session_state.messages[:-1]  # exclude current message
    rewritten = rewrite_query(history_so_far, raw_input)

    # ── Guardrail ─────────────────────────────────────────────────────────────
    if not check_guardrail(rewritten):
        msg = "⚠️ I'm only able to answer questions about WPI — academics, programs, campus life, research, and career outcomes. Please ask me something related to Worcester Polytechnic Institute!"
        with st.chat_message("assistant"):
            st.markdown(msg)
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.stop()

    # ── Cache check ───────────────────────────────────────────────────────────
    cached_answer = find_cached_answer(rewritten)
    if cached_answer:
        elapsed = int((time.time() - start_time) * 1000)
        st.session_state.turn_number += 1
        log_interaction(
            question=rewritten,
            answer=cached_answer,
            cache_hit=True,
            response_time_ms=elapsed,
            session_id=st.session_state.session_id,
            turn_number=st.session_state.turn_number,
            raw_user_input=raw_input,
            rewritten_query=rewritten,
        )
        with st.chat_message("assistant"):
            st.markdown(cached_answer)
            st.caption("⚡ Answered instantly from cache")
        st.session_state.messages.append({"role": "assistant", "content": cached_answer})
        st.stop()

    # ── Full pipeline ─────────────────────────────────────────────────────────
    with st.status("Looking that up for you! 📚", expanded=False) as status:
        sections = select_sections(rewritten)
        start_urls = [s["url"] for s in sections]
        top_pages = explore(rewritten, start_urls, max_depth=3, top_n=3)

        if not top_pages:
            status.update(label="Hmm, couldn't find anything.", state="error")
            st.error("Try rephrasing your question!")
            st.stop()

        pages = fetch_pages(top_pages)
        status.update(label="Here you go! 🎉", state="complete", expanded=False)

    # ── Stream answer ─────────────────────────────────────────────────────────
    with st.chat_message("assistant"):
        placeholder = st.empty()
        answer = ""
        for chunk in stream_answer(rewritten, pages, history=history_so_far):
            answer += chunk
            placeholder.markdown(answer + "▌")
            time.sleep(0.02)
        placeholder.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

    elapsed = int((time.time() - start_time) * 1000)
    st.session_state.turn_number += 1
    sections_used = [{"key": s["section_key"], "url": s["url"]} for s in sections]
    log_interaction(
        question=rewritten,
        answer=answer,
        cache_hit=False,
        response_time_ms=elapsed,
        sources=pages,
        session_id=st.session_state.session_id,
        turn_number=st.session_state.turn_number,
        raw_user_input=raw_input,
        rewritten_query=rewritten,
        sections_used=sections_used,
    )
