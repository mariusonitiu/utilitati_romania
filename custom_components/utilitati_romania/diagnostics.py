from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CHEIE_LICENTA,
    CONF_DIGI_COOKIES,
    CONF_PAROLA,
    DATE_VERIFICARE_LICENTA,
    DOMENIU,
)
from .licentiere import mascheaza_cheia_licenta


def _mascheaza_cookies(cookies: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    rezultat: list[dict[str, Any]] = []
    for item in cookies or []:
        rezultat.append(
            {
                "key": item.get("key"),
                "value": "***",
                "domain": item.get("domain"),
                "path": item.get("path"),
                "secure": item.get("secure"),
                "expires": item.get("expires"),
            }
        )
    return rezultat


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coordonator = hass.data[DOMENIU][entry.entry_id]
    data = dict(entry.data)
    optiuni = dict(entry.options)
    for container in (data, optiuni):
        if CONF_PAROLA in container:
            container[CONF_PAROLA] = "***"
        if CONF_CHEIE_LICENTA in container:
            container[CONF_CHEIE_LICENTA] = mascheaza_cheia_licenta(container[CONF_CHEIE_LICENTA])
        if CONF_DIGI_COOKIES in container:
            container[CONF_DIGI_COOKIES] = _mascheaza_cookies(container[CONF_DIGI_COOKIES])
        if DATE_VERIFICARE_LICENTA in container and isinstance(container[DATE_VERIFICARE_LICENTA], dict):
            container[DATE_VERIFICARE_LICENTA] = {
                k: v
                for k, v in container[DATE_VERIFICARE_LICENTA].items()
                if k in {"valid", "status", "plan", "expires_at", "checked_at", "message", "connection_error"}
            }
    return {
        "intrare": data,
        "optiuni": optiuni,
        "instantaneu": None if coordonator.data is None else {
            "furnizor": coordonator.data.furnizor,
            "conturi": len(coordonator.data.conturi),
            "facturi": len(coordonator.data.facturi),
            "consumuri": len(coordonator.data.consumuri),
            "extra": coordonator.data.extra,
        },
    }
