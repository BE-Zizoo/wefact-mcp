"""WeFact MCP server (stdio).

All tool parameters use the exact WeFact field names (DebtorCode, InvoiceCode,
InvoiceLines, PriceExcl, ...). See https://developer.wefact.com/ for the field
reference; ``wefact_request`` covers any controller/action without its own tool.
"""

from __future__ import annotations

import functools
import os
from typing import Any

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .client import WeFactClient, WeFactError

load_dotenv()

mcp = FastMCP(
    "wefact",
    instructions=(
        "Tools for the WeFact invoicing API. Field names are identical to the WeFact "
        "docs. Invoice Status codes: 0 concept, 2 sent, 3 partly paid, 4 paid, "
        "8 credit invoice, 9 expired. Money values are strings in EUR unless the "
        "administration uses another currency. Before sending, crediting or deleting "
        "anything, summarise what will happen and ask the user to confirm."
    ),
)

_client: WeFactClient | None = None


def get_client() -> WeFactClient:
    global _client
    if _client is None:
        api_key = os.environ.get("WEFACT_API_KEY", "")
        if not api_key:
            raise WeFactError("WEFACT_API_KEY is not set. Put it in .env or the MCP server env.")
        _client = WeFactClient(
            api_key,
            base_url=os.environ.get("WEFACT_BASE_URL", "https://api.mijnwefact.nl/v2/"),
            timeout=float(os.environ.get("WEFACT_TIMEOUT", "30")),
        )
    return _client


def tool(fn):
    """Register with FastMCP and turn WeFactError into a structured error dict."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except WeFactError as exc:
            return exc.to_dict()

    return mcp.tool()(wrapper)


def _ident(**kwargs: Any) -> dict[str, Any]:
    """Keep only the identifiers that were actually given; require at least one."""
    given = {k: v for k, v in kwargs.items() if v not in (None, "")}
    if not given:
        raise WeFactError("Provide one of: " + ", ".join(kwargs))
    return given


def _range(name: str, start: str | None, end: str | None) -> dict[str, Any]:
    rng = {k: v for k, v in (("from", start), ("to", end)) if v}
    return {name: rng} if rng else {}


def _list(controller: str, params: dict[str, Any], *, all_pages: bool, limit: int, offset: int,
          result_key: str | None = None) -> dict[str, Any]:
    client = get_client()
    params = {k: v for k, v in params.items() if v not in (None, "")}
    if all_pages:
        return client.list_all(controller, params, result_key=result_key)
    return client.request(controller, "list", {**params, "limit": limit, "offset": offset})


# ---------------------------------------------------------------- debtors

@tool
def list_debtors(
    searchfor: str | None = None,
    searchat: str | None = None,
    group: int | None = None,
    modified_from: str | None = None,
    modified_to: str | None = None,
    sort: str | None = None,
    order: str | None = None,
    limit: int = 100,
    offset: int = 0,
    all_pages: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List debtors (customers).

    searchat: pipe-separated fields to search, default 'DebtorCode|CompanyName|SurName'
    (e.g. 'EmailAddress'). modified_*: 'YYYY-MM-DD HH:MM:SS'. all_pages=True walks every
    page (safe for 10.000+ debtors). extra: any other WeFact list parameter.
    """
    params = {"searchfor": searchfor, "searchat": searchat, "group": group, "sort": sort,
              "order": order, **_range("modified", modified_from, modified_to), **(extra or {})}
    return _list("debtor", params, all_pages=all_pages, limit=limit, offset=offset)


@tool
def get_debtor(DebtorCode: str | None = None, Identifier: int | None = None) -> dict[str, Any]:
    """Show one debtor by DebtorCode (e.g. DB10000) or internal Identifier."""
    return get_client().request("debtor", "show", _ident(DebtorCode=DebtorCode, Identifier=Identifier))


@tool
def create_debtor(fields: dict[str, Any]) -> dict[str, Any]:
    """Create a debtor. `fields` uses WeFact debtor field names: CompanyName or SurName
    (one required), Initials, Sex, Address, ZipCode, City, Country (ISO-2), EmailAddress,
    PhoneNumber, TaxNumber, CompanyNumber, InvoiceMethod, InvoiceTerm, Groups [ids],
    CustomFields {...}. Omit DebtorCode to let WeFact number it."""
    if not (fields.get("CompanyName") or fields.get("SurName")):
        raise WeFactError("CompanyName or SurName is required", controller="debtor", action="add")
    return get_client().request("debtor", "add", fields)


