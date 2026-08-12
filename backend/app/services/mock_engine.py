"""Rule-based mock engine used when no AI provider is configured.

Implements the same interface as the OpenAI-backed AI service so the app can
run fully offline for demos: resume parsing, question generation, answer
scoring with dynamic follow-ups, and report feedback.
"""
from __future__ import annotations

import re
from collections import OrderedDict
from random import Random

from app.models import Education, Experience, Project, Question, ResumeInfo

# ---------------------------------------------------------------------------
# Tech vocabulary
# ---------------------------------------------------------------------------

LANGUAGES = [
    "python", "javascript", "typescript", "java", "c++", "c#", "c", "golang",
    "go", "rust", "kotlin", "swift", "ruby", "php", "scala", "r", "sql",
    "dart", "objective-c", "perl", "bash",
]

TECH_KEYWORDS = LANGUAGES + [
    "react", "angular", "vue", "svelte", "next.js", "node.js", "node", "express",
    "django", "flask", "fastapi", "spring", "spring boot", "laravel", "rails",
    "graphql", "rest", "rest api", "websockets", "grpc",
    "html", "css", "tailwind", "bootstrap", "sass",
    "mysql", "postgresql", "mongodb", "sqlite", "redis", "elasticsearch",
    "kafka", "rabbitmq", "airflow", "spark", "hadoop",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "jenkins",
    "git", "github", "gitlab", "ci/cd", "linux", "nginx",
    "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
    "machine learning", "deep learning", "nlp", "computer vision", "llm",
    "data science", "data analysis", "statistics", "probability",
    "excel", "tableau", "power bi", "looker",
    "firebase", "redux", "redux toolkit", "webpack", "vite", "jest", "pytest",
    "selenium", "cypress", "postman", "jira", "figma", "xd", "sketch", "zeplin",
    "android", "ios", "react native", "flutter", "swiftui", "jetpack compose",
    "material ui", "shadcn", "chakra ui", "storybook",
]

TECH_LABEL = {t: t for t in TECH_KEYWORDS}
TECH_LABEL["c++"] = "C++"
TECH_LABEL["c#"] = "C#"
TECH_LABEL["golang"] = "Go"
TECH_LABEL["node.js"] = "Node.js"
TECH_LABEL["next.js"] = "Next.js"
TECH_LABEL["rest api"] = "REST API"
TECH_LABEL["machine learning"] = "Machine Learning"
TECH_LABEL["deep learning"] = "Deep Learning"
TECH_LABEL["computer vision"] = "Computer Vision"
TECH_LABEL["data science"] = "Data Science"
TECH_LABEL["spring boot"] = "Spring Boot"
TECH_LABEL["ci/cd"] = "CI/CD"

# ---------------------------------------------------------------------------
# Question banks
# ---------------------------------------------------------------------------

