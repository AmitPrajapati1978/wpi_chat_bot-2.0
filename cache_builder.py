"""
One-time script to pre-generate Q&A pairs for the semantic cache.
Run: python cache_builder.py
Saves results to qa_cache.json (commit this file to GitHub).
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from sentence_transformers import SentenceTransformer
from main import ask_wpi

QUESTIONS = [
    # Degree programs
    "What undergraduate programs does WPI offer?",
    "What graduate degrees are available at WPI?",
    "Does WPI have a computer science program?",
    "What engineering majors can I study at WPI?",
    "What business programs does WPI offer?",
    "What minors are available at WPI?",
    "Does WPI offer online graduate programs?",

    # Course catalog
    "What CS courses does WPI offer?",
    "What are the prerequisites for advanced engineering courses at WPI?",
    "What math courses are required at WPI?",
    "What programming languages are taught at WPI?",
    "Does WPI offer machine learning courses?",
    "What data science courses are available at WPI?",

    # Student clubs and organizations
    "What clubs and organizations can I join at WPI?",
    "Does WPI have a robotics club?",
    "What sports clubs are at WPI?",
    "Are there cultural clubs at WPI?",
    "What Greek life options are at WPI?",
    "What entrepreneurship clubs does WPI have?",

    # Career and salaries
    "What is the average salary for WPI graduates?",
    "What is the employment rate for WPI CS graduates?",
    "How much do WPI engineering graduates earn?",
    "What companies hire WPI graduates?",
    "What are the career outcomes for WPI data science graduates?",
    "What is the average starting salary for WPI mechanical engineering graduates?",

    # Job and career outlook
    "What careers can I pursue with a WPI CS degree?",
    "What are the job prospects for WPI engineering graduates?",
    "What is the job outlook for robotics engineers?",
    "What careers are available for biomedical engineering graduates?",
    "What is the career path for a WPI business graduate?",

    # Student voices
    "What do WPI students say about the university?",
    "What is student life like at WPI?",
    "What do students think about WPI's project-based learning?",
    "What are the best things about WPI according to students?",
    "How do current WPI students describe their experience?",

    # IQP and MQP projects
    "What is the IQP at WPI?",
    "What is the MQP at WPI?",
    "Where can I do my IQP project?",
    "What are some examples of IQP projects at WPI?",
    "What are some examples of MQP projects at WPI?",
    "How does the WPI project system work?",

    # Campus offices
    "Where is the registrar's office at WPI?",
    "What student services does WPI offer?",
    "How do I contact financial aid at WPI?",
    "Where is the student health center at WPI?",
    "What does the career development center at WPI offer?",

    # Departments
    "What academic departments does WPI have?",
    "What is the WPI computer science department like?",
    "What does the mechanical engineering department at WPI offer?",
    "What humanities departments are at WPI?",
    "What is the WPI business school?",

    # Research areas
    "What research is done at WPI?",
    "Does WPI have AI and machine learning research?",
    "What cybersecurity research happens at WPI?",
    "What bioengineering research is at WPI?",
    "Does WPI do sustainability and environmental research?",
    "What robotics research is conducted at WPI?",

    # Facilities and labs
    "What labs and facilities does WPI have?",
    "Does WPI have a makerspace?",
    "What research labs are available to WPI students?",
    "What computing facilities does WPI offer?",
    "What biomedical labs are at WPI?",

    # Project centers
    "Where are WPI's global project centers?",
    "Can I do my IQP abroad?",
    "What countries can WPI students work in for their IQP?",
    "What US-based project centers does WPI have?",
    "How do I choose a project center for my IQP?",
]


def build_cache(max_workers: int = 1):
    print(f"Building cache for {len(QUESTIONS)} questions ({max_workers} workers)...\n")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    entries = []
    failed = []

    def process(q: str):
        try:
            answer = ask_wpi(q)
            embedding = model.encode(q).tolist()
            return {"question": q, "answer": answer, "embedding": embedding}
        except Exception as e:
            print(f"  [!] FAILED: {q[:60]} — {e}")
            return None

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process, q): q for q in QUESTIONS}
        for future in as_completed(futures):
            result = future.result()
            if result:
                entries.append(result)
                print(f"  ✓ ({len(entries)}/{len(QUESTIONS)}) {result['question'][:60]}")
            else:
                failed.append(futures[future])

    output = os.path.join(os.path.dirname(__file__), "qa_cache.json")
    with open(output, "w") as f:
        json.dump(entries, f, indent=2)

    print(f"\nDone! {len(entries)} pairs saved to qa_cache.json")
    if failed:
        print(f"  {len(failed)} failed — re-run to retry")


if __name__ == "__main__":
    build_cache()
