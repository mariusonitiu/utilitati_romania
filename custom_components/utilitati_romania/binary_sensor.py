from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMENIU
from .coordonator import CoordonatorUtilitatiRomania
from .entitate import EntitateUtilitatiRomania


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordonator: CoordonatorUtilitatiRomania = hass.data[DOMENIU][entry.entry_id]
    entitati: list[BinarySensorEntity] = []

    if coordonator.data and coordonator.data.furnizor == "digi":
        entitati.append(DigiNecesitaReautentificareBinarySensor(coordonator))
        entitati.append(DigiAreRestanteBinarySensor(coordonator))

    async_add_entities(entitati)


class DigiNecesitaReautentificareBinarySensor(EntitateUtilitatiRomania, BinarySensorEntity):
    _attr_name = "Necesită reautentificare"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordonator: CoordonatorUtilitatiRomania) -> None:
        super().__init__(coordonator)
        self._attr_unique_id = f"{coordonator.intrare.entry_id}_digi_necesita_reautentificare"
        self._attr_suggested_object_id = "digi_necesita_reautentificare"

    @property
    def is_on(self) -> bool:
        return bool((self.coordinator.data.extra or {}).get("needs_reauth")) if self.coordinator.data else False


class DigiAreRestanteBinarySensor(EntitateUtilitatiRomania, BinarySensorEntity):
    _attr_name = "Are restanțe Digi"

    def __init__(self, coordonator: CoordonatorUtilitatiRomania) -> None:
        super().__init__(coordonator)
        self._attr_unique_id = f"{coordonator.intrare.entry_id}_digi_are_restante"
        self._attr_suggested_object_id = "digi_are_restante"

    @property
    def is_on(self) -> bool:
        if not self.coordinator.data:
            return False
        for consum in self.coordinator.data.consumuri:
            if consum.cheie == "factura_restanta" and consum.id_cont and str(consum.valoare).strip().lower() == "da":
                return True
        return False
