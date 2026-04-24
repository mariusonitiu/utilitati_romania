from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(slots=True)
class FacturaUtilitate:
    id_factura: str
    titlu: str
    valoare: float | None
    moneda: str | None
    data_emitere: date | None
    data_scadenta: date | None
    stare: str | None
    categorie: str | None = None
    id_cont: str | None = None
    id_contract: str | None = None
    tip_utilitate: str | None = None
    tip_serviciu: str | None = None
    este_prosumator: bool = False
    date_brute: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConsumUtilitate:
    cheie: str
    valoare: float | int | str | None
    unitate: str | None
    perioada: str | None = None
    id_cont: str | None = None
    tip_utilitate: str | None = None
    tip_serviciu: str | None = None
    date_brute: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ContUtilitate:
    id_cont: str
    nume: str
    tip_cont: str | None = None
    id_contract: str | None = None
    adresa: str | None = None
    stare: str | None = None
    tip_utilitate: str | None = None
    tip_serviciu: str | None = None
    este_prosumator: bool = False
    date_brute: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class InstantaneuFurnizor:
    furnizor: str
    titlu: str
    conturi: list[ContUtilitate]
    facturi: list[FacturaUtilitate]
    consumuri: list[ConsumUtilitate]
    extra: dict[str, Any] = field(default_factory=dict)
