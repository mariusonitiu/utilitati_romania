from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMENIU
from .naming import build_location_short_name, build_provider_slug


def alias_loc_consum(nume: str | None, adresa: str | None, id_cont: str | None) -> str:
    return build_location_short_name(adresa or nume, nume or id_cont or "Cont")


def slug_loc_consum(id_cont: str | None, alias: str | None, adresa: str | None = None) -> str:
    return build_provider_slug("hidroelectrica", adresa or alias, id_cont or alias or "cont")


def info_device_hidro(entry_id: str, cont) -> DeviceInfo:
    alias = alias_loc_consum(getattr(cont, 'nume', None), getattr(cont, 'adresa', None), getattr(cont, 'id_cont', None))
    return DeviceInfo(
        identifiers={(DOMENIU, f"{entry_id}_hidro_{getattr(cont, 'id_cont', '')}")},
        name=f"Hidroelectrica – {alias}",
        manufacturer="onitium",
        model="Hidroelectrica",
    )
