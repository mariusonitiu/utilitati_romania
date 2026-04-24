from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMENIU

STORAGE_KEY = "utilitati_romania_citiri"
STORAGE_VERSION = 1
CACHE_KEY = "citiri_storage_cache"


def _cache_root(hass: HomeAssistant) -> dict[str, Any]:
    domeniu_data = hass.data.setdefault(DOMENIU, {})
    cache = domeniu_data.setdefault(CACHE_KEY, {})
    return cache


async def async_incarca_cache_citiri(hass: HomeAssistant) -> dict[str, Any]:
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    data = await store.async_load()
    cache = data if isinstance(data, dict) else {}
    hass.data.setdefault(DOMENIU, {})[CACHE_KEY] = cache
    return cache


async def async_salveaza_cache_citiri(hass: HomeAssistant) -> None:
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    cache = _cache_root(hass)
    await store.async_save(cache)


async def async_salveaza_citire(
    hass: HomeAssistant,
    furnizor: str,
    id_cont: str,
    valoare: float,
) -> None:
    cache = _cache_root(hass)
    key = f"{furnizor}_{id_cont}"
    cache[key] = {
        "valoare": valoare,
        "timestamp": datetime.now().isoformat(),
    }
    await async_salveaza_cache_citiri(hass)


def obtine_citire_cache(
    hass: HomeAssistant,
    furnizor: str,
    id_cont: str,
) -> dict[str, Any] | None:
    cache = _cache_root(hass)
    value = cache.get(f"{furnizor}_{id_cont}")
    return value if isinstance(value, dict) else None