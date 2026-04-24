from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components import persistent_notification

from .coordonator import CoordonatorUtilitatiRomania
from .entitate import EntitateUtilitatiRomania
from .const import DOMENIU, CONF_FURNIZOR, FURNIZOR_ADMIN_GLOBAL, SERVICIU_RELOAD_ALL
from .licentiere import async_obtine_context_licenta, async_salveaza_licenta_globala, async_valideaza_licenta
from .hidro_device import alias_loc_consum, info_device_hidro, slug_loc_consum
from .eon_device import alias_loc_eon, info_device_eon, slug_loc_eon
from .furnizori.hidroelectrica_helper import build_usage_entity, safe_get
from .myelectrica_device import alias_loc_myelectrica, info_device_myelectrica, slug_loc_myelectrica

from .storage_citiri import async_salveaza_citire

_LOGGER = logging.getLogger(__name__)


def _cont_curent_dupa_id(coordonator: CoordonatorUtilitatiRomania, id_cont: str | None):
    data = getattr(coordonator, "data", None)
    conturi = getattr(data, "conturi", None) or []
    for cont in conturi:
        if getattr(cont, "id_cont", None) == id_cont:
            return cont
    return None


def _admin_license_text_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    registry = er.async_get(hass)
    unique_id = f"{entry.entry_id}_admin_cod_licenta_noua"
    return registry.async_get_entity_id("text", DOMENIU, unique_id)


def _admin_device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMENIU, entry.entry_id)},
        name="Administrare integrare",
        manufacturer="onitium",
        model="Utilitati Romania",
        entry_type=None,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    if entry.data.get(CONF_FURNIZOR) == FURNIZOR_ADMIN_GLOBAL:
        async_add_entities([ButonReloadToateSubintegrarile(entry), ButonAplicaLicenta(entry)])
        return

    coordonator: CoordonatorUtilitatiRomania = hass.data[DOMENIU][entry.entry_id]
    entitati: list[ButtonEntity] = [ButonActualizareAcum(coordonator)]
    if coordonator.data and coordonator.data.furnizor == "hidroelectrica":
        for cont in coordonator.data.conturi:
            entitati.append(ButonTrimiteIndexHidro(coordonator, cont))
    elif coordonator.data and coordonator.data.furnizor == "eon":
        for cont in coordonator.data.conturi:
            entitati.append(ButonTrimiteIndexEon(coordonator, cont))
    elif coordonator.data and coordonator.data.furnizor == "myelectrica":
        for cont in coordonator.data.conturi:
            raw = getattr(cont, "date_brute", None) or {}
            meter = raw.get("meter_list") or {}
            contoare = meter.get("to_Contor", []) or []
            are_contor = bool(contoare and (contoare[0].get("SerieContor") or ((contoare[0].get("to_Cadran") or [{}])[0].get("RegisterCode"))))
            if are_contor:
                entitati.append(ButonTrimiteIndexMyElectrica(coordonator, cont))
    async_add_entities(entitati)


class ButonReloadToateSubintegrarile(ButtonEntity):
    _attr_icon = "mdi:reload-alert"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_admin_reload_all"
        self._attr_name = "Reload all subs"
        self._attr_device_info = _admin_device_info(entry)
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        await self.hass.services.async_call(DOMENIU, SERVICIU_RELOAD_ALL, {}, blocking=True)


