from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class InvoiceSummary:
    invoice_id: str
    address_key: str
    address: str
    issue_date: str
    due_date: str
    description: str
    amount: float


@dataclass(slots=True)
class InvoiceDetail:
    invoice_id: str
    invoice_number: str | None
    issue_date: str | None
    due_date: str | None
    total: float | None
    rest: float | None
    status: str | None
    pdf_url: str | None
    services: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class AddressInvoices:
    address_key: str
    address: str
    latest: dict[str, Any]
    history: list[dict[str, Any]]
    unpaid_count: int


@dataclass(slots=True)
class DigiData:
    account_label: str | None
    account_id: str | None
    invoices_by_address: dict[str, AddressInvoices]
    last_update: datetime
    needs_reauth: bool = False
