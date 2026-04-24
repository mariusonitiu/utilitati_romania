from __future__ import annotations

import re
import unicodedata

PREFIXE_STRAZI = {
    "strada", "str", "str.",
    "aleea", "alee", "ale", "ale.",
    "bulevard", "bulevardul", "bd", "bd.",
    "calea", "cal", "cal.",
    "soseaua", "sos", "sos.", "șoseaua", "şoseaua",
    "piata", "piața", "p-ta", "pta",
    "intrarea", "intr", "intr.", "int", "int.",
    "drumul", "drum", "dr", "dr.",
    "splaiul", "spl", "spl.",
    "prelungirea", "prel", "prel.",
}

TOKENURI_IGNORATE = PREFIXE_STRAZI | {
    "nr", "nr.", "numar", "numarul", "numărul",
    "bl", "bl.", "bloc", "sc", "sc.", "scara", "et", "et.", "ap", "ap.",
    "jud", "jud.", "judet", "judetul", "municipiul", "oras", "oraș", "sat", "comuna",
    "localitate", "loc", "consum", "adresa", "adresă", "contract", "cod", "client", "pod",
}

PREFIX_PATTERN = (
    r"(?:strada|str\.?|aleea|alee|ale\.?|bulevardul|bulevard|bd\.?|calea|cal\.?|"
    r"soseaua|sos\.?|piata|p-?ta|intrarea|intr\.?|drumul|dr\.?|splaiul|spl\.?|prelungirea|prel\.?)"
)


def normalize_text(text: str | None) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", value).strip()


def slugify_text(text: str | None) -> str:
    raw = normalize_text(text).lower()
    raw = re.sub(r"[^a-z0-9]+", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    return raw or "cont"


def _tokenize(text: str) -> list[str]:
    return [part for part in re.split(r"[^a-z0-9]+", text.lower()) if part]


def _source_parts(text: str) -> list[str]:
    cleaned = normalize_text(text)
    if not cleaned:
        return []
    cleaned = re.sub(r"(Localitate|Strada|Adresa|Adresă)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*/\s*", ", ", cleaned)
    return [p.strip() for p in re.split(r"[,;]", cleaned) if p.strip()]


def _candidate_from_labeled_street(text: str) -> str | None:
    raw = normalize_text(text)
    if not raw:
        return None
    match = re.search(rf"{PREFIX_PATTERN}\s*:?[ ]*([^,;/]+)", raw, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _candidate_from_parts(text: str) -> str | None:
    for part in _source_parts(text):
        lowered = part.lower()
        if re.search(rf"{PREFIX_PATTERN}", lowered, flags=re.IGNORECASE):
            lowered = re.sub(rf"^.*?{PREFIX_PATTERN}\s*", "", lowered, flags=re.IGNORECASE)
            return lowered.strip()
    parts = _source_parts(text)
    if not parts:
        return None
    # if first part looks like locality, second is probably street
    if len(parts) >= 2 and parts[0].lower() in {"sibiu", "selimbar"}:
        return parts[1]
    return parts[0]


def _street_tokens_from_text(text: str | None, fallback: str | None = None) -> list[str]:
    source = normalize_text(text)
    candidate = _candidate_from_labeled_street(source) if source else None
    if not candidate and source:
        candidate = _candidate_from_parts(source)
    if not candidate:
        candidate = normalize_text(fallback)
    tokens: list[str] = []
    for token in _tokenize(candidate):
        if token in TOKENURI_IGNORATE:
            continue
        if token.isdigit() or any(ch.isdigit() for ch in token):
            break
        tokens.append(token)
    if not tokens:
        for token in _tokenize(normalize_text(fallback)):
            if token in TOKENURI_IGNORATE or token.isdigit() or any(ch.isdigit() for ch in token):
                continue
            tokens.append(token)
        if not tokens:
            tokens = ["cont"]
    return tokens[:2]


def extract_street_slug(address: str | None, fallback: str | None = None) -> str:
    return "_".join(_street_tokens_from_text(address, fallback))


def build_location_short_name(address: str | None, fallback: str | None = None) -> str:
    tokens = _street_tokens_from_text(address, fallback)
    return " ".join(token.capitalize() for token in tokens) if tokens else (normalize_text(fallback) or "Cont")


def build_location_alias(address: str | None, fallback: str | None = None) -> str:
    street = build_location_short_name(address, fallback)
    locality = None
    raw = normalize_text(address)
    if raw:
        m = re.search(r"Localitate\s*:?[ ]*([^,;/]+)", raw, flags=re.IGNORECASE)
        if m:
            locality = m.group(1).strip().capitalize()
        else:
            parts = _source_parts(raw)
            if parts:
                cand = parts[0] if len(parts) == 1 else parts[-1]
                if cand and cand.lower() not in street.lower():
                    locality = cand.capitalize()
    return f"{street}, {locality}" if locality else street


def build_provider_slug(provider: str, address: str | None, fallback: str | None = None) -> str:
    return f"{provider}_{extract_street_slug(address, fallback)}"


def clean_association_name(name: str | None) -> str:
    text = normalize_text(name)
    if not text:
        return "Asociatie"
    text = re.sub(r"^asoc(?:iatie)?\.?\s+de\s+prop(?:rietari)?\.?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^asoc\.\s*", "", text, flags=re.IGNORECASE)
    return text.strip() or "Asociatie"