class ButonAplicaLicenta(ButtonEntity):
    _attr_icon = "mdi:key-chain-variant"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_admin_aplica_licenta"
        self._attr_name = "Aplică licență"
        self._attr_device_info = _admin_device_info(entry)
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_press(self) -> None:
        text_entity_id = _admin_license_text_entity_id(self.hass, self._entry)
        if not text_entity_id:
            raise HomeAssistantError("Nu am găsit câmpul text pentru introducerea licenței.")

        stare = self.hass.states.get(text_entity_id)
        cod = str(stare.state).strip() if stare else ""
        if not cod:
            raise HomeAssistantError("Introdu mai întâi un cod de licență nou.")

        utilizator, _cheie_curenta, _storage = await async_obtine_context_licenta(self.hass, intrare=self._entry)
        if not utilizator:
            raise HomeAssistantError("Nu există încă un cont de licență asociat. Configurează mai întâi cel puțin un furnizor.")

        notif_id = "utilitati_romania_aplica_licenta"
        rezultat = await async_valideaza_licenta(self.hass, cod, utilizator)

        if not rezultat.valida:
            mesaj = rezultat.mesaj or "Codul de licență nu a putut fi validat."
            persistent_notification.async_create(
                self.hass,
                f"Aplicarea licenței a eșuat.\n\nMotiv: **{mesaj}**",
                title="Utilități România – Licență",
                notification_id=notif_id,
            )
            raise HomeAssistantError(mesaj)

        await async_salveaza_licenta_globala(self.hass, cod, utilizator, rezultat)

        await self.hass.services.async_call(
            "text",
            "set_value",
            {"entity_id": text_entity_id, "value": cod},
            blocking=True,
        )

        await self.hass.services.async_call(
            DOMENIU,
            SERVICIU_RELOAD_ALL,
            {},
            blocking=True,
        )

        await self.hass.services.async_call(
            "homeassistant",
            "update_entity",
            {
                "entity_id": [
                    f"sensor.{DOMENIU}_status_licenta",
                    f"sensor.{DOMENIU}_plan_licenta",
                    f"sensor.{DOMENIU}_valabila_pana_la",
                    f"sensor.{DOMENIU}_ultima_verificare_licenta",
                    f"sensor.{DOMENIU}_cont_licenta",
                    f"sensor.{DOMENIU}_cod_licenta_mascat",
                    f"sensor.{DOMENIU}_mesaj_licenta",
                ]
            },
            blocking=False,
        )

        persistent_notification.async_create(
            self.hass,
            (
                "Licența a fost actualizată cu succes.\n\n"
                f"- Utilizator: **{utilizator}**\n"
                f"- Plan: **{rezultat.plan or '-'}**\n"
                f"- Expiră la: **{rezultat.expira_la or '-'}**"
            ),
            title="Utilități România – Licență",
            notification_id=notif_id,
        )


class ButonActualizareAcum(EntitateUtilitatiRomania, ButtonEntity):
    def __init__(self, coordonator: CoordonatorUtilitatiRomania) -> None:
        super().__init__(coordonator)
        self._attr_unique_id = f"{coordonator.intrare.entry_id}_actualizare_acum"
        self._attr_name = "Actualizează acum"
        self._attr_icon = "mdi:refresh"
    
    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()