ROLE_QUESTIONS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "software engineer": {
        "easy": [
            ("Can you explain the difference between object-oriented and functional programming, and when you would choose one over the other?", "Programming paradigms"),
            ("What is the difference between an array and a linked list, and what are the time complexities of common operations on each?", "Data structures"),
            ("Describe what a RESTful API is and the role of the HTTP methods GET, POST, PUT and DELETE.", "Web APIs"),
        ],
        "medium": [
            ("Explain how you would design a URL shortener. Cover the database schema, hashing strategy, and how you would handle collisions.", "System design"),
            ("What is the difference between a process and a thread? When would you use multi-threading versus multi-processing in a service?", "Concurrency"),
            ("How does a database index work under the hood, and when does an index hurt query performance?", "Databases"),
        ],
        "hard": [
            ("Design a distributed rate limiter. Discuss token bucket versus sliding window, consistency across nodes, and failure handling.", "System design"),
            ("Explain the CAP theorem with a real system you have worked on. How did you make the consistency-availability trade-off?", "Distributed systems"),
            ("How would you implement leader election and distributed consensus in a cluster of services, and when would you reach for Raft or Paxos?", "Distributed systems"),
        ],
    },
    "frontend developer": {
        "easy": [
            ("What is the difference between a framework like React and plain JavaScript DOM manipulation? What problems do frameworks solve?", "Frontend fundamentals"),
            ("Explain the CSS box model, and how flexbox and grid differ for building layouts.", "CSS"),
            ("What does responsive design mean, and what techniques do you use to make a page mobile-friendly?", "Responsive design"),
        ],
        "medium": [
            ("How does React's virtual DOM and reconciliation work, and how can memoization improve rendering performance?", "React"),
            ("Explain client-side versus server-side rendering. When would you choose each, and what are the trade-offs for SEO and performance?", "Rendering"),
            ("How do you manage state in a large frontend application? Compare local state, context, and external state libraries.", "State management"),
        ],
        "hard": [
            ("How would you optimize a page with heavy images on a slow network? Walk through lazy loading, image formats, and Core Web Vitals.", "Performance"),
            ("How would you implement real-time collaborative editing in the browser, covering cursor sync and conflict resolution?", "Advanced frontend"),
            ("Explain how you would structure a frontend monorepo with a shared design system while keeping type safety and build performance at scale.", "Architecture"),
        ],
    },
    "backend developer": {
        "easy": [
            ("What is the difference between SQL and NoSQL databases? Give an example use case for each.", "Databases"),
            ("Explain what caching is and where you would introduce it in a typical backend service.", "Caching"),
            ("What are the key principles of a well-designed API?", "API design"),
        ],
        "medium": [
            ("How would you design a system that handles 10,000 writes per second? Discuss database choice, sharding, and queueing.", "System design"),
            ("Explain synchronous versus asynchronous processing, and when you would introduce a message queue like Kafka or RabbitMQ.", "Architecture"),
            ("How do you handle authentication and authorization in a modern web application? Compare JWT and session-based approaches.", "Security"),
        ],
        "hard": [
            ("Design a payment system that must never double-charge. Discuss idempotency, distributed transactions, and reconciliation.", "System design"),
            ("How do you ensure data consistency in a microservices architecture? Compare saga patterns, the outbox pattern, and two-phase commit.", "Distributed systems"),
            ("Describe how you would debug a production outage caused by a database deadlock, from initial diagnosis to long-term fixes.", "Operations"),
        ],
    },
    "full stack developer": {
        "easy": [
            ("Walk through the full request lifecycle from typing a URL to rendering a page. Where do frontend and backend responsibilities split?", "Full stack fundamentals"),
            ("What is the difference between client-side and server-side validation, and why do you need both?", "Validation"),
            ("How would you structure a small full-stack application? Sketch the folders and the data flow.", "Architecture"),
        ],
        "medium": [
            ("How do you keep frontend and backend contracts in sync as an app grows? Discuss shared types, code generation, and versioning.", "Contracts"),
            ("Describe how you would implement authentication end-to-end, including secure storage of tokens on the client.", "Security"),
            ("How would you handle image uploads and resizing efficiently? Discuss storage options and CDNs.", "File handling"),
        ],
        "hard": [
            ("Design a system where users invite collaborators to share documents in real time. Cover auth, permission checks, websockets, and conflict handling.", "System design"),
            ("How do you migrate a legacy monolithic application to a modern architecture without downtime?", "Migration"),
            ("Explain how you would secure a full-stack application against the OWASP Top 10, with a concrete example for each class of vulnerability.", "Security"),
        ],
    },
    "machine learning engineer": {
        "easy": [
            ("Explain the difference between supervised, unsupervised, and reinforcement learning.", "ML fundamentals"),
            ("What is overfitting, and what are the main techniques used to prevent it?", "Modeling"),
            ("Explain precision and recall, and when each one matters more.", "Evaluation"),
        ],
        "medium": [
            ("Describe how you would deploy a trained ML model to production, covering serving latency, monitoring drift, and retraining.", "MLOps"),
            ("How would you handle an imbalanced classification dataset?", "Data"),
            ("Explain the bias-variance trade-off with a concrete example from a project you have worked on.", "Modeling"),
        ],
        "hard": [
            ("Design an end-to-end ML system for fraud detection: data, features, model, serving, and monitoring. Which metrics do you optimize?", "System design"),
            ("How do you diagnose and fix a model whose performance degrades in production over time?", "MLOps"),
            ("Compare batch and streaming inference. When would you choose each, and what infrastructure does each require?", "Inference"),
        ],
    },
    "data scientist": {
        "easy": [
            ("What is the difference between correlation and causation? Give an example.", "Statistics"),
            ("Why do we split data into training and test sets, and why does cross-validation matter?", "Evaluation"),
            ("What is an A/B test, and what can go wrong when you run one?", "Experimentation"),
        ],
        "medium": [
            ("Describe how you would clean a messy real-world dataset. What checks do you run, and how do you handle missing values?", "Data cleaning"),
            ("How do you decide between a statistical test and an ML model to answer a business question?", "Analysis"),
            ("Explain feature engineering, and give an example of features you would create for a time-series problem.", "Feature engineering"),
        ],
        "hard": [
            ("Design an experimentation platform for a product team, covering power analysis, multiple-testing corrections, and guardrail metrics.", "Experimentation"),
            ("How do you explain a complex model's decisions to non-technical stakeholders, and when is interpretability critical?", "Communication"),
            ("Describe how you would build a causal inference study when a randomized experiment is impossible.", "Causality"),
        ],
    },
    "mobile app developer": {
        "easy": [
            ("What is the difference between native, hybrid, and cross-platform development?", "Mobile fundamentals"),
            ("Explain the app lifecycle events in your framework of choice, and where you would load data.", "Lifecycle"),
            ("How do you handle app state and navigation in a mobile application?", "State management"),
        ],
        "medium": [
            ("How would you optimize app startup time and memory usage on low-end devices?", "Performance"),
            ("Describe how you handle offline support and local data synchronization when the network reconnects.", "Offline"),
            ("How do you manage permissions and privacy in a mobile app while keeping the user experience smooth?", "Permissions"),
        ],
        "hard": [
            ("Design the architecture for a chat app with push notifications, offline queues, and end-to-end encryption.", "System design"),
            ("How would you diagnose a memory leak or battery-draining issue in a production build?", "Debugging"),
            ("Explain how you would implement CI/CD with staged rollouts for a mobile app across app stores.", "CI/CD"),
        ],
    },
    "ui/ux designer": {
        "easy": [
            ("What is the difference between UX and UI design?", "UX fundamentals"),
            ("Why is user research important before building an interface?", "Research"),
            ("What makes a design system valuable to a product team?", "Design systems"),
        ],
        "medium": [
            ("Walk me through your design process from research to high-fidelity prototype.", "Process"),
            ("How do you balance stakeholder requirements with user needs when they conflict?", "Stakeholders"),
            ("Explain how you apply accessibility (WCAG) principles in your designs.", "Accessibility"),
        ],
        "hard": [
            ("How would you redesign a complex enterprise workflow that users find confusing? Describe research, information architecture, and validation.", "Redesign"),
            ("How do you measure the success of a design change using quantitative and qualitative methods?", "Metrics"),
            ("How do you design for consistency at scale while still allowing teams to innovate quickly?", "Scale"),
        ],
    },
}

