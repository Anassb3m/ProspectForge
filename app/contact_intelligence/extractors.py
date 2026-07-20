"""Deterministic extraction of public business contact facts from HTML."""

from __future__ import annotations

import html as html_module
import json
import io
import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from app.contact_intelligence.types import ContactPointFact, EvidenceFact, PersonFact

EMAIL_RE = re.compile(r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,24})(?![\w.-])", re.I)
OBFUSCATED_EMAIL_RE = re.compile(
    r"\b([a-z0-9._%+-]{1,64})\s*(?:\[\s*at\s*\]|\(\s*at\s*\)|\bat\b|arobase)\s*"
    r"([a-z0-9-]+(?:(?:\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\bdot\b|point)\s*)[a-z0-9-]+)+"
    r"|[a-z0-9-]+(?:\.[a-z0-9-]+)+)\b",
    re.I,
)
PHONE_RE = re.compile(r"(?<!\d)(?:(?:\+|00)33|0)\s*[1-9](?:[\s.()-]*\d{2}){4}(?!\d)")
GENERIC_LOCALS = {
    "contact", "info", "hello", "accueil", "commercial", "direction", "support", "sav",
    "maintenance", "rh", "recrutement", "admin", "administration", "facturation", "office",
}
ROLE_TERMS: tuple[tuple[str, str, int], ...] = (
    ("directeur des operations", "operations", 100),
    ("directrice des operations", "operations", 100),
    ("responsable operations", "operations", 95),
    ("directeur exploitation", "exploitation", 96),
    ("directrice exploitation", "exploitation", 96),
    ("responsable exploitation", "exploitation", 92),
    ("responsable maintenance", "maintenance", 94),
    ("directeur technique", "technical", 92),
    ("directrice technique", "technical", 92),
    ("responsable technique", "technical", 88),
    ("responsable sav", "service", 88),
    ("responsable service", "service", 84),
    ("responsable planification", "planning_methods", 88),
    ("responsable methodes", "planning_methods", 86),
    ("president", "executive", 73),
    ("presidente", "executive", 73),
    ("directeur general", "executive", 82),
    ("directrice generale", "executive", 82),
    ("gerant", "owner", 78),
    ("gerante", "owner", 78),
    ("fondateur", "owner", 76),
    ("fondatrice", "owner", 76),
    ("representant legal", "legal_representative", 45),
    ("representante legale", "legal_representative", 45),
    ("responsable commercial", "commercial", 64),
    ("daf", "administration_finance", 48),
)
NAME_RE = re.compile(
    r"\b([A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’-]{1,40}(?:\s+[A-ZÀ-ÖØ-Ý][A-Za-zÀ-ÖØ-öø-ÿ'’-]{1,40}){1,3})\b"
)


def strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char)
    )


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", html_module.unescape(value)).strip()


def normalize_person_name(value: str) -> str:
    value = strip_accents(normalize_space(value)).lower().replace("’", "'")
    value = re.sub(r"^(m(?:me|lle)?|monsieur|madame|dr)\.?\s+", "", value)
    return re.sub(r"[^a-z0-9' -]", "", value).strip()