class ButonTrimiteIndexHidro(EntitateUtilitatiRomania, ButtonEntity):
    def __init__(self, coordonator: CoordonatorUtilitatiRomania, cont) -> None:
        super().__init__(coordonator)
        self.cont = cont
        alias = alias_loc_consum(cont.nume, cont.adresa, cont.id_cont)
        slug = slug_loc_consum(cont.id_cont, alias, cont.adresa)
        self._attr_unique_id = f"{coordonator.intrare.entry_id}_hidro_{cont.id_cont}_trimite_index"
        self._attr_name = f"Trimite index energie electrică {alias}"
        self._attr_icon = "mdi:send-circle"
        self._attr_device_info = info_device_hidro(coordonator.intrare.entry_id, cont)
        self._attr_suggested_object_id = f"hidro_{cont.id_cont}_{slug}_trimite_index"
        self.entity_id = f"button.hidro_{cont.id_cont}_{slug}_trimite_index"
        self._entity_numar = f"number.hidro_{cont.id_cont}_{slug}_index_energie_electrica"

    @property
    def _cont_actual(self):
        return _cont_curent_dupa_id(self.coordinator, getattr(self.cont, "id_cont", None)) or self.cont

    @property
    def available(self) -> bool:
        return _cont_curent_dupa_id(self.coordinator, getattr(self.cont, "id_cont", None)) is not None

    async def async_press(self) -> None:
        numar = self.hass.states.get(self._entity_numar)
        if not numar:
            raise ValueError(f"Nu există entitatea {self._entity_numar}")
        index_value = str(int(float(numar.state)))

        meta = self._cont_actual.date_brute or {}
        previous_payload = meta.get("previous_meter_read") or {}
        prev_data = safe_get(previous_payload, "result", "Data", default=[])
        if not prev_data or not isinstance(prev_data, list):
            raise ValueError("Nu există date anterioare pentru transmiterea indexului.")
        now_str = datetime.now().strftime("%d/%m/%Y")
        usage_entities = [
            build_usage_entity(reading, index_value, now_str)
            for reading in prev_data
            if isinstance(reading, dict)
        ]
        api = self.coordinator.client.api
        user_id = api.user_id or ""
        pod = meta.get("pod") or ""
        instalare = meta.get("instalare") or ""
        account_number = meta.get("account_number") or ""
        await api.async_get_meter_value(
            user_id=user_id,
            pod_value=pod,
            installation_number=instalare,
            account_number=account_number,
            usage_entity=usage_entities,
        )
        await api.async_submit_self_meter_read(
            user_id=user_id,
            pod_value=pod,
            installation_number=instalare,
            account_number=account_number,
            usage_entity=usage_entities,
        )

        await async_salveaza_citire(
            self.hass,
            "hidroelectrica",
            self.cont.id_cont,
            float(index_value),
        )

        await async_salveaza_citire(
            self.hass,
            "hidroelectrica",
            self.cont.id_cont,
            float(index_value),
        )

        await self.coordinator.async_request_refresh()


class ButonTrimiteIndexEon(EntitateUtilitatiRomania, ButtonEntity):
    def __init__(self, coordonator: CoordonatorUtilitatiRomania, cont) -> None:
        super().__init__(coordonator)
        self.cont = cont
        alias = alias_loc_eon(cont.nume, cont.adresa, cont.id_cont)
        slug = slug_loc_eon(cont.id_cont, alias, cont.adresa)
        tip = cont.tip_serviciu or cont.tip_utilitate or "curent"

        self._alias = alias
        self._tip = tip

        self._attr_unique_id = f"{coordonator.intrare.entry_id}_eon_{slug}_trimite_index"
        self._attr_name = f"Trimite index {'gaz' if tip == 'gaz' else 'energie electrică'} {alias}"
        self._attr_icon = "mdi:send-circle"
        self._attr_device_info = info_device_eon(coordonator.intrare.entry_id, cont)

    async def async_press(self) -> None:
        tip_label = "gaz" if self._tip == "gaz" else "energie electrică"
        notif_id = f"utilitati_romania_eon_trimite_index_{self.cont.id_cont}"

        try:
            text_cautat = "index gaz" if self._tip == "gaz" else "index energie electrică"

            numar = next(
                (
                    state
                    for state in self.hass.states.async_all("number")
                    if text_cautat in str(state.attributes.get("friendly_name", "")).lower()
                    and self._alias.lower() in str(state.attributes.get("friendly_name", "")).lower()
                ),
                None,
            )

            if not numar:
                raise ValueError(
                    f"Nu am găsit entitatea number pentru indexul de {tip_label} aferentă locației „{self._alias}”."
                )

            try:
                index_value = int(float(numar.state))
            except (TypeError, ValueError):
                raise ValueError(
                    f"Valoarea indexului introdusă pentru „{self._alias}” nu este validă: {numar.state}"
                )

            meta = self.cont.date_brute or {}
            meter_index = meta.get("meter_index") or {}
            devices = ((meter_index.get("indexDetails") or {}).get("devices") or [])

            ablbelnr = None
            for dev in devices:
                for idx in (dev.get("indexes") or []):
                    ablbelnr = idx.get("ablbelnr")
                    if ablbelnr:
                        break
                if ablbelnr:
                    break

            if not ablbelnr:
                raise ValueError(
                    f"Nu s-a putut identifica ID-ul intern al contorului (ablbelnr) pentru „{self._alias}”."
                )

            indexes_payload = [
                {
                    "ablbelnr": ablbelnr,
                    "indexValue": index_value,
                }
            ]

            rezultat = await self.coordinator.client.api.async_submit_meter_index(
                self.cont.id_cont,
                indexes_payload,
            )

            if rezultat is None:
                raise ValueError(
                    f"Transmiterea indexului de {tip_label} pentru „{self._alias}” a eșuat. "
                    "API-ul E.ON nu a returnat un răspuns valid."
                )

            persistent_notification.async_create(
                self.hass,
                (
                    f"Indexul de **{tip_label}** pentru **{self._alias}** a fost trimis cu succes.\n\n"
                    f"- Contract: `{self.cont.id_cont}`\n"
                    f"- Valoare transmisă: **{index_value}**\n"
                    f"- ID contor intern: `{ablbelnr}`"
                ),
                title="Utilități România – E.ON",
                notification_id=notif_id,
            )

            await self.coordinator.async_request_refresh()

        except Exception as err:
            persistent_notification.async_create(
                self.hass,
                (
                    f"Transmiterea indexului de **{tip_label}** pentru **{self._alias}** a eșuat.\n\n"
                    f"Motiv: **{err}**\n\n"
                    f"- Contract: `{self.cont.id_cont}`"
                ),
                title="Utilități România – E.ON",
                notification_id=notif_id,
            )
            raise