BEHAVIORAL = [
    ("easy", "Tell me about yourself and how your background led you to this role.", "Self introduction"),
    ("easy", "What motivates you to do your best work?", "Motivation"),
    ("easy", "What are you most proud of in your career so far?", "Achievement"),
    ("medium", "Describe a time you worked with a difficult teammate and how you handled it.", "Collaboration"),
    ("medium", "Tell me about a time you had to learn a new technology quickly to meet a deadline.", "Adaptability"),
    ("medium", "Describe a situation where you received tough feedback. How did you respond?", "Feedback"),
    ("hard", "Tell me about a time you made a mistake with significant impact. What did you do and what did you learn?", "Accountability"),
    ("hard", "Describe a time you disagreed with a technical decision your team made. How did you handle it?", "Conflict"),
    ("hard", "Tell me about a time you led a project with ambiguous requirements.", "Leadership"),
]

SITUATIONAL = [
    ("easy", "A teammate is blocked on a bug and asks for your help, but you are behind on your own deadline. What do you do?", "Prioritization"),
    ("medium", "You discover a critical bug affecting real users in production. Walk me through your immediate response.", "Incident response"),
    ("medium", "A stakeholder changes the requirements halfway through a sprint. How do you handle it?", "Change management"),
    ("medium", "Your project is at risk of missing its deadline. How do you reprioritize and communicate?", "Planning"),
    ("hard", "Your team has to ship a major feature in half the usual time. How do you approach planning and delivery?", "Delivery"),
    ("hard", "You are assigned a task in an area you have never worked in, with no documentation. What is your plan?", "Autonomy"),
    ("hard", "A senior engineer proposes an approach you believe is technically risky. How do you respond?", "Influence"),
]

