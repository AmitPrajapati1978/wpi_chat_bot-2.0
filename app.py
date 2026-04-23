import base64
import time
import markdown as md
import streamlit as st

def get_base64_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg_image = get_base64_image("resources/wpi.jpg")
from section_selector import select_sections
from link_explorer import explore
from page_fetcher import fetch_pages
from answer_generator import generate_answer
from semantic_cache import find_cached_answer
from logger import log_interaction


st.set_page_config(
    page_title="WPI AI Assistant",
    page_icon="🦙",
    layout="centered",
)

# ── WPI Theme ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Import font */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* Background image from WPI website */
[data-testid="stAppViewContainer"] {
    background-image: url("PLACEHOLDER_BG");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
    font-family: 'Inter', sans-serif;
}

/* Dark overlay so text is readable */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0, 0, 0, 0.55);
    z-index: 0;
}

/* Main content card */
[data-testid="stMainBlockContainer"] {
    position: relative;
    z-index: 1;
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 2rem;
    margin-top: 2rem;
    border: 1px solid rgba(255,255,255,0.15);
}

/* All text white */
html, body, [class*="css"], p, span, label, div {
    color: #ffffff !important;
}

/* Title */
h1, h2, h3 {
    color: #ffffff !important;
    font-weight: 700 !important;
}

/* Crimson accent on title */
.wpi-title {
    color: #AC2B37 !important;
    font-size: 2.4rem;
    font-weight: 700;
    text-shadow: 0 2px 8px rgba(0,0,0,0.4);
}

.wpi-subtitle {
    color: rgba(255,255,255,0.75) !important;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}

/* Input box */
[data-testid="stTextInput"] input {
    background: rgba(20, 20, 20, 0.75) !important;
    border: 1px solid rgba(172, 43, 55, 0.6) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-size: 1rem !important;
    padding: 0.6rem 1rem !important;
}

[data-testid="stTextInput"] input::placeholder {
    color: rgba(255,255,255,0.45) !important;
}

[data-testid="stTextInput"] input:focus {
    border-color: #AC2B37 !important;
    box-shadow: 0 0 0 2px rgba(172,43,55,0.3) !important;
    background: rgba(20, 20, 20, 0.9) !important;
}

/* Primary button — WPI crimson */
[data-testid="stButton"] button[kind="primary"] {
    background: #AC2B37 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    padding: 0.6rem !important;
    transition: background 0.2s;
}

[data-testid="stButton"] button[kind="primary"]:hover {
    background: #8a2230 !important;
}

/* Answer box */
.answer-box {
    background: rgba(255,255,255,0.1);
    border-left: 4px solid #AC2B37;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-top: 1rem;
    line-height: 1.7;
}

.answer-box a {
    color: #7ec8e3 !important;
    text-decoration: underline !important;
}

.answer-box a:hover {
    color: #ffffff !important;
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

/* Divider */
hr {
    border-color: rgba(255,255,255,0.15) !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Inject background image separately to avoid f-string/CSS brace conflicts
st.markdown(
    f'<style>[data-testid="stAppViewContainer"] {{ background-image: url("data:image/jpeg;base64,{bg_image}"); }}</style>',
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="wpi-title">🦙 WPI AI Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="wpi-subtitle">Your friendly guide to everything Worcester Polytechnic Institute</div>', unsafe_allow_html=True)
st.markdown("---")

# ── Input ──────────────────────────────────────────────────────────────────────
question = st.text_input(
    label="What do you want to know?",
    placeholder="e.g. What fun things can I do? Where can I eat? What are tuition fees?",
)

ask = st.button("Ask →", type="primary", use_container_width=True)

# ── Meta question handler ──────────────────────────────────────────────────────
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

# ── Pipeline ───────────────────────────────────────────────────────────────────
if ask and question.strip():
    q_lower = question.strip().lower()
    if any(kw in q_lower for kw in META_KEYWORDS):
        st.markdown("---")
        st.markdown(f'<div class="answer-box">{md.markdown(META_ANSWER)}</div>', unsafe_allow_html=True)
        st.stop()

    start_time = time.time()

    # ── Cache check ────────────────────────────────────────────────────────────
    cached_answer = find_cached_answer(question)
    if cached_answer:
        elapsed = int((time.time() - start_time) * 1000)
        log_interaction(question, cached_answer, cache_hit=True, response_time_ms=elapsed)
        st.markdown("---")
        st.markdown(f'<div class="answer-box">{md.markdown(cached_answer)}</div>', unsafe_allow_html=True)
        st.caption("⚡ Answered instantly from cache")
        st.stop()

    # ── Full pipeline ──────────────────────────────────────────────────────────
    with st.status("On it! 🔍", expanded=False) as status:

        sections = select_sections(question)
        start_urls = [s["url"] for s in sections]
        top_pages = explore(question, start_urls, max_depth=3, top_n=3)

        if not top_pages:
            status.update(label="Hmm, couldn't find anything.", state="error")
            st.error("Try rephrasing your question!")
            st.stop()

        pages = fetch_pages(top_pages)
        answer = generate_answer(question, pages)

        status.update(label="Here you go! 🎉", state="complete", expanded=False)

    elapsed = int((time.time() - start_time) * 1000)
    log_interaction(question, answer, cache_hit=False, response_time_ms=elapsed)

    st.markdown("---")
    st.markdown(f'<div class="answer-box">{md.markdown(answer)}</div>', unsafe_allow_html=True)
    st.markdown("---")

    with st.expander("🔗 Sources used"):
        for p in top_pages:
            url = p.get("url", "")
            label = p.get("title", url)
            if url.startswith("http"):
                st.markdown(f"- [{label}]({url})")
            else:
                st.markdown(f"- {label}")

elif ask and not question.strip():
    st.warning("Hey, don't forget to type your question! 😄")