class ButonTrimiteIndexMyElectrica(EntitateUtilitatiRomania, ButtonEntity):
    def __init__(self, coordonator: CoordonatorUtilitatiRomania, cont) -> None:
        super().__init__(coordonator)
        self.cont = cont
        alias = alias_loc_myelectrica(cont.nume, cont.adresa, cont.id_cont)
        slug = slug_loc_myelectrica(cont.id_cont, alias, cont.adresa)
        self._attr_unique_id = f"{coordonator.intrare.entry_id}_myelectrica_{slug}_trimite_index"
        self._attr_name = f"Trimite index {alias}"
        self._attr_icon = "mdi:send-circle"
        self._attr_device_info = info_device_myelectrica(coordonator.intrare.entry_id, cont)
        self._entity_numar = f"number.utilitati_romania_myelectrica_{slug}_index_contor"

    async def async_press(self) -> None:
        numar = self.hass.states.get(self._entity_numar)
        if not numar:
            raise ValueError(f"Nu există entitatea {self._entity_numar}")
        index_value = int(float(numar.state))
        raw = getattr(self.cont, "date_brute", None) or {}
        serie_contor = raw.get("serie_contor") or raw.get("meter_list", {}).get("to_Contor", [{}])[0].get("SerieContor")
        register_code = raw.get("register_code")
        if not register_code:
            contoare = raw.get("meter_list", {}).get("to_Contor", []) or []
            if contoare:
                cadrane = contoare[0].get("to_Cadran", []) or []
                if cadrane:
                    register_code = cadrane[0].get("RegisterCode")
        if not serie_contor or not register_code:
            raise ValueError("Nu s-au putut identifica seria contorului sau codul registrului pentru myElectrica.")
        rezultat = await self.coordinator.client.api.async_set_index(self.cont.id_cont, serie_contor, register_code, index_value)
        if not isinstance(rezultat, dict):
            raise ValueError("Transmiterea indexului myElectrica a eșuat.")
        errors = rezultat.get("errors") or []
        if errors:
            mesaj = "; ".join(str(item.get("errorMessage") or item) for item in errors)
            raise ValueError(mesaj)
        self.hass.components.persistent_notification.create(
            f"Indexul a fost transmis cu succes pentru {alias_loc_myelectrica(self.cont.nume, self.cont.adresa, self.cont.id_cont)}.",
            title="myElectrica",
        )
        await self.coordinator.async_request_refresh()