WARMUP = (
    "easy",
    "To start, tell me about yourself and how your background aligns with this role.",
    "Self introduction",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _q(text: str, qtype: str, topic: str, difficulty: str, follow_up_for: str | None = None) -> Question:
    return Question(text=text, type=qtype, topic=topic, difficulty=difficulty, follow_up_for=follow_up_for)  # type: ignore[arg-type]


def _pick_random(rng: Random, items: list, n: int) -> list:
    return rng.sample(items, min(n, len(items)))


def _matches_role(role: str, bank_key: str) -> bool:
    r = role.lower()
    return bank_key in r or r in bank_key


def _role_key(role: str) -> str | None:
    for key in ROLE_QUESTIONS:
        if _matches_role(role, key):
            return key
    return None


def _dedupe(items: list) -> list:
    return list(OrderedDict.fromkeys(items))


def _clean_tech(label: str) -> str:
    return TECH_LABEL.get(label.lower(), label)


# ---------------------------------------------------------------------------
# Resume parsing (mock)
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s\-().]{7,}\d)")
SECTION_HEADINGS = [
    "education", "work experience", "experience", "skills", "technologies",
    "programming languages", "projects", "certifications", "certificates",
    "summary", "profile", "about", "objective", "languages", "links",
]
HEADER_SECTION = "header"


def mock_analyze_resume(text: str) -> tuple[ResumeInfo, str]:
    resume = ResumeInfo()
    resume.email = EMAIL_RE.search(text).group(0) if EMAIL_RE.search(text) else ""

    phone_match = PHONE_RE.search(text)
    resume.phone = phone_match.group(1).strip() if phone_match else ""

    sections: dict[str, list[str]] = {}
    current = HEADER_SECTION
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower().rstrip(":.")
        matched = None
        for heading in SECTION_HEADINGS:
            if re.fullmatch(re.escape(heading) + r"[\s:]*", low):
                matched = heading
                break
        if matched:
            current = matched
            sections.setdefault(current, [])
        else:
            sections.setdefault(current, []).append(line)

    header = sections.get(HEADER_SECTION, [])
    for line in header:
        if resume.email and resume.email in line:
            continue
        if resume.phone and resume.phone in line:
            continue
        if line.count(" ") >= 1 and line.split()[0][:1].isupper():
            resume.name = line
            break
    if not resume.name and header:
        resume.name = header[0]

    resume.summary = " ".join(sections.get("summary", []) or sections.get("profile", []) or sections.get("about", []) or sections.get("objective", []))

    full_text_lower = text.lower()
    detected = _dedupe([t for t in TECH_KEYWORDS if re.search(rf"\b{re.escape(t)}\b", full_text_lower)])
    resume.languages = [L for L in LANGUAGES if L in detected]
    resume.technologies = [t for t in detected if t not in LANGUAGES]
    resume.skills = _dedupe(resume.languages + resume.technologies)

    def _section_lines(key: str) -> list[str]:
        for k in (key,):
            if k in sections:
                return sections[k]
        return []

    resume.certifications = [l.strip("-• ") for l in _section_lines("certifications")][:10]

    skill_lines = _section_lines("skills")
    if skill_lines:
        raw_skills = []
        for l in skill_lines:
            raw_skills += [s.strip().lower() for s in re.split(r"[,;•|]+", l) if s.strip()]
        resume.skills = _dedupe(resume.skills + [s for s in raw_skills if s])
        resume.technologies = _dedupe(resume.technologies + [s for s in raw_skills if s in TECH_KEYWORDS])

    edu_lines = _section_lines("education")
    for chunk in _chunk_lines(edu_lines, 3):
        degree = chunk[0] if chunk else ""
        resume.education.append(Education(degree=degree, institution=chunk[1] if len(chunk) > 1 else "", year=chunk[2] if len(chunk) > 2 else ""))

    exp_lines = _section_lines("experience")
    resume.experience = _parse_experience(exp_lines)

    proj_lines = _section_lines("projects")
    resume.projects = _parse_projects(proj_lines, text)

    summary = _build_summary(resume)
    return resume, summary


