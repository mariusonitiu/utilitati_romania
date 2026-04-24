from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMENIU
from .coordonator import CoordonatorUtilitatiRomania


class EntitateUtilitatiRomania(CoordinatorEntity[CoordonatorUtilitatiRomania]):
    _attr_has_entity_name = True

    def __init__(self, coordonator: CoordonatorUtilitatiRomania) -> None:
        super().__init__(coordonator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMENIU, coordonator.intrare.entry_id)},
            name=coordonator.intrare.title,
            manufacturer="onitium",
            model=coordonator.cheie_furnizor,
        )
