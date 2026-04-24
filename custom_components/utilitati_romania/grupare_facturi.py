from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMENIU

_STORAGE_VERSION = 1
_STORAGE_KEY = "utilitati_romania_grupari_facturi"
_DATA_KEY = "_grupari_facturi"
_PAYLOAD_KEY = "grupari"


def _domain_data(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data.setdefault(DOMENIU, {})


def _cache(hass: HomeAssistant) -> dict[str, str]:
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


def construieste_cheie_grupare_factura(
    entry_id: str,
    furnizor: str | None,
    id_cont: str | None,
) -> str | None:
    entry_id_text = str(entry_id or "").strip()
    furnizor_text = str(furnizor or "").strip().lower()
    id_cont_text = str(id_cont or "").strip()

    if not entry_id_text or not furnizor_text or not id_cont_text:
        return None

    return f"{entry_id_text}:{furnizor_text}:{id_cont_text}"


async def async_incarca_grupari_facturi(hass: HomeAssistant) -> dict[str, str]:
    loaded = await _store(hass).async_load()
    payload = loaded if isinstance(loaded, dict) else {}
    values = payload.get(_PAYLOAD_KEY, {}) if isinstance(payload, dict) else {}
    cache = _cache(hass)
    cache.clear()

    if isinstance(values, dict):
        for key, value in values.items():
            key_text = str(key or "").strip()
            value_text = str(value or "").strip()
            if key_text and value_text:
                cache[key_text] = value_text

    return dict(cache)


async def async_salveaza_grupari_facturi(hass: HomeAssistant) -> None:
    await _store(hass).async_save({_PAYLOAD_KEY: dict(sorted(_cache(hass).items()))})


async def async_obtine_grupare_factura(
    hass: HomeAssistant,
    entry_id: str,
    furnizor: str | None,
    id_cont: str | None,
) -> str | None:
    if not _cache(hass):
        await async_incarca_grupari_facturi(hass)

    return obtine_grupare_factura(hass, entry_id, furnizor, id_cont)


async def async_seteaza_grupare_factura(
    hass: HomeAssistant,
    entry_id: str,
    furnizor: str | None,
    id_cont: str | None,
    eticheta: str | None,
) -> None:
    cheie = construieste_cheie_grupare_factura(entry_id, furnizor, id_cont)
    if not cheie:
        return

    cache = _cache(hass)
    eticheta_text = str(eticheta or "").strip()
    if eticheta_text:
        cache[cheie] = eticheta_text
    else:
        cache.pop(cheie, None)

    await async_salveaza_grupari_facturi(hass)


def obtine_grupare_factura(
    hass: HomeAssistant,
    entry_id: str,
    furnizor: str | None,
    id_cont: str | None,
) -> str | None:
    cheie = construieste_cheie_grupare_factura(entry_id, furnizor, id_cont)
    if not cheie:
        return None

    value = _cache(hass).get(cheie)
    value_text = str(value or "").strip()
    return value_text or None