@tool
def update_debtor(
    fields: dict[str, Any], DebtorCode: str | None = None, Identifier: int | None = None
) -> dict[str, Any]:
    """Edit a debtor. Only the fields supplied are changed (same names as create_debtor)."""
    params = {**_ident(DebtorCode=DebtorCode, Identifier=Identifier), **fields}
    return get_client().request("debtor", "edit", params)


# --------------------------------------------------------------- invoices

@tool
def list_invoices(
    status: int | None = None,
    searchfor: str | None = None,
    searchat: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    paybefore_from: str | None = None,
    paybefore_to: str | None = None,
    paydate_from: str | None = None,
    paydate_to: str | None = None,
    modified_from: str | None = None,
    modified_to: str | None = None,
    sort: str | None = None,
    order: str | None = None,
    limit: int = 100,
    offset: int = 0,
    all_pages: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List invoices. status: 0 concept, 2 sent (unpaid), 3 partly paid, 4 paid,
    8 credit invoice, 9 expired. Dates 'YYYY-MM-DD'. Outstanding invoices older than
    N days = status 2 or 3 with paybefore_to = today - N days (check AmountOutstanding).
    Default sort InvoiceCode DESC. all_pages=True walks every page."""
    params = {
        "status": status, "searchfor": searchfor, "searchat": searchat, "sort": sort, "order": order,
        **_range("date", date_from, date_to),
        **_range("paybefore", paybefore_from, paybefore_to),
        **_range("paydate", paydate_from, paydate_to),
        **_range("modified", modified_from, modified_to),
        **(extra or {}),
    }
    return _list("invoice", params, all_pages=all_pages, limit=limit, offset=offset)


@tool
def get_invoice(InvoiceCode: str | None = None, Identifier: int | None = None) -> dict[str, Any]:
    """Show one invoice incl. InvoiceLines. InvoiceCode like 'F2026-0001' or '[concept]0001'."""
    return get_client().request("invoice", "show", _ident(InvoiceCode=InvoiceCode, Identifier=Identifier))


@tool
def create_invoice(
    DebtorCode: str,
    InvoiceLines: list[dict[str, Any]],
    fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a CONCEPT invoice (Status 0) — nothing is sent. Returns the invoice with its
    concept code. Each line: Description, PriceExcl (per unit, excl. VAT), Number (default 1),
    TaxCode (e.g. V21) or TaxPercentage, optional ProductCode (auto-fills description/price),
    DiscountPercentage, Periodic/Periods/StartDate. fields: other invoice params
    (Date, Term, ReferenceNumber, Description, Comment, VatCalcMethod, Discount, ...).
    Use send_invoice afterwards, after the user confirmed."""
    if not InvoiceLines:
        raise WeFactError("InvoiceLines must contain at least one line", controller="invoice", action="add")
    params = {"DebtorCode": DebtorCode, "InvoiceLines": InvoiceLines, **(fields or {})}
    return get_client().request("invoice", "add", params)


@tool
def send_invoice(
    InvoiceCode: str | None = None, Identifier: int | None = None, confirm: bool = False
) -> dict[str, Any]:
    """Send an invoice by e-mail (or Peppol per debtor setting). A concept gets its
    definitive InvoiceCode and Status 2. IRREVERSIBLE: ask the user first and pass
    confirm=True."""
    if not confirm:
        raise WeFactError("Refused: confirm=True is required after the user approved sending.",
                          controller="invoice", action="sendbyemail")
    return get_client().request("invoice", "sendbyemail", _ident(InvoiceCode=InvoiceCode, Identifier=Identifier))


@tool
def credit_invoice(
    InvoiceCode: str | None = None, Identifier: int | None = None, confirm: bool = False
) -> dict[str, Any]:
    """Create a credit invoice (Status 8, negated amounts) for a sent invoice and mark the
    original as credited. IRREVERSIBLE: ask the user first and pass confirm=True.
    (To remove a concept instead, use wefact_request invoice/delete.)"""
    if not confirm:
        raise WeFactError("Refused: confirm=True is required after the user approved crediting.",
                          controller="invoice", action="credit")
    return get_client().request("invoice", "credit", _ident(InvoiceCode=InvoiceCode, Identifier=Identifier))


@tool
def mark_invoice_paid(
    InvoiceCode: str | None = None,
    Identifier: int | None = None,
    PayDate: str | None = None,
    PaymentMethod: str | None = None,
) -> dict[str, Any]:
    """Mark a sent invoice as fully paid (Status 4). PayDate 'YYYY-MM-DD' (default today).
    PaymentMethod: wire (bank transfer, default), cash, card, auth (direct debit), paypal,
    ideal, accounting, various, other. Undo via wefact_request invoice/markasunpaid."""
    params = {**_ident(InvoiceCode=InvoiceCode, Identifier=Identifier)}
    if PayDate:
        params["PayDate"] = PayDate
    if PaymentMethod:
        params["PaymentMethod"] = PaymentMethod
    return get_client().request("invoice", "markaspaid", params)


# --------------------------------------------------------------- products

@tool
def list_products(
    searchfor: str | None = None,
    searchat: str | None = None,
    group: int | None = None,
    limit: int = 100,
    offset: int = 0,
    all_pages: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List products. searchat default 'ProductCode|ProductName|ProductKeyPhrase'."""
    params = {"searchfor": searchfor, "searchat": searchat, "group": group, **(extra or {})}
    return _list("product", params, all_pages=all_pages, limit=limit, offset=offset)


@tool
def get_product(ProductCode: str | None = None, Identifier: int | None = None) -> dict[str, Any]:
    """Show one product by ProductCode (e.g. P0001) or Identifier."""
    return get_client().request("product", "show", _ident(ProductCode=ProductCode, Identifier=Identifier))


# ---------------------------------------------------------- subscriptions

@tool
def list_subscriptions(
    status: str = "active",
    searchfor: str | None = None,
    searchat: str | None = None,
    sort: str | None = None,
    order: str | None = None,
    limit: int = 100,
    offset: int = 0,
    all_pages: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List subscriptions. status: 'active' (default) or 'terminated'. Default sort NextDate ASC.
    Items carry NextDate, TerminationDate, PriceExcl, Periodic (m/k/h/j), DebtorCode,
    ProductCode. To find subscriptions ending soon, list all_pages=True and filter on
    TerminationDate client-side (WeFact has no server-side filter for it)."""
    params = {"status": status, "searchfor": searchfor, "searchat": searchat, "sort": sort,
              "order": order, **(extra or {})}
    return _list("subscription", params, all_pages=all_pages, limit=limit, offset=offset)


@tool
def get_subscription(Identifier: int) -> dict[str, Any]:
    """Show one subscription by its Identifier (subscriptions have no code)."""
    return get_client().request("subscription", "show", {"Identifier": Identifier})


# -------------------------------------------- purchase (credit) invoices

@tool
def list_credit_invoices(
    status: int | None = None,
    searchfor: str | None = None,
    searchat: str | None = None,
    modified_from: str | None = None,
    modified_to: str | None = None,
    limit: int = 100,
    offset: int = 0,
    all_pages: bool = False,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List WeFact 'creditinvoice' records = PURCHASE invoices (inkoopfacturen from
    suppliers). status: 1 unpaid, 2 partly paid, 3 paid, 8 credit. NOTE: sales credit notes
    you issued to customers are ordinary invoices with Status 8 -> use list_invoices(status=8)."""
    params = {"status": status, "searchfor": searchfor, "searchat": searchat,
              **_range("modified", modified_from, modified_to), **(extra or {})}
    return _list("creditinvoice", params, all_pages=all_pages, limit=limit, offset=offset)


@tool
def get_credit_invoice(CreditInvoiceCode: str | None = None, Identifier: int | None = None) -> dict[str, Any]:
    """Show one purchase invoice by CreditInvoiceCode (e.g. CF0002) or Identifier."""
    return get_client().request(
        "creditinvoice", "show", _ident(CreditInvoiceCode=CreditInvoiceCode, Identifier=Identifier)
    )


# ------------------------------------------------------------ diagnostics

@tool
def whoami() -> dict[str, Any]:
    """Sanity-check the WeFact connection (API key + IP whitelist). Does one cheap
    debtor list call and returns endpoint, total number of debtors and the first DebtorCode."""
    client = get_client()
    data = client.request("debtor", "list", {"limit": 1})
    first = (data.get("debtors") or [{}])[0]
    return {
        "status": "success",
        "endpoint": client.base_url,
        "totalresults": data.get("totalresults"),
        "first_debtor_code": first.get("DebtorCode"),
    }


# ------------------------------------------------------------ escape hatch

@tool
def wefact_request(controller: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Generic call to any WeFact endpoint: controller + action + params exactly as in the
    WeFact docs (nested arrays as JSON lists/objects). Controllers: debtor, invoice,
    invoiceline, creditinvoice, creditor, product, subscription, pricequote, group,
    attachment, transaction, task, interaction, settings, extraclientcontact.
    Examples: invoice/markasunpaid, invoice/download, invoice/sendreminderbyemail,
    subscription/edit {Identifier, Subscription: {PriceExcl: 30}}, settings/list.
    Confirm with the user before delete/send/terminate actions."""
    return get_client().request(controller, action, params or {})


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
