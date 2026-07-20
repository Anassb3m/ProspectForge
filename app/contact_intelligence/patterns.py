"""Published same-domain pattern learning and bounded candidate generation."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.contact_intelligence.extractors import GENERIC_LOCALS, normalize_email, normalize_person_name


@dataclass(frozen=True, slots=True)
class LearnedPattern:
    name: str
    observations: int
    strength: str


def _tokens(full_name: str) -> tuple[str, str]:
    parts = normalize_person_name(full_name).replace("'", "").replace("-", "").split()
    return (parts[0], parts[-1]) if len(parts) >= 2 else (parts[0], parts[0]) if parts else ("", "")


def render_pattern(pattern: str, first: str, last: str) -> str:
    options = {
        "firstname.lastname": f"{first}.{last}",
        "firstnamelastname": f"{first}{last}",
        "f.lastname": f"{first[:1]}.{last}",
        "firstinitiallastname": f"{first[:1]}{last}",
        "lastname.firstname": f"{last}.{first}",
        "firstname.l": f"{first}.{last[:1]}",
        "firstname": first,
        "lastname": last,
    }
    return options.get(pattern, "")


def identify_pattern(email: str, person_name: str) -> str | None:
    normalized = normalize_email(email)
    first, last = _tokens(person_name)
    if not normalized or not first or not last:
        return None
    local = normalized.split("@", 1)[0]
    for pattern in (
        "firstname.lastname", "firstnamelastname", "f.lastname", "firstinitiallastname",
        "lastname.firstname", "firstname.l", "firstname", "lastname",
    ):
        if render_pattern(pattern, first, last) == local:
            return pattern
    return None


def learn_patterns(published: list[tuple[str, str]]) -> list[LearnedPattern]:
    counts: Counter[str] = Counter()
    for email, person_name in published:
        local = email.lower().split("@", 1)[0]
        if local in GENERIC_LOCALS:
            continue
        if pattern := identify_pattern(email, person_name):
            counts[pattern] += 1
    learned = []
    for name, count in counts.most_common():
        strength = "strong" if count >= 3 else "moderate" if count >= 2 else "weak"
        learned.append(LearnedPattern(name=name, observations=count, strength=strength))
    return learned


def generate_pattern_candidates(
    person_name: str,
    domain: str,
    patterns: list[LearnedPattern],
    *,
    max_candidates: int = 6,
    allow_blind_fallback: bool = True,
) -> list[dict[str, object]]:
    first, last = _tokens(person_name)
    if not first or not last:
        return []
    ordered = list(patterns)
    if not ordered and allow_blind_fallback:
        ordered = [
            LearnedPattern("firstname.lastname", 0, "none"),
            LearnedPattern("f.lastname", 0, "none"),
        ]
    result: list[dict[str, object]] = []
    seen: set[str] = set()
    for pattern in ordered:
        local = render_pattern(pattern.name, first, last)
        email = normalize_email(f"{local}@{domain}") if local else None
        if not email or email in seen:
            continue
        seen.add(email)
        result.append(
            {
                "email": email,
                "pattern": pattern.name,
                "pattern_observations": pattern.observations,
                "pattern_strength": pattern.strength,
                "person_match_state": (
                    "exact_person_pattern_confirmed" if pattern.observations >= 2 else "name_only_guess"
                ),
            }
        )
        if len(result) >= max_candidates:
            break
    return result
