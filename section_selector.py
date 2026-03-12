import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

SECTIONS = {
    "project_based_learning": {
        "description": "Overview of WPI's project-based learning model, including project-based education philosophy, PBL in higher education, and the long-term impact of experiential learning.",
        "url": "https://www.wpi.edu/academics/project-based-learning",
    },

    "academics": {
        "description": "Academic programs at WPI including degrees, certificates, departments, undergraduate and graduate studies, faculty, and academic resources.",
        "url": "https://www.wpi.edu/academics",
    },

    "degrees_and_certificates": {
        "description": "Information about the degrees and certificates offered by WPI across various disciplines and programs.",
        "url": "https://www.wpi.edu/academics/degrees-and-certificates",
    },

    "departments_and_programs": {
        "description": "Details about academic departments, interdisciplinary programs, and fields of study available at WPI.",
        "url": "https://www.wpi.edu/academics/departments-programs",
    },

    "undergraduate_studies": {
        "description": "Resources and information related to undergraduate academic programs, curriculum, and academic opportunities.",
        "url": "https://www.wpi.edu/academics/undergraduate",
    },

    "graduate_studies": {
        "description": "Information about master's and doctoral programs, graduate admissions, research opportunities, and graduate student resources.",
        "url": "https://www.wpi.edu/academics/graduate",
    },

    "pre_collegiate_outreach": {
        "description": "Programs and initiatives designed to engage pre-college students in STEM education and academic exploration.",
        "url": "https://www.wpi.edu/academics/pre-collegiate",
    },

    "online_graduate_programs": {
        "description": "Online master's degrees and graduate programs designed for working professionals and remote learners.",
        "url": "https://www.wpi.edu/academics/online",
    },

    "online_professional_development": {
        "description": "Professional development courses, certificates, and continuing education opportunities offered online.",
        "url": "https://www.wpi.edu/academics/professional-development",
    },

    "stem_education_center": {
        "description": "The STEM Education Center at WPI focusing on STEM education research, teacher development, and outreach programs.",
        "url": "https://www.wpi.edu/academics/stem-education-center",
    },

    "faculty": {
        "description": "Information about WPI faculty including profiles, research areas, academic leadership, and teaching staff.",
        "url": "https://www.wpi.edu/academics/faculty",
    },

    "academic_calendar": {
        "description": "Important academic dates including semester schedules, holidays, registration deadlines, and academic events.",
        "url": "https://www.wpi.edu/academics/calendar",
    },

    "academic_catalogs": {
        "description": "Official academic catalogs containing course descriptions, degree requirements, and program structures.",
        "url": "https://www.wpi.edu/academics/catalogs",
    },

    "admissions_and_aid": {
        "description": "Information about applying to WPI, including undergraduate and graduate admissions, financial aid, scholarships, and tuition.",
        "url": "https://www.wpi.edu/admissions",
    },

    "undergraduate_admissions": {
        "description": "Application process, requirements, deadlines, and information for prospective undergraduate students.",
        "url": "https://www.wpi.edu/admissions/undergraduate",
    },

    "graduate_admissions": {
        "description": "Admissions information for master's and PhD programs including application requirements and deadlines.",
        "url": "https://www.wpi.edu/admissions/graduate",
    },

    "financial_aid": {
        "description": "Scholarships, grants, loans, and financial aid resources available to WPI students.",
        "url": "https://www.wpi.edu/admissions/financial-aid",
    },

    "athletics": {
        "description": "Information about WPI athletics including varsity teams, competitions, athletic facilities, and sports programs.",
        "url": "https://www.wpi.edu/athletics",
    },

    "student_experience": {
        "description": "Student life at WPI including housing, dining, student organizations, campus culture, recreation, health, and support services.",
        "url": "https://www.wpi.edu/student-experience",
    },

    "community_and_culture": {
        "description": "Campus community, student culture, diversity initiatives, and opportunities for social engagement.",
        "url": "https://www.wpi.edu/student-experience/community-culture",
    },

    "housing_and_dining": {
        "description": "Information about campus housing options, residence halls, meal plans, and dining services.",
        "url": "https://www.wpi.edu/student-experience/housing-dining",
    },

    "getting_involved": {
        "description": "Student clubs, organizations, leadership opportunities, and ways to get involved on campus.",
        "url": "https://www.wpi.edu/student-experience/getting-involved",
    },

    "sports_and_recreation": {
        "description": "Recreational sports, fitness programs, intramurals, and athletic facilities available to students.",
        "url": "https://www.wpi.edu/student-experience/sports-recreation",
    },

    "health_and_wellness": {
        "description": "Student health services, mental health resources, wellness programs, and counseling services.",
        "url": "https://www.wpi.edu/student-experience/health-wellness",
    },

    "resources_and_support": {
        "description": "Academic support, advising services, student assistance programs, and campus resources.",
        "url": "https://www.wpi.edu/student-experience/resources-support",
    },

    "first_year_experience": {
        "description": "Programs and resources designed to help first-year students transition successfully to WPI.",
        "url": "https://www.wpi.edu/student-experience/first-year-experience",
    },

    "research": {
        "description": "Research initiatives at WPI including major research areas, institutes, labs, and interdisciplinary collaboration.",
        "url": "https://www.wpi.edu/research",
    },

    "areas_of_research": {
        "description": "Key research fields and focus areas pursued by WPI faculty and research groups.",
        "url": "https://www.wpi.edu/research/areas",
    },

    "institutes_and_centers": {
        "description": "Research institutes and centers that support interdisciplinary collaboration and innovation.",
        "url": "https://www.wpi.edu/research/institutes-centers",
    },

    "student_research": {
        "description": "Research opportunities and projects available for undergraduate and graduate students.",
        "url": "https://www.wpi.edu/research/student-research",
    },

    "core_research_facilities": {
        "description": "Shared research laboratories, equipment, and facilities supporting advanced scientific research.",
        "url": "https://www.wpi.edu/research/facilities",
    },

    "innovation_and_entrepreneurship": {
        "description": "Programs supporting innovation, startups, entrepreneurship, and technology commercialization at WPI.",
        "url": "https://www.wpi.edu/innovation-entrepreneurship",
    },

    "news_and_events": {
        "description": "Latest news stories, campus announcements, and upcoming events at WPI.",
        "url": "https://www.wpi.edu/news",
    },

    "give_to_wpi": {
        "description": "Information about donating to WPI, alumni giving programs, and philanthropic initiatives.",
        "url": "https://www.wpi.edu/giving",
    },

    "students": {
        "description": "Resources and services specifically for current WPI students including academic and campus life support.",
        "url": "https://www.wpi.edu/students",
    },

    "parents": {
        "description": "Information and resources for parents of WPI students including campus updates and support resources.",
        "url": "https://www.wpi.edu/parents",
    },

    "faculty_staff": {
        "description": "Resources, policies, and tools for WPI faculty and staff.",
        "url": "https://www.wpi.edu/faculty-staff",
    },

    "alumni": {
        "description": "Alumni resources, engagement opportunities, events, and ways to stay connected with WPI.",
        "url": "https://www.wpi.edu/alumni",
    },

    "employers_and_partners": {
        "description": "Information for employers and industry partners interested in collaborating with WPI or recruiting students.",
        "url": "https://www.wpi.edu/employers-partners",
    },

    "k12": {
        "description": "Educational outreach programs and STEM initiatives for K-12 students and teachers.",
        "url": "https://www.wpi.edu/k-12",
    },

    "media": {
        "description": "Press releases, media contacts, and resources for journalists covering WPI.",
        "url": "https://www.wpi.edu/news/media",
    }
}

