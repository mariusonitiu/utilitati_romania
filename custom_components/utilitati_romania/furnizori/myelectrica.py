from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

import aiohttp

from ..const import CONF_PUNCTE_CONSUM_SELECTATE
from ..exceptions import EroareAutentificare, EroareConectare, EroareParsare
from ..modele import ConsumUtilitate, ContUtilitate, FacturaUtilitate, InstantaneuFurnizor
from .baza import ClientFurnizor

_LOGGER = logging.getLogger(__name__)

URL_BAZA = "https://api.myelectrica.ro/api"
URL_LOGIN = f"{URL_BAZA}/login"
URL_HIERARCHY = f"{URL_BAZA}/account-data-hierarchy"
URL_CLIENT_DATA = f"{URL_BAZA}/client-data/{{client_code}}"
URL_CONTRACT_NLC = f"{URL_BAZA}/contract-nlc-details/{{nlc}}"
URL_INVOICES = f"{URL_BAZA}/client-code-invoices/{{client_code}}/{{start_date}}/{{end_date}}/{{unpaid}}"
URL_PAYMENTS = f"{URL_BAZA}/client-code-payments/{{client_code}}/{{start_date}}/{{end_date}}"
URL_METER_LIST = f"{URL_BAZA}/meter-list/{{nlc}}"
URL_READINGS = f"{URL_BAZA}/readings/{{client_code}}/{{nlc}}"
URL_CONVENTION = f"{URL_BAZA}/consumtion-convention/{{nlc}}"
URL_SET_INDEX = f"{URL_BAZA}/set-index"
HEADERS_BAZA = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/146.0.0.0 Safari/537.36"
    ),
}


class EroareApiMyElectrica(Exception):
    pass