def _chunk_lines(lines: list[str], size: int) -> list[list[str]]:
    chunks: list[list[str]] = []
    cur: list[str] = []
    for line in lines:
        cur.append(line)
        if len(cur) >= size:
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def _parse_experience(lines: list[str]) -> list:
    experiences = []
    cur: list[str] = []
    for line in lines:
        if re.match(r"^[A-Z][^,;:]{2,}( - | \| |, )", line) or line.startswith(("-", "•")) or (cur and re.match(r"^\d{4}", line)):
            if cur:
                experiences.append(_exp_from_lines(cur))
            cur = [line]
        else:
            cur.append(line)
    if cur:
        experiences.append(_exp_from_lines(cur))
    return [e for e in experiences if e.role or e.company][:6]


def _exp_from_lines(lines: list[str]) -> Experience:
    head = lines[0] if lines else ""
    desc = " ".join(lines[1:])
    parts = re.split(r"\s*(-|\|)\s*", head, maxsplit=1)
    if len(parts) >= 3:
        role, _, company = parts[0], parts[1], parts[2]
    else:
        role, company = head, ""
    period = ""
    m = re.search(r"(\d{4}\s*[-–to]+\s*(?:\d{4}|present|now))", " ".join(lines), re.IGNORECASE)
    if m:
        period = m.group(1)
    return Experience(role=role.strip(), company=company.strip(), period=period, description=desc)


def _parse_projects(lines: list[str], text: str) -> list:
    projects = []
    cur: list[str] = []
    for line in lines:
        if line.startswith(("-", "•")) or ":" in line or " - " in line:
            if cur:
                projects.append(_proj_from_lines(cur))
            cur = [line]
        else:
            cur.append(line)
    if cur:
        projects.append(_proj_from_lines(cur))

    if not projects:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            low = sent.lower()
            if any(w in low for w in ("built ", "developed ", "created ", "designed a ")):
                projects.append(Project(name=sent[:48], description=sent))
                if len(projects) >= 4:
                    break
    return [p for p in projects if p.name or p.description][:6]


def _proj_from_lines(lines: list[str]) -> Project:
    head = lines[0].lstrip("-• ").strip()
    desc = " ".join(lines[1:]) if len(lines) > 1 else ""
    tech = [t for t in TECH_KEYWORDS if re.search(rf"\b{re.escape(t)}\b", (head + " " + desc).lower())]
    return Project(name=head, description=desc or head, technologies=tech)


def _build_summary(resume: ResumeInfo) -> str:
    top = ", ".join(resume.technologies[:5]) if resume.technologies else "no explicit technologies listed"
    return (
        f"Candidate identified: {resume.name or 'Unknown'}. "
        f"Detected {len(resume.skills)} relevant skills — highlights: {top}. "
        f"Education entries: {len(resume.education)}. Experience: {len(resume.experience)} role(s). "
        f"Projects identified: {len(resume.projects)}. Certifications: {len(resume.certifications)}."
    )


# ---------------------------------------------------------------------------
# Question generation (mock)
# ---------------------------------------------------------------------------

