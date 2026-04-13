import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Each category maps to either:
#   prefix ending in "/" → an S3 folder of files to search through
#   prefix ending in a file extension → a direct S3 file to read as-is
S3_CATEGORIES = {
    "degree_programs": {
        "description": "Undergraduate and graduate degree programs, majors, minors, and certificates at WPI — curriculum, requirements, and program overviews.",
        "prefix": "data/drupal/tracks-md/",
    },
    "course_catalog": {
        "description": "Individual course descriptions, credit hours, prerequisites, and offerings for undergrad and graduate courses by department.",
        "prefix": "data/clean-catalog/programs/",
    },
    "student_clubs_orgs": {
        "description": "Student clubs, organizations, cultural groups, Greek life, and extracurricular activities on campus.",
        "prefix": "data/mywpi/",
    },
    "career_salaries": {
        "description": "Post-graduation employment rates, average salaries by program, knowledge rates, and career outcomes for WPI graduates.",
        "prefix": "data/career/2025/",
    },
    "job_career_outlook": {
        "description": "Occupational outlook, job titles, salary ranges, and career growth for careers related to WPI fields of study.",
        "prefix": "data/bls/",
    },
    "student_voices": {
        "description": "Personal testimonials, stories, and first-hand perspectives from current and former WPI students.",
        "prefix": "data/drupal/student-voices-md/",
    },
    "iqp_mqp_projects": {
        "description": "IQP and MQP project titles, descriptions, sponsors, advisors, and global project center locations.",
        "prefix": "data/projects/",
    },
    "campus_offices": {
        "description": "Campus offices, student services — housing, dining, health, registrar, financial aid, and administrative units.",
        "prefix": "data/drupal/office-data.csv",
    },
    "departments": {
        "description": "Academic departments at WPI — engineering, sciences, business, arts, and humanities.",
        "prefix": "data/drupal/department-data.csv",
    },
    "research_areas": {
        "description": "Research areas, institutes, and centers at WPI — AI, bioengineering, sustainability, cybersecurity, robotics, and more.",
        "prefix": "data/drupal/research/",
    },
    "facilities_labs": {
        "description": "Campus facilities, research labs, makerspaces, specialized equipment, and shared research infrastructure.",
        "prefix": "data/drupal/facilities/",
    },
    "project_centers": {
        "description": "Global and domestic IQP project center locations — where students go to complete their qualifying projects.",
        "prefix": "data/drupal/project_center-data.csv",
    },
}

SYSTEM_PROMPT = """You are an AI assistant helping navigate WPI's knowledge base.

Given a user's question, identify the top 3 data categories most likely to contain the answer.

Rules:
- Only select keys that exist in the provided dictionary
- Select EXACTLY 3 category keys ranked by relevance (most relevant first)
- Return ONLY a valid JSON array of 3 keys, no explanation

Example output: ["degree_programs", "course_catalog", "career_salaries"]"""


def select_sections(question: str) -> list[dict]:
    """
    Given a user question, returns the top 3 most relevant S3 categories
    as a list of dicts with keys: section_key, description, url (S3 prefix or key)
    """
    client = anthropic.Anthropic()

    categories_for_prompt = {k: v["description"] for k, v in S3_CATEGORIES.items()}

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=128,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"""User question: {question}

Available data categories:
{json.dumps(categories_for_prompt, indent=2)}

Return a JSON array of the 3 most relevant category keys, ranked by relevance."""
        }],
    )

    raw = response.content[0].text.strip()
    start = raw.find("[")
    end = raw.find("]", start)
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in response: {raw}")
    keys = json.loads(raw[start:end + 1])

    assert isinstance(keys, list) and len(keys) == 3, "Expected a list of 3 keys"
    for key in keys:
        assert key in S3_CATEGORIES, f"Unknown category key: {key}"

    return [{"section_key": k, "description": S3_CATEGORIES[k]["description"], "url": S3_CATEGORIES[k]["prefix"]} for k in keys]


if __name__ == "__main__":
    print("WPI Section Selector (S3) — type a question, Ctrl+C to quit\n")
    while True:
        try:
            question = input("Your question: ").strip()
            if not question:
                continue
            results = select_sections(question)
            print("\nTop 3 categories:")
            for i, s in enumerate(results, 1):
                print(f"  {i}. [{s['section_key']}] {s['url']}")
            print()
        except KeyboardInterrupt:
            print("\nBye!")
            break