def normalize_role(value: str | None) -> tuple[str, str, int]:
    normalized = strip_accents(normalize_space(value or "")).lower()
    normalized = re.sub(r"[^a-z0-9 ]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for term, category, score in ROLE_TERMS:
        if term in normalized:
            return normalized, category, score
    return normalized or "unknown", "other" if normalized else "unknown", 20 if normalized else 0


def normalize_email(value: str) -> str | None:
    email = value.strip().strip(".,;:<>[]()\"'").lower()
    if len(email) > 320 or not EMAIL_RE.fullmatch(email):
        return None
    local, domain = email.rsplit("@", 1)
    if ".." in email or local.startswith(".") or local.endswith(".") or domain.startswith("-"):
        return None
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    return f"{local}@{domain}"


def extract_emails(text: str) -> list[str]:
    found = {email for match in EMAIL_RE.findall(text) if (email := normalize_email(match))}
    for match in OBFUSCATED_EMAIL_RE.finditer(text):
        local, domain_raw = match.groups()
        domain = re.sub(
            r"\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\bdot\b|point|\.)\s*", ".", domain_raw,
            flags=re.I,
        )
        if email := normalize_email(f"{local}@{domain}"):
            found.add(email)
    return sorted(found)


def normalize_phone(value: str, country: str = "FR") -> str | None:
    raw = re.sub(r"[^\d+]", "", value.replace("00", "+", 1) if value.startswith("00") else value)
    try:
        import phonenumbers  # type: ignore[import-not-found]

        parsed = phonenumbers.parse(raw, country)
        if not phonenumbers.is_possible_number(parsed):
            return None
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except ImportError:
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 10 and digits.startswith("0"):
            return "+33" + digits[1:]
        if len(digits) == 11 and digits.startswith("33"):
            return "+" + digits
        return raw if raw.startswith("+") and 8 <= len(digits) <= 15 else None
    except Exception:
        return None


def redact_email(value: str) -> str:
    if "@" not in value:
        return "[redacted]"
    local, domain = value.split("@", 1)
    return f"{local[:1]}***@{domain}"


def classify_form(url: str, title: str, text: str) -> str:
    haystack = strip_accents(f"{url} {title} {text}").lower()
    if any(term in haystack for term in ("devis", "commercial", "demande de prix")):
        return "sales_quote"
    if any(term in haystack for term in ("maintenance", "intervention", "depannage")):
        return "maintenance_request"
    if any(term in haystack for term in ("sav", "support", "assistance")):
        return "support"
    if any(term in haystack for term in ("recrutement", "carriere", "emploi")):
        return "recruitment"
    if "contact" in haystack:
        return "general_contact"
    return "unknown"


@dataclass(slots=True)
class _Form:
    action: str = ""
    inputs: list[str] = field(default_factory=list)
    captcha: bool = False


class _ContactHTMLParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = ""
        self._in_title = False
        self._skip_depth = 0
        self._script_type = ""
        self._script_text: list[str] = []
        self.json_ld: list[object] = []
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []
        self.forms: list[_Form] = []
        self._form: _Form | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag in {"style", "noscript"}:
            self._skip_depth += 1
        if tag == "script":
            self._script_type = values.get("type", "").lower()
            self._script_text = []
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a" and values.get("href"):
            self._anchor_href = urljoin(self.base_url, values["href"])
            self._anchor_text = []
        elif tag == "form":
            self._form = _Form(action=urljoin(self.base_url, values.get("action") or self.base_url))
        elif self._form is not None:
            marker = " ".join(values.values()).lower()
            self._form.captcha = self._form.captcha or "captcha" in marker or "recaptcha" in marker
            if tag in {"input", "textarea", "select"}:
                name = values.get("name") or values.get("type") or tag
                self._form.inputs.append(name[:80])

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            if "ld+json" in self._script_type:
                try:
                    self.json_ld.append(json.loads("".join(self._script_text)))
                except (json.JSONDecodeError, ValueError):
                    pass
            self._skip_depth = max(0, self._skip_depth - 1)
            self._script_type = ""
        elif tag in {"style", "noscript"}:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "title":
            self._in_title = False
        elif tag == "a" and self._anchor_href:
            self.links.append((self._anchor_href, normalize_space(" ".join(self._anchor_text))))
            self._anchor_href = None
            self._anchor_text = []
        elif tag == "form" and self._form is not None:
            self.forms.append(self._form)
            self._form = None

    def handle_data(self, data: str) -> None:
        if self._script_type:
            self._script_text.append(data)
        if self._skip_depth:
            return
        clean = normalize_space(data)
        if not clean:
            return
        self.text_parts.append(clean)
        if self._in_title:
            self.title = normalize_space(f"{self.title} {clean}")
        if self._anchor_href:
            self._anchor_text.append(clean)


@dataclass(slots=True)
class ParsedPage:
    title: str
    text: str
    links: list[tuple[str, str]]
    people: list[PersonFact]
    contact_points: list[ContactPointFact]
    evidence: list[EvidenceFact]


def _walk_json_ld(value: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(_walk_json_ld(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_json_ld(child))
    return found


def _extract_people(text_parts: list[str], json_ld: list[object], source_url: str) -> list[PersonFact]:
    people: dict[str, PersonFact] = {}
    for root in json_ld:
        for item in _walk_json_ld(root):
            types = item.get("@type")
            type_values = {types} if isinstance(types, str) else set(types or [])
            if "Person" not in type_values or not item.get("name"):
                continue
            name = normalize_space(str(item["name"]))
            title = normalize_space(str(item.get("jobTitle") or "")) or None
            normalized_role, category, score = normalize_role(title)
            key = normalize_person_name(name)
            if key:
                people[key] = PersonFact(
                    full_name=name,
                    job_title=title,
                    role_category=category,
                    buyer_role_score=score,
                    company_match_state="strong",
                    identity_confidence=90,
                    linkedin_url=(str(item.get("sameAs")) if "linkedin.com/in/" in str(item.get("sameAs")) else None),
                    source_url=source_url,
                    metadata={"normalized_role": normalized_role, "structured_data": True},
                )
    for index, part in enumerate(text_parts):
        normalized_role, category, score = normalize_role(part)
        if score < 40:
            continue
        neighborhood = " ".join(text_parts[max(0, index - 2): index + 3])
        for match in NAME_RE.findall(neighborhood):
            name = normalize_space(match)
            key = normalize_person_name(name)
            if not key or any(term in key for term in ("responsable", "directeur", "service", "societe")):
                continue
            current = people.get(key)
            if current is None or score > current.buyer_role_score:
                people[key] = PersonFact(
                    full_name=name,
                    job_title=part[:200],
                    role_category=category,
                    buyer_role_score=score,
                    company_match_state="probable",
                    identity_confidence=70,
                    source_url=source_url,
                    metadata={"normalized_role": normalized_role},
                )
    return sorted(people.values(), key=lambda person: person.buyer_role_score, reverse=True)


def parse_html_contacts(html: str, source_url: str) -> ParsedPage:
    parser = _ContactHTMLParser(source_url)
    parser.feed(html[:2_000_000])
    text = normalize_space(" ".join(parser.text_parts))
    host = (urlsplit(source_url).hostname or "").lower().removeprefix("www.")
    contacts: dict[tuple[str, str], ContactPointFact] = {}

    mailto_values = [urlsplit(url).path for url, _ in parser.links if url.lower().startswith("mailto:")]
    for email in extract_emails(" ".join([text, *mailto_values])):
        local, domain = email.split("@", 1)
        if domain.lower().removeprefix("www.") != host:
            continue
        generic = local.split("+", 1)[0] in GENERIC_LOCALS
        publication = "published_generic" if generic else "published_personal"
        person_match = "generic_company_mailbox" if generic else "strong_person_match"
        contacts[("email", email)] = ContactPointFact(
            kind="email", value=email, publication_state=publication,
            person_match_state=person_match, source_url=source_url,
            confidence=72 if generic else 82,
        )

    for root in parser.json_ld:
        for item in _walk_json_ld(root):
            types = item.get("@type")
            type_values = {types} if isinstance(types, str) else set(types or [])
            is_person = "Person" in type_values
            is_company = bool(type_values & {"Organization", "LocalBusiness", "Corporation"})
            if not (is_person or is_company or "ContactPoint" in type_values):
                continue
            if email := normalize_email(str(item.get("email") or "")):
                local, domain = email.split("@", 1)
                if domain.removeprefix("www.") == host:
                    generic = local in GENERIC_LOCALS or not is_person
                    contacts[("email", email)] = ContactPointFact(
                        kind="email", value=email,
                        publication_state="published_generic" if generic else "published_personal",
                        person_match_state=(
                            "generic_company_mailbox" if generic else "exact_person_published"
                        ),
                        source_class="structured_data", source_url=source_url,
                        person_name=(str(item.get("name")) if is_person and item.get("name") else None),
                        confidence=88,
                    )
            if phone := normalize_phone(str(item.get("telephone") or "")):
                contacts[("phone", phone)] = ContactPointFact(
                    kind="phone", value=phone, publication_state="published_generic",
                    person_match_state="generic_company_mailbox", source_class="structured_data",
                    source_url=source_url, confidence=85,
                    metadata={"phone_type": "personal_direct" if is_person else "switchboard"},
                )
            same_as = item.get("sameAs")
            profiles = [same_as] if isinstance(same_as, str) else same_as if isinstance(same_as, list) else []
            for profile in profiles:
                if isinstance(profile, str) and "linkedin.com/" in profile.lower():
                    contacts[("linkedin", profile)] = ContactPointFact(
                        kind="linkedin", value=profile,
                        publication_state="published_personal" if is_person else "published_generic",
                        person_match_state="strong_person_match" if is_person else "generic_company_mailbox",
                        source_class="structured_data", source_url=source_url,
                        person_name=(str(item.get("name")) if is_person and item.get("name") else None),
                        confidence=82,
                    )

    tel_values = [urlsplit(url).path for url, _ in parser.links if url.lower().startswith("tel:")]
    for raw in [*PHONE_RE.findall(text), *tel_values]:
        if phone := normalize_phone(raw):
            contacts[("phone", phone)] = ContactPointFact(
                kind="phone", value=phone, publication_state="published_generic",
                person_match_state="generic_company_mailbox", source_url=source_url,
                confidence=75, metadata={"phone_type": "switchboard"},
            )

    for form in parser.forms:
        category = classify_form(form.action, parser.title, text[:1000])
        contacts[("contact_form", form.action)] = ContactPointFact(
            kind="contact_form", value=form.action, publication_state="published_generic",
            person_match_state="generic_company_mailbox", source_url=source_url, confidence=70,
            metadata={"category": category, "required_fields": form.inputs[:30], "has_captcha": form.captcha},
        )

    for url, _anchor in parser.links:
        if "linkedin.com/in/" in url.lower():
            contacts[("linkedin", url)] = ContactPointFact(
                kind="linkedin", value=url, publication_state="published_personal",
                person_match_state="strong_person_match", source_url=source_url, confidence=75,
            )

    people = _extract_people(parser.text_parts, parser.json_ld, source_url)
    evidence: list[EvidenceFact] = []
    for point in contacts.values():
        safe_excerpt = redact_email(point.value) if point.kind == "email" else point.kind
        evidence.append(
            EvidenceFact(
                evidence_type=f"published_{point.kind}", source_adapter="official_website",
                source_url=source_url, excerpt=safe_excerpt, page_title=parser.title[:300],
                confidence=point.confidence, contact_value=point.value,
            )
        )
    for person in people:
        evidence.append(
            EvidenceFact(
                evidence_type="published_person", source_adapter="official_website",
                source_url=source_url, excerpt=f"{person.full_name} — {person.job_title or 'role unstated'}"[:600],
                page_title=parser.title[:300], confidence=person.identity_confidence,
                person_name=person.full_name,
            )
        )
    return ParsedPage(
        title=parser.title[:300], text=text, links=parser.links,
        people=people, contact_points=list(contacts.values()), evidence=evidence,
    )


def parse_pdf_contacts(content: bytes, source_url: str, *, max_pages: int = 30) -> ParsedPage:
    """Extract text only from a bounded official-domain PDF; OCR and attachments are ignored."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - production dependency, explicit degradation
        raise ValueError("pdf_parser_unavailable") from exc
    reader = PdfReader(io.BytesIO(content), strict=False)
    if reader.is_encrypted or len(reader.pages) > max_pages:
        raise ValueError("pdf_encrypted_or_too_many_pages")
    merged_people: dict[tuple[str, str], PersonFact] = {}
    merged_points: dict[tuple[str, str], ContactPointFact] = {}
    merged_evidence: list[EvidenceFact] = []
    text_parts: list[str] = []
    for index, page in enumerate(reader.pages):
        page_text = (page.extract_text() or "")[:200_000]
        if not page_text:
            continue
        text_parts.append(page_text)
        escaped = html_module.escape(page_text).replace("\n", "</p><p>")
        parsed = parse_html_contacts(
            f"<html><title>PDF page {index + 1}</title><p>{escaped}</p></html>", source_url
        )
        for person in parsed.people:
            merged_people[(normalize_person_name(person.full_name), person.job_title or "")] = person
        for point in parsed.contact_points:
            merged_points[(point.kind, point.value)] = point
        for evidence in parsed.evidence:
            evidence.metadata["pdf_page"] = index + 1
            evidence.source_adapter = "official_pdf"
            merged_evidence.append(evidence)
    return ParsedPage(
        title=urlsplit(source_url).path.rsplit("/", 1)[-1][:300],
        text=normalize_space(" ".join(text_parts)), links=[],
        people=list(merged_people.values()), contact_points=list(merged_points.values()),
        evidence=merged_evidence,
    )
