from __future__ import annotations

import re
from typing import Any

from .naming import normalize_text


_LOCALITY_WORDS = {
    "sibiu",
    "selimbar",
    "șelimbăr",
    "bucuresti",
    "bucurești",
    "cluj",
    "timisoara",
    "timișoara",
    "brasov",
    "brașov",
    "iasi",
    "iași",
    "constanta",
    "constanța",
    "oradea",
    "ploiesti",
    "ploiești",
}

_COUNTY_CODES = {
    "sb",
    "cj",
    "bv",
    "bh",
    "b",
    "if",
    "tm",
    "is",
    "ct",
    "ph",
    "ms",
    "ag",
    "ab",
    "mm",
    "sv",
    "nt",
    "bc",
    "vn",
    "bt",
    "db",
    "gl",
    "br",
    "dj",
    "gj",
    "vl",
    "hd",
    "cs",
    "tr",
    "ot",
    "il",
    "cl",
    "tl",
    "cv",
    "hr",
    "sj",
    "sm",
    "bn",
    "bz",
    "gr",
}

_STREET_PREFIXES = {
    "strada",
    "str",
    "str.",
    "aleea",
    "alee",
    "ale",
    "ale.",
    "bulevard",
    "bulevardul",
    "bd",
    "bd.",
    "calea",
    "cal",
    "cal.",
    "soseaua",
    "șoseaua",
    "sos",
    "sos.",
    "piata",
    "piața",
    "p-ta",
    "pta",
    "intrarea",
    "intr",
    "intr.",
    "drumul",
    "drum",
    "dr",
    "dr.",
    "splaiul",
    "spl",
    "spl.",
    "prelungirea",
    "prel",
    "prel.",
}

_STOP_MARKERS = {
    "nr",
    "nr.",
    "numar",
    "numărul",
    "bl",
    "bl.",
    "bloc",
    "sc",
    "sc.",
    "scara",
    "et",
    "et.",
    "etaj",
    "ap",
    "ap.",
    "apartament",
    "jud",
    "jud.",
    "judet",
    "judetul",
    "localitate",
    "loc",
    "consum",
    "adresa",
    "adresă",
    "contract",
    "client",
    "cod",
    "pod",
}