def mock_generate_questions(resume: ResumeInfo, role: str, difficulty: str, count: int = 8) -> list[Question]:
    rng = Random(role + difficulty)
    bank_key = _role_key(role)
    pool: list[Question] = []

    if bank_key:
        for text, topic in ROLE_QUESTIONS[bank_key].get(difficulty, ROLE_QUESTIONS[bank_key]["medium"]):
            pool.append(_q(text, "technical", topic, difficulty))

    if not bank_key:
        pool.append(_q(
            f"As a {role or 'software'} professional, how would you approach breaking down a large, ambiguous problem into actionable tasks?",
            "behavioral", "Problem solving", difficulty,
        ))

    tech_pool = _dedupe(resume.technologies + resume.languages + resume.skills)[:6]
    for skill in _pick_random(rng, tech_pool, 3):
        label = _clean_tech(skill)
        pool.append(_q(
            f"Describe a real scenario where you used {label} and explain why it was the right tool for the job.",
            "technical", label, difficulty,
        ))

    for proj in _pick_random(rng, resume.projects[:6], 2):
        name = proj.name or "your project"
        techs = ", ".join(_clean_tech(t) for t in proj.technologies[:3]) or "the stack you used"
        pool.append(_q(
            f"Walk me through {name}. What was your role, what did you build with {techs}, and what was the biggest technical challenge you solved?",
            "project", name, difficulty,
        ))
        pool.append(_q(
            f"Looking back at {name}, what would you architect differently today, and how would you measure its success?",
            "project", name, "hard" if difficulty == "hard" else "medium",
        ))

    if resume.experience:
        exp = resume.experience[0]
        pool.append(_q(
            f"Your resume highlights a {exp.role or 'role'} position at {exp.company or 'a company'}. What was your most significant contribution there?",
            "cv", "Experience", difficulty,
        ))
    if resume.certifications:
        cert = resume.certifications[0]
        pool.append(_q(
            f"You list {cert} as a certification. How has it directly influenced your day-to-day work?",
            "cv", "Certification", difficulty,
        ))
    if resume.education:
        edu = resume.education[0]
        pool.append(_q(
            f"How did your background in {edu.degree or edu.institution or 'your studies'} prepare you for this role?",
            "cv", "Education", difficulty,
        ))

    behav_pool = [b for b in BEHAVIORAL if b[0] == difficulty] or BEHAVIORAL
    for _, text, topic in _pick_random(rng, behav_pool, 2):
        pool.append(_q(text, "behavioral", topic, difficulty))

    situ_pool = [s for s in SITUATIONAL if s[0] == difficulty] or SITUATIONAL
    for _, text, topic in _pick_random(rng, situ_pool, 1):
        pool.append(_q(text, "situational", topic, difficulty))

    rng.shuffle(pool)
    chosen = pool[: max(0, count - 1)]

    warmup = _q(WARMUP[1], "behavioral", WARMUP[2], WARMUP[0])
    return [warmup] + chosen[: count - 1]


# ---------------------------------------------------------------------------
# Answer evaluation (mock)
# ---------------------------------------------------------------------------

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "of", "to", "in", "on",
    "for", "at", "by", "with", "as", "is", "are", "was", "were", "be", "been",
    "it", "its", "this", "that", "these", "those", "you", "your", "do", "does",
    "did", "i", "me", "my", "we", "our", "us", "so", "just", "very", "really",
    "about", "from", "can", "could", "would", "should", "will", "when", "where",
    "what", "how", "why", "have", "has", "had", "not", "no", "yes", "also",
    "get", "got", "go", "went", "well", "use", "used", "using", "make", "made",
}

MARKERS = ["first", "second", "third", "then", "finally", "because", "for example",
           "for instance", "however", "specifically", "in short", "in my view",
           "as a result", "which means", "the reason", "also"]
HEDGES = ["i think maybe", "i'm not sure", "i am not sure", "not really", "i guess",
          "i don't know", "i dont know", "maybe", "probably", "kind of", "sort of"]
PROBLEM_WORDS = ["approach", "analyzed", "solution", "solved", "challenge", "debug",
                 "optimized", "tested", "designed", "implemented", "measured", "tried",
                 "experiment", "evaluated", "refactored", "automated", "compared"]

