from app.matching.normalize import (
    canonical_skill,
    implied_skills,
    normalize_skill,
    skill_satisfies,
    skills_equivalent,
)


def test_normalize_lowercase_and_strip():
    assert normalize_skill("  React.js  ") == "reactjs"
    assert normalize_skill("Node.JS!!!") == "nodejs"


def test_synonym_react():
    assert canonical_skill("React.js") == "react"
    assert canonical_skill("ReactJS") == "react"
    assert skills_equivalent("React", "react.js")
    assert skill_satisfies("React", "React.js")
    assert skill_satisfies("React.js", "React")


def test_synonym_javascript():
    assert canonical_skill("JS") == "javascript"
    assert skills_equivalent("JavaScript", "js")
    assert skill_satisfies("JavaScript", "JS")


def test_synonym_postgres():
    assert canonical_skill("Postgres") == "postgresql"
    assert skills_equivalent("PostgreSQL", "postgres")


def test_unknown_skill_passthrough():
    assert canonical_skill("Rust") == "rust"


def test_html5_css3_synonyms():
    assert skills_equivalent("HTML", "HTML5")
    assert skills_equivalent("CSS", "CSS3")


def test_typescript_implies_javascript():
    assert skill_satisfies("TypeScript", "JavaScript")
    assert skill_satisfies("TypeScript", "JS")
    assert not skill_satisfies("JavaScript", "TypeScript")


def test_css_html_imply_each_other():
    assert skill_satisfies("CSS", "HTML")
    assert skill_satisfies("HTML", "CSS")
    assert skill_satisfies("SCSS", "CSS")
    assert skill_satisfies("Tailwind", "HTML")


def test_react_implies_javascript_not_java():
    assert skill_satisfies("React", "JavaScript")
    assert "java" not in implied_skills("React")
    assert "javascript" in implied_skills("React")
    assert not skill_satisfies("React", "Java")


def test_compound_html_css_js():
    assert skill_satisfies("HTML/CSS/JavaScript", "JavaScript")
    assert skill_satisfies("SCSS", "HTML/CSS")


def test_known_tokens_in_noisy_jd_phrases():
    assert skill_satisfies("React", "Proficiency in React.js")
    assert skill_satisfies("TypeScript", "Vanilla JavaScript")
    assert skill_satisfies("TailwindCSS", "HTML5 & CSS3")
    assert skill_satisfies("Next.js", "React.js")
