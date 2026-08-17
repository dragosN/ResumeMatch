"""Deterministic skill normalization, synonyms, and implication rules."""

from __future__ import annotations

import re

# Alias → canonical (all lowercase, post-normalize).
SYNONYM_MAP: dict[str, str] = {
    "react": "react",
    "reactjs": "react",
    "react js": "react",
    "node": "node",
    "nodejs": "node",
    "node js": "node",
    "javascript": "javascript",
    "js": "javascript",
    "ecmascript": "javascript",
    "es6": "javascript",
    "es2015": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "psql": "postgresql",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "amazon web services": "aws",
    "aws": "aws",
    "google cloud platform": "gcp",
    "gcp": "gcp",
    "google cloud": "gcp",
    "machine learning": "machine learning",
    "ml": "machine learning",
    "artificial intelligence": "ai",
    "ai": "ai",
    "ci/cd": "cicd",
    "cicd": "cicd",
    "ci cd": "cicd",
    "rest api": "rest",
    "rest": "rest",
    "restful": "rest",
    "graphql": "graphql",
    "gql": "graphql",
    "nextjs": "nextjs",
    "next js": "nextjs",
    "next": "nextjs",
    "vuejs": "vue",
    "vue": "vue",
    "angularjs": "angular",
    "angular": "angular",
    "c sharp": "csharp",
    "csharp": "csharp",
    "dot net": "dotnet",
    "dotnet": "dotnet",
    "objective c": "objective-c",
    "objective-c": "objective-c",
    "objectivec": "objective-c",
    "html": "html",
    "html5": "html",
    "html 5": "html",
    "css": "css",
    "css3": "css",
    "css 3": "css",
    "scss": "scss",
    "sass": "sass",
    "less": "less",
    "tailwind": "tailwind",
    "tailwindcss": "tailwind",
    "tailwind css": "tailwind",
    "jsx": "jsx",
    "tsx": "tsx",
    "vanilla javascript": "javascript",
    "vanilla js": "javascript",
    "hypertext markup language": "html",
    "cascading style sheets": "css",
}

# Resume canonical → JD canons it also satisfies (one-way, then transitively closed).
IMPLIES: dict[str, tuple[str, ...]] = {
    "typescript": ("javascript",),
    "tsx": ("typescript", "react", "javascript"),
    "jsx": ("react", "javascript"),
    "nextjs": ("react",),
    "react": ("javascript",),
    "vue": ("javascript",),
    "angular": ("javascript",),
    "node": ("javascript",),
    "scss": ("css",),
    "sass": ("css",),
    "less": ("css",),
    "tailwind": ("css",),
    "css": ("html",),
    "html": ("css",),
}

_SPLIT_COMPOUND = re.compile(r"[,/|&;]+|\band\b", re.IGNORECASE)
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "etc",
        "experience",
        "expert",
        "framework",
        "frameworks",
        "in",
        "including",
        "knowledge",
        "language",
        "languages",
        "library",
        "libraries",
        "must",
        "of",
        "or",
        "plus",
        "proficient",
        "proficiency",
        "required",
        "solid",
        "strong",
        "such",
        "the",
        "using",
        "with",
        "years",
    }
)

# Placeholders so C++, C#, .NET survive punctuation stripping.
_PROTECT = (
    (re.compile(r"c\+\+", re.I), "cplusplus"),
    (re.compile(r"c#", re.I), "csharp"),
    (re.compile(r"\.net", re.I), "dotnet"),
)
_UNPROTECT = {
    "cplusplus": "c++",
}