SYSTEM_PROMPT = """You are an AI navigation assistant for the Worcester Polytechnic Institute (WPI) website.

Your task is to analyze a user's question and identify the top 3 website sections most likely to contain the answer.

Rules:
- Only select keys that exist in the provided dictionary
- Select EXACTLY 3 section keys ranked by relevance (most relevant first)
- Think like a human researcher navigating the WPI website main menu
- Return ONLY a valid JSON array of 3 section keys, with no explanation or extra text

Example output: ["academics", "admissions_and_aid", "research"]"""


def select_sections(question: str) -> list[dict]:
    """
    Given a user question, returns the top 3 most relevant sections
    as a list of dicts with keys: section_key, description, url
    """
    client = anthropic.Anthropic()

    sections_for_prompt = {k: v["description"] for k, v in SECTIONS.items()}

    user_message = f"""User question: {question}

Available website sections:
{json.dumps(sections_for_prompt, indent=2)}

Return a JSON array of the 3 most relevant section keys, ranked by relevance."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = response.content[0].text.strip()
    start = raw.find("[")
    end = raw.find("]", start)
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in response: {raw}")
    keys = json.loads(raw[start:end + 1])

    assert isinstance(keys, list) and len(keys) == 3, "Expected a list of 3 keys"
    for key in keys:
        assert key in SECTIONS, f"Unknown section key: {key}"

    return [{"section_key": k, **SECTIONS[k]} for k in keys]


if __name__ == "__main__":
    print("WPI Section Selector — type a question, Ctrl+C to quit\n")
    while True:
        try:
            question = input("Your question: ").strip()
            if not question:
                continue
            results = select_sections(question)
            print("\nTop 3 sections:")
            for i, s in enumerate(results, 1):
                print(f"  {i}. [{s['section_key']}] {s['url']}")
            print()
        except KeyboardInterrupt:
            print("\nBye!")
            break