class ClientApiMyElectrica:
    def __init__(self, sesiune: aiohttp.ClientSession, email: str, parola: str) -> None:
        self._sesiune = sesiune
        self._email = email
        self._parola = parola
        self._token: str | None = None

    async def async_login(self) -> bool:
        try:
            async with self._sesiune.post(
                URL_LOGIN,
                headers=HEADERS_BAZA,
                json={"email": self._email, "parola": self._parola},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as raspuns:
                if raspuns.status != 200:
                    self._token = None
                    return False
                data = await raspuns.json()
        except aiohttp.ClientError as err:
            raise EroareConectare(f"Eroare de conectare la myElectrica: {err}") from err
        except TimeoutError as err:
            raise EroareConectare("Timeout la autentificarea myElectrica") from err

        if data.get("error") is False and data.get("app_token"):
            self._token = str(data["app_token"])
            return True
        self._token = None
        return False

    async def _get(self, url: str) -> dict | list | None:
        if not self._token and not await self.async_login():
            raise EroareAutentificare("Autentificare myElectrica eșuată")
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self._token}",
            "user-agent": HEADERS_BAZA["User-Agent"],
        }
        try:
            async with self._sesiune.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as raspuns:
                if raspuns.status == 401:
                    self._token = None
                    if not await self.async_login():
                        raise EroareAutentificare("Sesiune myElectrica expirată")
                    headers["authorization"] = f"Bearer {self._token}"
                    async with self._sesiune.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as retry:
                        if retry.status >= 400:
                            raise EroareApiMyElectrica(f"HTTP {retry.status} pentru {url}")
                        return await retry.json()
                if raspuns.status >= 400:
                    raise EroareApiMyElectrica(f"HTTP {raspuns.status} pentru {url}")
                return await raspuns.json()
        except EroareApiMyElectrica:
            raise
        except aiohttp.ClientError as err:
            raise EroareConectare(f"Eroare de conectare myElectrica: {err}") from err
        except TimeoutError as err:
            raise EroareConectare(f"Timeout myElectrica pentru {url}") from err

    async def _post(self, url: str, payload: dict[str, Any]) -> dict | None:
        if not self._token and not await self.async_login():
            raise EroareAutentificare("Autentificare myElectrica eșuată")
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self._token}",
            "user-agent": HEADERS_BAZA["User-Agent"],
        }
        try:
            async with self._sesiune.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as raspuns:
                if raspuns.status == 401:
                    self._token = None
                    if not await self.async_login():
                        raise EroareAutentificare("Sesiune myElectrica expirată")
                    headers["authorization"] = f"Bearer {self._token}"
                    async with self._sesiune.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as retry:
                        return await retry.json()
                return await raspuns.json()
        except aiohttp.ClientError as err:
            raise EroareConectare(f"Eroare de conectare myElectrica: {err}") from err
        except TimeoutError as err:
            raise EroareConectare(f"Timeout myElectrica pentru {url}") from err

    async def async_get_hierarchy(self) -> dict | None:
        data = await self._get(URL_HIERARCHY)
        return data if isinstance(data, dict) else None

    async def async_get_client_data(self, client_code: str) -> dict | list | None:
        return await self._get(URL_CLIENT_DATA.format(client_code=client_code))

    async def async_get_contract_nlc(self, nlc: str) -> dict | list | None:
        return await self._get(URL_CONTRACT_NLC.format(nlc=nlc))

    async def async_get_invoices(self, client_code: str, unpaid: bool = False) -> dict | list | None:
        now = datetime.now(tz=UTC)
        start_date = (now - timedelta(days=730)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        return await self._get(URL_INVOICES.format(client_code=client_code, start_date=start_date, end_date=end_date, unpaid=str(unpaid).lower()))

    async def async_get_payments(self, client_code: str) -> dict | list | None:
        now = datetime.now(tz=UTC)
        start_date = (now - timedelta(days=730)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        return await self._get(URL_PAYMENTS.format(client_code=client_code, start_date=start_date, end_date=end_date))

    async def async_get_meter_list(self, nlc: str) -> dict | list | None:
        return await self._get(URL_METER_LIST.format(nlc=nlc))

    async def async_get_readings(self, client_code: str, nlc: str) -> dict | list | None:
        return await self._get(URL_READINGS.format(client_code=client_code, nlc=nlc))

    async def async_get_convention(self, nlc: str) -> dict | list | None:
        return await self._get(URL_CONVENTION.format(nlc=nlc))

    async def async_set_index(self, nlc: str, serie_contor: str, register_code: str, index_value: str | int | float) -> dict | None:
        payload = {
            "NLC": nlc,
            "to_Contor": [{"SerieContor": serie_contor, "to_Cadran": [{"RegisterCode": register_code, "Index": str(index_value)}]}],
        }
        data = await self._post(URL_SET_INDEX, payload)
        return data if isinstance(data, dict) else None


def _body_response(raw: Any) -> Any:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        body = raw.get("body")
        if isinstance(body, dict) and "response" in body:
            return body.get("response")
        return raw.get("details") if "details" in raw else raw
    return None


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "None"):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_date(value: Any) -> date | None:
    if value in (None, "", "None"):
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _normalize_service(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"electricitate", "energie electrică", "energie electrica"}:
        return "curent"
    if text in {"gaz", "gaze naturale"}:
        return "gaz"
    return text or "energie"


def _build_address(loc: dict[str, Any]) -> str:
    parts: list[str] = []
    street = str(loc.get("Street") or "").strip().title()
    nr = str(loc.get("HouseNumber") or "").strip()
    if street and nr:
        parts.append(f"{street} {nr}")
    elif street:
        parts.append(street)
    for src, label in (("Building", "bl."), ("Entrance", "sc."), ("Floor", "et."), ("RoomNumber", "ap.")):
        val = str(loc.get(src) or "").strip()
        if val:
            parts.append(f"{label} {val}")
    postcode = str(loc.get("PostCode") or "").strip()
    city = str(loc.get("City") or "").strip().title()
    if postcode and city:
        parts.append(f"{postcode} {city}")
    elif city:
        parts.append(city)
    return ", ".join(parts) if parts else "Adresă necunoscută"


def _extract_selected_structure(hierarchy: list[dict[str, Any]], selected_nlcs: list[str] | None) -> tuple[dict[str, str], dict[str, str], list[str], list[dict[str, Any]]]:
    nlc_to_client: dict[str, str] = {}
    nlc_to_contract: dict[str, str] = {}
    client_codes: list[str] = []
    locations: list[dict[str, Any]] = []
    for client in hierarchy:
        client_code = str(client.get("ClientCode") or "")
        client_name = str(client.get("ClientName") or "")
        for contract in client.get("to_ContContract", []) or []:
            contract_account = str(contract.get("ContractAccount") or "")
            for loc in contract.get("to_LocConsum", []) or []:
                nlc = str(loc.get("IdLocConsum") or "")
                if not nlc:
                    continue
                if selected_nlcs and nlc not in selected_nlcs:
                    continue
                nlc_to_client[nlc] = client_code
                nlc_to_contract[nlc] = contract_account
                if client_code and client_code not in client_codes:
                    client_codes.append(client_code)
                locations.append({
                    "nlc": nlc,
                    "client_code": client_code,
                    "client_name": client_name,
                    "contract_account": contract_account,
                    "loc": loc,
                })
    return nlc_to_client, nlc_to_contract, client_codes, locations


def _invoice_amount(invoice: dict[str, Any]) -> float:
    return round(
        _safe_float(
            invoice.get("TotalAmount")
            or invoice.get("InvoiceAmount")
            or invoice.get("AmountDue")
            or invoice.get("Amount")
            or invoice.get("PaidValue")
        ),
        2,
    )


def _invoice_unpaid(invoice: dict[str, Any]) -> float:
    unpaid = invoice.get("UnpaidValue")
    if unpaid not in (None, "", "None"):
        return round(_safe_float(unpaid), 2)

    status = str(
        invoice.get("InvoiceStatus")
        or invoice.get("Status")
        or ""
    ).strip().lower()
    if status in {"achitat", "platita", "plătită", "paid"}:
        return 0.0
    return _invoice_amount(invoice)


def _payment_amount(payment: dict[str, Any]) -> float:
    return round(
        _safe_float(
            payment.get("PaidValue")
            or payment.get("PaymentAmount")
            or payment.get("Amount")
            or payment.get("Value")
        ),
        2,
    )


def _invoice_matches_location(invoice: dict[str, Any], contract_account: str, nlc: str) -> bool:
    invoice_contract = str(invoice.get("ContractAccount") or invoice.get("ContractAcccount") or "").strip()
    invoice_nlc = str(invoice.get("nlcField") or invoice.get("NLC") or invoice.get("Nlc") or "").strip()
    if contract_account and invoice_contract and invoice_contract == contract_account:
        return True
    if nlc and invoice_nlc and invoice_nlc == nlc:
        return True
    return False


def _filter_invoices_for_location(
    invoices: list[dict[str, Any]],
    contract_account: str,
    nlc: str,
) -> list[dict[str, Any]]:
    filtrate = [inv for inv in invoices if _invoice_matches_location(inv, contract_account, nlc)]
    if filtrate:
        return filtrate
    if contract_account:
        contract_only = [
            inv for inv in invoices
            if str(inv.get("ContractAccount") or inv.get("ContractAcccount") or "").strip() == contract_account
        ]
        if contract_only:
            return contract_only
    if nlc:
        nlc_only = [
            inv for inv in invoices
            if str(inv.get("nlcField") or inv.get("NLC") or inv.get("Nlc") or "").strip() == nlc
        ]
        if nlc_only:
            return nlc_only
    return invoices


def _filter_payments_for_location(
    payments: list[dict[str, Any]],
    invoice_list: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not payments:
        return []

    invoice_ids: set[str] = set()
    fiscal_numbers: set[str] = set()
    for invoice in invoice_list:
        for key in ("InvoiceId", "InvoiceID", "InvoiceNumber", "DocumentNumber"):
            value = str(invoice.get(key) or "").strip()
            if value:
                invoice_ids.add(value)
        fiscal = str(invoice.get("FiscalNumber") or "").strip()
        if fiscal:
            fiscal_numbers.add(fiscal)

    filtrate: list[dict[str, Any]] = []
    for payment in payments:
        valori = {
            str(payment.get("InvoiceId") or "").strip(),
            str(payment.get("InvoiceID") or "").strip(),
            str(payment.get("InvoiceNumber") or "").strip(),
            str(payment.get("DocumentNumber") or "").strip(),
            str(payment.get("FiscalNumber") or "").strip(),
            str(payment.get("DocumentNo") or "").strip(),
        }
        valori.discard("")
        if (invoice_ids and valori.intersection(invoice_ids)) or (fiscal_numbers and valori.intersection(fiscal_numbers)):
            filtrate.append(payment)

    return filtrate if filtrate else payments


class ClientFurnizorMyElectrica(ClientFurnizor):
    cheie_furnizor = "myelectrica"
    nume_prietenos = "myElectrica"

    def __init__(self, *, sesiune, utilizator: str, parola: str, optiuni: dict) -> None:
        super().__init__(sesiune=sesiune, utilizator=utilizator, parola=parola, optiuni=optiuni)
        self.api = ClientApiMyElectrica(sesiune=sesiune, email=utilizator, parola=parola)

    async def async_testeaza_conexiunea(self) -> str:
        try:
            ok = await self.api.async_login()
            if not ok:
                raise EroareAutentificare("Autentificare myElectrica eșuată")
            hierarchy_raw = await self.api.async_get_hierarchy()
        except EroareConectare:
            raise
        except EroareAutentificare:
            raise
        except Exception as err:
            raise EroareParsare(str(err)) from err
        hierarchy = []
        if isinstance(hierarchy_raw, dict):
            hierarchy = hierarchy_raw.get("details") or []
        if not hierarchy:
            return self.utilizator.lower()
        _, _, _, locations = _extract_selected_structure(hierarchy, self.optiuni.get(CONF_PUNCTE_CONSUM_SELECTATE))
        if locations:
            return str(locations[0]["nlc"])
        return self.utilizator.lower()

    async def async_obtine_instantaneu(self) -> InstantaneuFurnizor:
        try:
            hierarchy_raw = await self.api.async_get_hierarchy()
        except EroareAutentificare as err:
            raise
        except EroareConectare as err:
            raise
        except Exception as err:
            raise EroareParsare(str(err)) from err
        hierarchy = []
        if isinstance(hierarchy_raw, dict):
            hierarchy = hierarchy_raw.get("details") or []
        if not hierarchy:
            raise EroareParsare("myElectrica nu a returnat ierarhia contului")

        selected_nlcs = self.optiuni.get(CONF_PUNCTE_CONSUM_SELECTATE) or None
        nlc_to_client, nlc_to_contract, client_codes, locations = _extract_selected_structure(hierarchy, selected_nlcs)
        if not locations:
            raise EroareParsare("Nu există puncte de consum myElectrica selectate")

        client_data: dict[str, Any] = {}
        invoices: dict[str, list[dict[str, Any]]] = {}
        payments: dict[str, list[dict[str, Any]]] = {}
        for client_code in client_codes:
            client_data[client_code] = _body_response(await self.api.async_get_client_data(client_code)) or {}
            invoices[client_code] = _body_response(await self.api.async_get_invoices(client_code)) or []
            payments[client_code] = _body_response(await self.api.async_get_payments(client_code)) or []

        contract_details: dict[str, Any] = {}
        meter_list: dict[str, Any] = {}
        readings: dict[str, list[dict[str, Any]]] = {}
        convention: dict[str, list[dict[str, Any]]] = {}
        for item in locations:
            nlc = item["nlc"]
            cc = item["client_code"]
            contract_details[nlc] = _body_response(await self.api.async_get_contract_nlc(nlc)) or {}
            meter_list[nlc] = _body_response(await self.api.async_get_meter_list(nlc)) or {}
            readings[nlc] = _body_response(await self.api.async_get_readings(cc, nlc)) or []
            convention[nlc] = _body_response(await self.api.async_get_convention(nlc)) or []

        conturi: list[ContUtilitate] = []
        facturi_model: list[FacturaUtilitate] = []
        consumuri: list[ConsumUtilitate] = []
        total_due = 0.0

        for item in locations:
            nlc = item["nlc"]
            client_code = item["client_code"]
            contract_account = item["contract_account"]
            loc = item["loc"]
            service_type = str(loc.get("ServiceType") or "")
            tip_serviciu = _normalize_service(service_type)
            tip_utilitate = "energie electrică" if tip_serviciu == "curent" else "gaz" if tip_serviciu == "gaz" else service_type or "energie"
            address = _build_address(loc)
            contract = contract_details.get(nlc) or {}
            meter = meter_list.get(nlc) or {}
            read_list = readings.get(nlc) or []
            conv_list = convention.get(nlc) or []
            client_info = client_data.get(client_code) or {}
            all_invoices = [x for x in (invoices.get(client_code) or []) if isinstance(x, dict)]
            invoice_list = _filter_invoices_for_location(all_invoices, contract_account, nlc)
            all_payments = [x for x in (payments.get(client_code) or []) if isinstance(x, dict)]
            payment_list = _filter_payments_for_location(all_payments, invoice_list)

            contract_status = str(contract.get("ContractStatus") or loc.get("ContractStatus") or "activ").strip().lower()
            client_name = str(client_info.get("ClientName") or item.get("client_name") or f"NLC {nlc}").strip().title()
            pac_indicator = str(meter.get("PACIndicator") or contract.get("PACIndicator") or "0")
            permitted = "da" if pac_indicator in {"1", "true", "True"} else "nu"

            contoare = meter.get("to_Contor") or []
            contor = contoare[0] if contoare else {}
            cadrane = contor.get("to_Cadran") or []
            cadran = cadrane[0] if cadrane else {}
            index_curent = cadran.get("Index")
            register_code = cadran.get("RegisterCode")
            serie_contor = contor.get("SerieContor")

            latest_invoice = None
            if invoice_list:
                latest_invoice = sorted(invoice_list, key=lambda x: _parse_date(x.get("IssueDate")) or date.min, reverse=True)[0]
            due_total = round(sum(_invoice_unpaid(x) for x in invoice_list), 2)
            total_due += due_total

            if latest_invoice:
                consumuri.append(ConsumUtilitate("id_ultima_factura", str(latest_invoice.get("InvoiceNumber") or latest_invoice.get("DocumentNumber") or latest_invoice.get("InvoiceID") or latest_invoice.get("InvoiceId") or ""), None, id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu))
                consumuri.append(ConsumUtilitate("valoare_ultima_factura", _invoice_amount(latest_invoice), "RON", id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu))
                if latest_invoice.get("DueDate"):
                    consumuri.append(ConsumUtilitate("urmatoarea_scadenta", str(latest_invoice.get("DueDate")), None, id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu))

            if payment_list:
                latest_payment = sorted(payment_list, key=lambda x: _parse_date(x.get("PaymentDate")) or date.min, reverse=True)[0]
                consumuri.append(ConsumUtilitate("valoare_ultima_plata", _payment_amount(latest_payment), "RON", id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu))
                if latest_payment.get("PaymentDate"):
                    consumuri.append(ConsumUtilitate("data_ultima_plata", str(latest_payment.get("PaymentDate")), None, id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu))

            if index_curent not in (None, ""):
                try:
                    index_val = float(index_curent)
                except (TypeError, ValueError):
                    index_val = None
                if index_val is not None:
                    consumuri.append(ConsumUtilitate("index_contor", round(index_val, 3), "kWh" if tip_serviciu == "curent" else "m³", id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu, date_brute={"register_code": register_code, "serie_contor": serie_contor}))

            consumuri.extend([
                ConsumUtilitate("citire_permisa", permitted, None, id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu, date_brute={"start": meter.get("StartDatePAC"), "end": meter.get("EndDatePAC")}),
                ConsumUtilitate("conventie_consum", "da" if sum(_safe_float(x.get("Quantity")) for x in conv_list if isinstance(x, dict)) > 0 else "nu", None, id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu, date_brute={"convention": conv_list}),
                ConsumUtilitate("istoric_citiri", len(read_list), None, id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu, date_brute={"readings": read_list}),
                ConsumUtilitate("numar_facturi", len(invoice_list), None, id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu, date_brute={"invoices": invoice_list}),
                ConsumUtilitate("factura_restanta", "da" if due_total > 0 else "nu", None, id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu),
                ConsumUtilitate("sold_curent", due_total, "RON", id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu),
                ConsumUtilitate("numar_plati", len(payment_list), None, id_cont=nlc, tip_utilitate=tip_utilitate, tip_serviciu=tip_serviciu, date_brute={"payments": payment_list}),
            ])

            conturi.append(ContUtilitate(
                id_cont=nlc,
                nume=client_name,
                tip_cont="loc_consum",
                id_contract=contract_account,
                adresa=address,
                stare=contract_status,
                tip_utilitate=tip_utilitate,
                tip_serviciu=tip_serviciu,
                date_brute={
                    "nlc": nlc,
                    "client_code": client_code,
                    "client_name": item.get("client_name"),
                    "contract_account": contract_account,
                    "loc": loc,
                    "client_data": client_info,
                    "contract_details": contract,
                    "meter_list": meter,
                    "readings": read_list,
                    "convention": conv_list,
                    "invoices": invoice_list,
                    "payments": payment_list,
                    "serie_contor": serie_contor,
                    "register_code": register_code,
                },
            ))

            for idx, factura in enumerate(invoice_list, start=1):
                id_factura = str(factura.get("InvoiceNumber") or factura.get("DocumentNumber") or factura.get("InvoiceId") or f"{client_code}-{idx}")
                facturi_model.append(FacturaUtilitate(
                    id_factura=id_factura,
                    titlu=f"Factură {id_factura}",
                    valoare=_invoice_amount(factura),
                    moneda="RON",
                    data_emitere=_parse_date(factura.get("IssueDate")),
                    data_scadenta=_parse_date(factura.get("DueDate")),
                    stare=str(factura.get("Status") or "").strip().lower() or None,
                    categorie="factura",
                    id_cont=nlc,
                    id_contract=contract_account,
                    tip_utilitate=tip_utilitate,
                    tip_serviciu=tip_serviciu,
                    date_brute=factura,
                ))

        consumuri.append(ConsumUtilitate("sold_curent", round(total_due, 2), "RON", tip_utilitate="energie"))
        consumuri.append(ConsumUtilitate("de_plata", round(max(total_due, 0.0), 2), "RON", tip_utilitate="energie"))

        titlu = self.nume_prietenos
        if len(conturi) == 1:
            titlu = f"{self.nume_prietenos} – {conturi[0].adresa or conturi[0].id_cont}"

        return InstantaneuFurnizor(
            furnizor=self.cheie_furnizor,
            titlu=titlu,
            conturi=conturi,
            facturi=facturi_model,
            consumuri=consumuri,
            extra={
                "hierarchy": hierarchy,
                "nlc_to_client": nlc_to_client,
                "nlc_to_contract": nlc_to_contract,
                "client_data": client_data,
                "contract_details": contract_details,
                "meter_list": meter_list,
                "readings": readings,
                "convention": convention,
                "payments": payments,
                "selected_nlcs": selected_nlcs or [c.id_cont for c in conturi],
            },
        )