def normalize_skill(skill: str) -> str:
    """Lowercase, collapse .js/.ts suffixes, strip punctuation, collapse whitespace."""
    text = skill.lower().strip()
    for pattern, token in _PROTECT:
        text = pattern.sub(token, text)
    # react.js / node.js / next.js → reactjs / nodejs / nextjs
    text = re.sub(r"\.jsx\b", "jsx", text)
    text = re.sub(r"\.tsx\b", "tsx", text)
    text = re.sub(r"\.js\b", "js", text)
    text = re.sub(r"\.ts\b", "ts", text)
    text = re.sub(r"[^\w\s+#/-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _UNPROTECT.get(text, text)


def canonical_skill(skill: str) -> str:
    """Normalize then map through synonym table."""
    normalized = normalize_skill(skill)
    return SYNONYM_MAP.get(normalized, normalized)


def expand_skill(skill: str) -> list[str]:
    """Canonical tokens for a skill, including known names inside longer JD phrases."""
    known = known_skill_tokens(skill)
    if known:
        return known
    whole = canonical_skill(skill)
    return [whole] if whole else []


def known_skill_tokens(skill: str) -> list[str]:
    """Pull synonym-map skills out of phrases like 'Proficiency in React.js' or 'HTML5 CSS3'."""
    found: list[str] = []

    def add(canon: str) -> None:
        if canon and canon not in found:
            found.append(canon)

    whole = normalize_skill(skill)
    if whole in SYNONYM_MAP:
        add(SYNONYM_MAP[whole])
        return found

    chunks = [skill, *(_SPLIT_COMPOUND.split(skill))]
    seen_chunks: set[str] = set()
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        key = chunk.lower()
        if key in seen_chunks:
            continue
        seen_chunks.add(key)
        norm = normalize_skill(chunk)
        if norm in SYNONYM_MAP:
            add(SYNONYM_MAP[norm])
            continue
        words = [w for w in norm.split() if w and w not in _STOPWORDS]
        if not words:
            continue
        used = [False] * len(words)
        for n in range(min(4, len(words)), 0, -1):
            for i in range(len(words) - n + 1):
                if any(used[i : i + n]):
                    continue
                gram = " ".join(words[i : i + n])
                if gram in SYNONYM_MAP:
                    add(SYNONYM_MAP[gram])
                    for j in range(i, i + n):
                        used[j] = True
        for i, word in enumerate(words):
            if used[i]:
                continue
            if word in SYNONYM_MAP:
                add(SYNONYM_MAP[word])
            elif word in IMPLIES:
                add(word)
    return found


def coverage_set(skills: list[str]) -> set[str]:
    """Union of canonical skills + implications for a list of resume (or JD) skills."""
    covered: set[str] = set()
    for skill in skills:
        covered |= implied_skills(skill)
    return covered


def implied_skills(skill: str) -> set[str]:
    """Canonical forms this skill satisfies, including itself and transitive implications."""
    covered: set[str] = set()
    stack = list(expand_skill(skill))
    while stack:
        cur = stack.pop()
        if cur in covered:
            continue
        covered.add(cur)
        stack.extend(IMPLIES.get(cur, ()))
    return covered


def skill_satisfies(resume_skill: str, jd_skill: str) -> bool:
    """True if a resume skill covers a JD skill via synonym, compound split, or implication."""
    covered = implied_skills(resume_skill)
    jd_tokens = expand_skill(jd_skill)
    if not jd_tokens:
        return False
    return all(token in covered for token in jd_tokens)


def is_weaker_than_requirement(resume_skill: str, jd_skill: str) -> bool:
    """True when the JD skill is a specialization of the resume skill (JS vs TypeScript)."""
    if skill_satisfies(resume_skill, jd_skill):
        return False
    resume_canon = canonical_skill(resume_skill)
    return resume_canon in implied_skills(jd_skill)


def skills_equivalent(a: str, b: str) -> bool:
    """True when two skill strings resolve to the same canonical form."""
    return canonical_skill(a) == canonical_skill(b)


def satisfaction_reason(resume_skill: str, jd_skill: str) -> str:
    if skills_equivalent(resume_skill, jd_skill):
        return "Exact or synonym match"
    if skill_satisfies(resume_skill, jd_skill):
        return f"Implied by {resume_skill}"
    return "Match"
