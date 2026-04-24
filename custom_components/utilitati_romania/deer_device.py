from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMENIU
from .naming import build_location_short_name, build_provider_slug


def alias_loc_deer(nume: str | None, adresa: str | None, pod: str) -> str:
    return build_location_short_name(adresa or nume, nume or f"POD {pod}")


def slug_loc_deer(pod: str, alias: str, adresa: str | None = None, nume: str | None = None) -> str:
    return build_provider_slug("deer", adresa or nume or alias, pod)


def info_device_deer(entry_id: str, cont) -> DeviceInfo:
    alias = alias_loc_deer(getattr(cont, "nume", None), getattr(cont, "adresa", None), getattr(cont, "id_cont", "pod"))
    return DeviceInfo(
        identifiers={(DOMENIU, f"{entry_id}_deer_{getattr(cont, 'id_cont', 'pod')}")},
        name=f"DEER – {alias}",
        manufacturer="Distribuție Energie Electrică România",
        model="Portal date măsură",
    )
