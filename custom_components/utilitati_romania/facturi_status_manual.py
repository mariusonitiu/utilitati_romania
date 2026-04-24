from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMENIU
from .naming import normalize_text

_STORAGE_VERSION = 1
_STORAGE_KEY = "utilitati_romania_status_facturi_manual"
_DATA_KEY = "_status_facturi_manual"
_PAYLOAD_KEY = "overrides"


def _domain_data(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data.setdefault(DOMENIU, {})


def _cache(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    data = _domain_data(hass)
    cache = data.setdefault(_DATA_KEY, {})
    return cache if isinstance(cache, dict) else {}


def _store(hass: HomeAssistant) -> Store:
    data = _domain_data(hass)
    store = data.get(f"{_DATA_KEY}_store")
    if store is None:
        store = Store(hass, _STORAGE_VERSION, _STORAGE_KEY)
        data[f"{_DATA_KEY}_store"] = store
    return store


def _normalize_part(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "-"
    return normalize_text(text).lower().replace(" ", "_") or "-"


def construieste_cheie_status_factura(
    entry_id: str | None,
    furnizor: str | None,
    id_cont: str | None,
    invoice_id: str | None,
    invoice_title: str | None,
    issue_date: str | None,
    amount: Any,
    currency: str | None,
) -> str | None:
    entry_text = str(entry_id or "").strip()
    provider_text = str(furnizor or "").strip().lower()
    if not entry_text or not provider_text:
        return None

    return ":".join(
        [
            entry_text,
            provider_text,
            str(id_cont or "").strip() or "-",
            str(invoice_id or "").strip() or "-",
        ]
    )


async def async_incarca_statusuri_facturi_manuale(hass: HomeAssistant) -> dict[str, dict[str, Any]]:
    loaded = await _store(hass).async_load()
    payload = loaded if isinstance(loaded, dict) else {}
    values = payload.get(_PAYLOAD_KEY, {}) if isinstance(payload, dict) else {}
    cache = _cache(hass)
    cache.clear()

    if isinstance(values, dict):
        for key, value in values.items():
            key_text = str(key or "").strip()
            if not key_text or not isinstance(value, dict):
                continue
            status_text = str(value.get("status") or "").strip().lower()
            if status_text != "paid":
                continue
            cache[key_text] = {
                "status": "paid",
                "updated_at": str(value.get("updated_at") or "").strip() or None,
                "source": "manual",
            }

    return dict(cache)


async def async_salveaza_statusuri_facturi_manuale(hass: HomeAssistant) -> None:
    await _store(hass).async_save({_PAYLOAD_KEY: dict(sorted(_cache(hass).items()))})


async def async_obtine_status_manual_factura(
    hass: HomeAssistant,
    entry_id: str | None,
    furnizor: str | None,
    id_cont: str | None,
    invoice_id: str | None,
    invoice_title: str | None,
    issue_date: str | None,
    amount: Any,
    currency: str | None,
) -> dict[str, Any] | None:
    if not _cache(hass):
        await async_incarca_statusuri_facturi_manuale(hass)

    cheie = construieste_cheie_status_factura(
        entry_id,
        furnizor,
        id_cont,
        invoice_id,
        invoice_title,
        issue_date,
        amount,
        currency,
    )
    if not cheie:
        return None

    value = _cache(hass).get(cheie)
    return dict(value) if isinstance(value, dict) else None


async def async_seteaza_status_manual_factura(
    hass: HomeAssistant,
    entry_id: str | None,
    furnizor: str | None,
    id_cont: str | None,
    invoice_id: str | None,
    invoice_title: str | None,
    issue_date: str | None,
    amount: Any,
    currency: str | None,
    status: str | None,
) -> bool:
    cheie = construieste_cheie_status_factura(
        entry_id,
        furnizor,
        id_cont,
        invoice_id,
        invoice_title,
        issue_date,
        amount,
        currency,
    )
    if not cheie:
        return False

    cache = _cache(hass)
    status_text = str(status or "").strip().lower()
    if status_text == "paid":
        cache[cheie] = {
            "status": "paid",
            "updated_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "source": "manual",
        }
    else:
        cache.pop(cheie, None)

    await async_salveaza_statusuri_facturi_manuale(hass)
    return True
