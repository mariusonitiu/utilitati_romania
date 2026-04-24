from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMENIU
from .naming import build_location_short_name, build_provider_slug


def alias_loc_myelectrica(nume: str | None, adresa: str | None, nlc: str) -> str:
    return build_location_short_name(adresa or nume, nume or f"NLC {nlc}")


def slug_loc_myelectrica(nlc: str, alias: str, adresa: str | None = None) -> str:
    return build_provider_slug("myelectrica", adresa or alias, nlc)


def info_device_myelectrica(entry_id: str, cont) -> DeviceInfo:
    alias = alias_loc_myelectrica(getattr(cont, 'nume', None), getattr(cont, 'adresa', None), getattr(cont, 'id_cont', 'cont'))
    return DeviceInfo(
        identifiers={(DOMENIU, f"{entry_id}_myelectrica_{getattr(cont, 'id_cont', 'cont')}")},
        name=f"myElectrica – {alias}",
        manufacturer="Electrica Furnizare",
        model="myElectrica",
    )
