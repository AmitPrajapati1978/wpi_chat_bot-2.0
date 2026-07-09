"""
RAGAS evaluation for the WPI chatbot RAG pipeline.

Metrics (no ground truth required):
  - faithfulness     : answer is grounded in retrieved context
  - answer_relevancy : answer actually addresses the question
  - context_relevance: retrieved context is relevant to the question

LLM evaluator : Anthropic Claude Haiku (via LangchainLLMWrapper)
Embeddings    : sentence-transformers/all-MiniLM-L6-v2
"""

from dotenv import load_dotenv

from ragas import EvaluationDataset, SingleTurnSample, evaluate
from ragas.metrics._faithfulness import faithfulness
from ragas.metrics._answer_relevance import AnswerRelevancy
from ragas.metrics import _ContextRelevance
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_anthropic import ChatAnthropic
from langchain_huggingface import HuggingFaceEmbeddings

from section_selector import select_sections
from link_explorer import explore
from page_fetcher import fetch_pages
from answer_generator import generate_answer

load_dotenv()

TEST_QUESTIONS = [
    # degree_programs
    "What undergraduate engineering programs does WPI offer?",
    # course_catalog
    "What CS courses does WPI offer and what are their prerequisites?",
    # career_salaries
    "What is the average salary of a WPI computer science graduate?",
    # job_career_outlook
    "What is the job outlook for robotics engineers?",
    # student_clubs_orgs
    "What student clubs are available for international students?",
    # student_voices
    "What do WPI students say about the IQP experience?",
    # iqp_mqp_projects + project_centers
    "Where are WPI's global IQP project centers located?",
    # research_areas
    "What AI and machine learning research is done at WPI?",
    # facilities_labs
    "What research labs does WPI have for biomedical engineering?",
    # campus_offices + departments
    "What academic departments does WPI have?",
]


def run_pipeline(question: str) -> tuple[str, list[str]]:
    sections = select_sections(question)
    start_urls = [s["url"] for s in sections]
    top_pages = explore(question, start_urls, max_depth=3, top_n=3)
    if not top_pages:
        return "", []
    pages = fetch_pages(top_pages)
    answer = generate_answer(question, pages)
    contexts = [p["text"] for p in pages if p.get("text")]
    return answer, contexts


def build_dataset(questions: list[str]) -> EvaluationDataset:
    samples = []
    for i, q in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] {q}")
        try:
            answer, contexts = run_pipeline(q)
            if answer and contexts:
                samples.append(SingleTurnSample(
                    user_input=q,
                    response=answer,
                    retrieved_contexts=contexts,
                ))
                print(f"  OK — {len(contexts)} context(s), answer length {len(answer)}")
            else:
                print("  Skipped — no answer or empty context")
        except Exception as e:
            print(f"  Skipped — {e}")
    return EvaluationDataset(samples=samples)


def main():
    evaluator_llm = LangchainLLMWrapper(
        ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)
    )
    evaluator_embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    )

    metrics = [
        faithfulness,
        AnswerRelevancy(),
        _ContextRelevance(),
    ]

    print("=== Building evaluation dataset ===")
    dataset = build_dataset(TEST_QUESTIONS)
    print(f"\n=== Evaluating {len(dataset)} samples ===")

    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
        batch_size=3,  # limit concurrency to avoid rate limits
    )

    print("\n--- RAGAS Scores ---")
    print(results)

    df = results.to_pandas()
    out = "ragas_results.csv"
    df.to_csv(out, index=False)
    print(f"\nPer-question results saved to {out}")

    summary_cols = ["faithfulness", "answer_relevancy", "nv_context_relevance"]
    available = [c for c in summary_cols if c in df.columns]
    if available:
        print("\n--- Per-question summary ---")
        print(df[["user_input"] + available].to_string(index=False))


if __name__ == "__main__":
    main()
