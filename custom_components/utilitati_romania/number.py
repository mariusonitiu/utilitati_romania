from __future__ import annotations

from homeassistant.components.number import NumberEntity, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordonator import CoordonatorUtilitatiRomania
from .const import DOMENIU
from .entitate import EntitateUtilitatiRomania
from .hidro_device import alias_loc_consum, info_device_hidro, slug_loc_consum
from .eon_device import alias_loc_eon, info_device_eon, slug_loc_eon
from .myelectrica_device import alias_loc_myelectrica, info_device_myelectrica, slug_loc_myelectrica


def _valoare_consum_curent(coordonator: CoordonatorUtilitatiRomania, id_cont: str, cheie: str) -> float | None:
    data = getattr(coordonator, 'data', None)
    consumuri = getattr(data, 'consumuri', None) or []
    for consum in consumuri:
        if getattr(consum, 'id_cont', None) != id_cont:
            continue
        if getattr(consum, 'cheie', None) != cheie:
            continue
        valoare = getattr(consum, 'valoare', None)
        try:
            return float(valoare) if valoare is not None else None
        except (TypeError, ValueError):
            return None
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordonator: CoordonatorUtilitatiRomania = hass.data[DOMENIU][entry.entry_id]
    entitati: list[NumberEntity] = []

    if coordonator.data:
        if coordonator.data.furnizor == "hidroelectrica":
            for cont in coordonator.data.conturi:
                entitati.append(NumarIndexHidro(coordonator, cont))

        elif coordonator.data.furnizor == "eon":
            for cont in coordonator.data.conturi:
                entitati.append(NumarIndexEon(coordonator, cont))

        elif coordonator.data.furnizor == "myelectrica":
            for cont in coordonator.data.conturi:
                raw = getattr(cont, "date_brute", None) or {}
                meter = raw.get("meter_list") or {}
                contoare = meter.get("to_Contor", []) or []
                are_contor = bool(
                    contoare
                    and (
                        contoare[0].get("SerieContor")
                        or ((contoare[0].get("to_Cadran") or [{}])[0].get("RegisterCode"))
                    )
                )
                if are_contor:
                    entitati.append(NumarIndexMyElectrica(coordonator, cont))

    async_add_entities(entitati)


class NumarIndexHidro(EntitateUtilitatiRomania, RestoreNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 99999999
    _attr_native_step = 1
    _attr_icon = "mdi:counter"
    _attr_mode = "box"
    _attr_native_unit_of_measurement = "kWh"

    def __init__(self, coordonator: CoordonatorUtilitatiRomania, cont) -> None:
        super().__init__(coordonator)
        self.cont = cont

        alias = alias_loc_consum(cont.nume, cont.adresa, cont.id_cont)
        slug = slug_loc_consum(cont.id_cont, alias, cont.adresa)

        self._attr_unique_id = (
            f"{coordonator.intrare.entry_id}_hidro_{cont.id_cont}_index_energie_electrica"
        )
        self._attr_name = f"Index energie electrică {alias}"
        self._attr_device_info = info_device_hidro(coordonator.intrare.entry_id, cont)
        self._attr_native_value = 0
        self._attr_suggested_object_id = (
            f"hidro_{cont.id_cont}_{slug}_index_energie_electrica"
        )
        self.entity_id = f"number.hidro_{cont.id_cont}_{slug}_index_energie_electrica"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        ultima_stare = await self.async_get_last_number_data()
        if ultima_stare and ultima_stare.native_value is not None:
            self._attr_native_value = ultima_stare.native_value
        else:
            valoare_curenta = _valoare_consum_curent(self.coordinator, self.cont.id_cont, 'index_energie_electrica')
            if valoare_curenta is not None:
                self._attr_native_value = valoare_curenta

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()


class NumarIndexEon(EntitateUtilitatiRomania, RestoreNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 99999999
    _attr_native_step = 1
    _attr_icon = "mdi:counter"
    _attr_mode = "box"

    def __init__(self, coordonator: CoordonatorUtilitatiRomania, cont) -> None:
        super().__init__(coordonator)
        self.cont = cont

        alias = alias_loc_eon(cont.nume, cont.adresa, cont.id_cont)
        slug = slug_loc_eon(cont.id_cont, alias, cont.adresa)
        tip = cont.tip_serviciu or cont.tip_utilitate or "curent"

        self._attr_native_unit_of_measurement = "m³" if tip == "gaz" else "kWh"
        self._attr_unique_id = f"{coordonator.intrare.entry_id}_eon_{cont.id_cont}_index"
        self._attr_name = (
            f"Index {'gaz' if tip == 'gaz' else 'energie electrică'} {alias}"
        )
        self._attr_device_info = info_device_eon(coordonator.intrare.entry_id, cont)
        self._attr_suggested_object_id = f"eon_{cont.id_cont}_{slug}_index"
        self.entity_id = f"number.eon_{cont.id_cont}_{slug}_index"
        self._attr_native_value = 0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        ultima_stare = await self.async_get_last_number_data()
        if ultima_stare and ultima_stare.native_value is not None:
            self._attr_native_value = ultima_stare.native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()


class NumarIndexMyElectrica(EntitateUtilitatiRomania, RestoreNumber):
    _attr_native_min_value = 0
    _attr_native_max_value = 99999999
    _attr_native_step = 1
    _attr_icon = "mdi:counter"
    _attr_mode = "box"

    def __init__(self, coordonator: CoordonatorUtilitatiRomania, cont) -> None:
        super().__init__(coordonator)
        self.cont = cont

        alias = alias_loc_myelectrica(cont.nume, cont.adresa, cont.id_cont)
        slug = slug_loc_myelectrica(cont.id_cont, alias, cont.adresa)
        tip = str(cont.tip_serviciu or cont.tip_utilitate or "").lower()

        self._attr_native_unit_of_measurement = "m³" if tip == "gaz" else "kWh"
        self._attr_unique_id = (
            f"{coordonator.intrare.entry_id}_myelectrica_{cont.id_cont}_index_contor"
        )
        self._attr_name = f"Index contor {alias}"
        self._attr_device_info = info_device_myelectrica(coordonator.intrare.entry_id, cont)
        self._attr_suggested_object_id = f"utilitati_romania_myelectrica_{slug}_index_contor"
        self.entity_id = f"number.utilitati_romania_myelectrica_{slug}_index_contor"
        self._attr_native_value = 0

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        ultima_stare = await self.async_get_last_number_data()
        if ultima_stare and ultima_stare.native_value is not None:
            self._attr_native_value = ultima_stare.native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()