DIMENSIONS = ["Relevance", "Technical Accuracy", "Completeness", "Communication",
              "Clarity", "Confidence", "Problem Solving"]

WEIGHTS = {
    "Relevance": 0.18,
    "Technical Accuracy": 0.20,
    "Completeness": 0.18,
    "Communication": 0.12,
    "Clarity": 0.12,
    "Confidence": 0.10,
    "Problem Solving": 0.10,
}

FOLLOWUP_THRESHOLD = {"easy": 6.2, "medium": 6.8, "hard": 7.3}


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9+#.]+", text.lower()) if t not in STOPWORDS and len(t) > 1]


def mock_evaluate_answer(question: Question, answer: str, resume: ResumeInfo, difficulty: str) -> dict:
    answer = (answer or "").strip()
    if not answer:
        return _empty_evaluation()

    words = re.findall(r"\S+", answer)
    n_words = len(words)
    q_tokens = set(_tokens(question.text + " " + question.topic))
    a_tokens = set(_tokens(answer))

    relevance = 0.0
    if q_tokens:
        overlap = len(q_tokens & a_tokens)
        relevance = min(1.0, overlap / min(max(len(q_tokens), 1), 12))

    tech_vocab = set(t.lower() for t in _dedupe(resume.technologies + resume.skills + resume.languages) + TECH_KEYWORDS)
    tech_hits = len(tech_vocab & a_tokens)
    if question.type == "technical":
        technical = 0.3 + 0.5 * min(1.0, tech_hits / 2.0)
    else:
        technical = 0.35 + 0.2 * min(1.0, tech_hits / 2.0)
    technical = min(1.0, technical)

    completeness = min(1.0, n_words / 70) * 0.7 + min(1.0, n_words / 150) * 0.3

    sentences = [s for s in re.split(r"[.!?]+", answer) if len(s.strip()) > 1]
    avg_len = n_words / max(1, len(sentences))
    communication = max(0.25, 1.0 - abs(avg_len - 18) / 28)

    clarity = min(1.0, 0.45 + len([m for m in MARKERS if m in answer.lower()]) * 0.09)

    low = answer.lower()
    hedge_count = sum(low.count(h) for h in HEDGES)
    confidence = max(0.3, 1.0 - hedge_count * 0.22)

    ps = min(1.0, 0.3 + len([w for w in PROBLEM_WORDS if w in low]) * 0.12)

    dims = {
        "Relevance": round(relevance * 10, 1),
        "Technical Accuracy": round(technical * 10, 1),
        "Completeness": round(completeness * 10, 1),
        "Communication": round(communication * 10, 1),
        "Clarity": round(clarity * 10, 1),
        "Confidence": round(confidence * 10, 1),
        "Problem Solving": round(ps * 10, 1),
    }

    score = sum(dims[k] * WEIGHTS[k] for k in DIMENSIONS)
    score = round(max(1.0, min(10.0, score)), 1)

    explanation = _explanation(dims)

    threshold = FOLLOWUP_THRESHOLD.get(difficulty, 6.8)
    follow_up_needed = score < threshold
    follow_up_question = None
    if follow_up_needed:
        term = _followup_term(a_tokens, tech_vocab)
        follow_up_question = _followup_text(question, term, difficulty)

    return {
        "score": score,
        "dimensions": dims,
        "explanation": explanation,
        "follow_up_needed": follow_up_needed,
        "follow_up_question": follow_up_question,
    }


def _empty_evaluation() -> dict:
    dims = {k: 0.0 for k in DIMENSIONS}
    return {
        "score": 0.0,
        "dimensions": dims,
        "explanation": "No answer was provided, so this question was not scored.",
        "follow_up_needed": False,
        "follow_up_question": None,
    }