def _append_candidate(candidates: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in candidates:
        candidates.append(text)


def extract_location_candidates(cont_or_value: Any) -> list[str]:
    if cont_or_value is None:
        return []

    if isinstance(cont_or_value, str):
        text = cont_or_value.strip()
        return [text] if text else []

    candidates: list[str] = []

    _append_candidate(candidates, getattr(cont_or_value, "adresa", None))
    _append_candidate(candidates, getattr(cont_or_value, "nume", None))

    raw = getattr(cont_or_value, "date_brute", None)
    if isinstance(raw, dict):
        for key in (
            "address",
            "service_address",
            "serviceAddress",
            "site_address",
            "siteAddress",
            "usageAddress",
            "consumptionAddress",
            "full_address",
            "addressLine",
            "premise_label",
            "premiseLabel",
            "loc_consum",
            "adresa_loc_consum",
            "consumption_place",
            "consumptionPlaceName",
            "usage_place",
            "specificIdForUtilityType",
            "adresa",
        ):
            _append_candidate(candidates, raw.get(key))

    return candidates


def _parts(value: str) -> list[str]:
    text = normalize_text(value)
    text = re.sub(r"\s*/\s*", ",", text)
    text = re.sub(r"\s*;\s*", ",", text)
    return [part.strip() for part in text.split(",") if part.strip()]


def _clean_segment_for_street(segment: str) -> str:
    text = normalize_text(segment).lower()
    tokens = re.split(r"[^a-z0-9ăâîșţșț]+", text)
    result: list[str] = []

    started = False
    for token in tokens:
        if not token:
            continue

        if token in _STREET_PREFIXES:
            started = True
            continue

        if token in _STOP_MARKERS:
            break

        if token in _LOCALITY_WORDS or token in _COUNTY_CODES:
            if started:
                break
            continue

        if re.fullmatch(r"\d+[a-z]?", token):
            break

        if token.isdigit():
            break

        started = True
        result.append(token)

    return " ".join(result).strip()


def _extract_from_labeled_or_inline(text: str) -> str | None:
    normalized = normalize_text(text)

    pattern = re.compile(
        r"(?:strada|str\.?|aleea|alee|ale\.?|bulevardul|bulevard|bd\.?|calea|cal\.?|"
        r"soseaua|șoseaua|sos\.?|piata|piața|p-?ta|intrarea|intr\.?|drumul|dr\.?|"
        r"splaiul|spl\.?|prelungirea|prel\.?)\s+([^,;/]+)",
        re.IGNORECASE,
    )
    match = pattern.search(normalized)
    if match:
        cleaned = _clean_segment_for_street(match.group(1))
        if cleaned:
            return cleaned

    # format de tip "Doamna Stanca 29 ..."
    match2 = re.search(r"([A-Za-zĂÂÎȘȚăâîșț][^,;/]*?)\s+\d+[A-Za-z]?", normalized)
    if match2:
        cleaned = _clean_segment_for_street(match2.group(1))
        if cleaned:
            return cleaned

    return None


def _extract_from_parts(text: str) -> str | None:
    parts = _parts(text)
    if not parts:
        return None

    # caz tipic Hidroelectrica: "14,Sevis,SIBIU,SB,550382"
    if len(parts) >= 2 and re.fullmatch(r"\d+[A-Za-z]?", parts[0]):
        second = _clean_segment_for_street(parts[1])
        if second:
            return second

    # caz tipic cu localitatea înainte: "Sibiu, Selimbar, Frasinului 10A ..."
    for part in parts:
        low = normalize_text(part).lower()
        if low in _LOCALITY_WORDS or low in _COUNTY_CODES or re.fullmatch(r"\d{4,6}", low):
            continue

        cleaned = _clean_segment_for_street(part)
        if cleaned:
            return cleaned

        match = re.match(r"([A-Za-zĂÂÎȘȚăâîșț][A-Za-zĂÂÎȘȚăâîșț \-]+?)\s+\d+[A-Za-z]?", normalize_text(part))
        if match:
            cleaned2 = _clean_segment_for_street(match.group(1))
            if cleaned2:
                return cleaned2

    return None


def _slugify(text: str) -> str:
    value = normalize_text(text).lower()
    value = "".join(ch if ch.isalnum() else "_" for ch in value)
    while "__" in value:
        value = value.replace("__", "_")
    return value.strip("_")


def normalize_facturi_location_key(cont_or_value: Any) -> str:
    candidates = extract_location_candidates(cont_or_value)

    for candidate in candidates:
        street = _extract_from_labeled_or_inline(candidate) or _extract_from_parts(candidate)
        if street:
            return _slugify(street)

    if hasattr(cont_or_value, "id_cont"):
        fallback = str(
            getattr(cont_or_value, "nume", None)
            or getattr(cont_or_value, "id_cont", None)
            or "locatie"
        )
        return _slugify(fallback) or "locatie"

    text = str(cont_or_value or "").strip()
    return _slugify(text) or "locatie"


def build_facturi_location_label(cont_or_value: Any) -> str:
    candidates = extract_location_candidates(cont_or_value)

    for candidate in candidates:
        street = _extract_from_labeled_or_inline(candidate) or _extract_from_parts(candidate)
        if street:
            return " ".join(word.capitalize() for word in street.split())

    if hasattr(cont_or_value, "nume"):
        fallback = str(
            getattr(cont_or_value, "nume", None)
            or getattr(cont_or_value, "id_cont", None)
            or "Locație"
        ).strip()
        return fallback or "Locație"

    text = str(cont_or_value or "").strip()
    return text or "Locație"