def _explanation(dims: dict) -> str:
    worst = min(dims, key=dims.get)
    best = max(dims, key=dims.get)
    tips = {
        "Completeness": "Try to expand your points with concrete examples and cover what, how, and why.",
        "Technical Accuracy": "Ground your answer in specific technologies or techniques and be precise about terminology.",
        "Relevance": "Make sure every point ties back to the question that was asked.",
        "Communication": "Structure your response so it flows logically and is easy for the interviewer to follow.",
        "Clarity": "Use signposting words (first, then, finally) and keep sentences focused.",
        "Confidence": "Avoid hedging language; state your points with conviction.",
        "Problem Solving": "Show your thought process, the options you considered, and how you evaluated them.",
    }
    return (
        f"Your answer was strongest on {best} ({dims[best]:.0f}/10) and weakest on {worst} ({dims[worst]:.0f}/10). "
        + tips[worst]
    )


def _followup_term(a_tokens: set[str], tech_vocab: set[str]) -> str | None:
    for tok in a_tokens:
        if tok in tech_vocab and len(tok) > 2:
            return tok
    for tok in a_tokens:
        if len(tok) > 3 and not tok.isdigit():
            return tok
    return None


def _followup_text(question: Question, term: str | None, difficulty: str) -> str:
    depth = {"easy": "Could you go one level deeper",
             "medium": "Could you walk me through the details",
             "hard": "Could you critically analyze"}.get(difficulty, "Could you elaborate")
    if question.type == "project":
        base = f"You mentioned {term or 'that'} in the context of your project. {depth}: what decisions did you make, what trade-offs were involved, and what would you change today?"
    elif question.type == "technical":
        base = f"You mentioned {term or 'that'}. {depth}: how have you applied it in practice, and what edge cases or pitfalls did you encounter?"
    elif question.type == "behavioral":
        base = f"Interesting. {depth}: how did that experience change how you work or communicate with your team?"
    else:
        base = f"You mentioned {term or 'that'}. {depth}: what impact did it have on the outcome, and what would you do differently next time?"
    return base


# ---------------------------------------------------------------------------
# Report feedback (mock)
# ---------------------------------------------------------------------------

GUIDANCE = {
    "Relevance": "Pay closer attention to the exact question and answer directly, then add context.",
    "Technical Accuracy": "Reinforce fundamentals: practice core concepts, data structures, and frameworks for the target role.",
    "Completeness": "Use the STAR / what-how-why structure and aim for answers that include a concrete example.",
    "Communication": "Practice explaining technical topics in a clear, confident, structured way.",
    "Clarity": "Slow down and signpost your answers (first, second, finally) to keep the interviewer following.",
    "Confidence": "Replace hedging phrases with decisive language; rehearse answers aloud before the real interview.",
    "Problem Solving": "Verbalize your reasoning and the alternatives you considered so the interviewer can follow your process.",
}


def mock_feedback(session, dim_averages: dict, overall: float) -> dict:
    strengths, weaknesses, improvements, recommended = [], [], [], []
    for dim, avg in sorted(dim_averages.items(), key=lambda kv: -kv[1]):
        if avg >= 7.0:
            strengths.append(f"Strong {dim.lower()} — averaged {avg:.1f}/10 across your answers.")
        elif avg <= 5.5:
            weaknesses.append(f"{dim} needs work — averaged {avg:.1f}/10.")
            improvements.append(GUIDANCE[dim])
            recommended.append(GUIDANCE[dim])

    if overall >= 8.0:
        strengths.append("Consistently strong performance — you are interview-ready for this difficulty level.")
    elif overall >= 6.5:
        strengths.append("Solid overall performance with a clear base to build on.")
        recommended.append("Run a few more mock interviews at the same difficulty to polish delivery.")
    else:
        weaknesses.append("The overall score indicates preparation gaps across multiple areas.")
        recommended.append("Start with a structured preparation plan: fundamentals, project deep-dives, then mock interviews.")

    if not strengths:
        strengths.append("You completed the interview — finishing the full session is a first win.")
    if not recommended:
        recommended.append("Rehearse your project stories and practice answering with the what-how-why structure.")

    return {
        "strengths": strengths[:6],
        "weaknesses": weaknesses[:6],
        "improvements": improvements[:6],
        "recommended_practice": _dedupe(recommended)[:8],
    }
