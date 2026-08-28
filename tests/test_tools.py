import asyncio
import json

import pytest

from wefact_mcp import server
from tests.conftest import err, ok


# -- debtors ---------------------------------------------------------------

def test_list_debtors_maps_filters_and_pagination(wefact):
    wefact.queue(ok("debtor", "list", totalresults=1, currentresults=1, offset=0, debtors=[{"DebtorCode": "DB10000"}]))
    result = server.list_debtors(searchfor="info@example.com", searchat="EmailAddress",
                                 modified_from="2026-01-01 00:00:00", limit=50, offset=10)
    assert result["debtors"][0]["DebtorCode"] == "DB10000"
    r = wefact.last
    assert r["controller"] == "debtor" and r["action"] == "list"
    assert r["searchfor"] == "info@example.com" and r["searchat"] == "EmailAddress"
    assert r["modified[from]"] == "2026-01-01 00:00:00" and "modified[to]" not in r
    assert r["limit"] == "50" and r["offset"] == "10"


def test_list_debtors_all_pages_uses_client_pagination(wefact):
    wefact.queue(ok("debtor", "list", totalresults=2, currentresults=1, offset=0, debtors=[{"DebtorCode": "A"}]))
    wefact.queue(ok("debtor", "list", totalresults=2, currentresults=1, offset=1, debtors=[{"DebtorCode": "B"}]))
    # the fake serves one item per page; list_all must keep going until totalresults
    result = server.list_debtors(all_pages=True)
    assert [d["DebtorCode"] for d in result["debtors"]] == ["A", "B"]
    assert [r["offset"] for r in wefact.requests] == ["0", "1"]
    assert wefact.last["limit"] == "1000"


def test_get_debtor_requires_an_identifier(wefact):
    result = server.get_debtor()
    assert result["status"] == "error"
    assert "DebtorCode" in result["message"]
    assert wefact.requests == []


def test_create_debtor_passes_fields_1to1(wefact):
    wefact.queue(ok("debtor", "add", debtor={"DebtorCode": "DB10001"}))
    result = server.create_debtor({"CompanyName": "Acme BV", "Country": "BE", "Groups": [3],
                                   "CustomFields": {"klantnr": "77"}})
    assert result["debtor"]["DebtorCode"] == "DB10001"
    r = wefact.last
    assert r["action"] == "add" and r["CompanyName"] == "Acme BV"
    assert r["Groups[0]"] == "3" and r["CustomFields[klantnr]"] == "77"


def test_create_debtor_without_name_is_rejected_locally(wefact):
    result = server.create_debtor({"EmailAddress": "x@y.z"})
    assert result["status"] == "error" and wefact.requests == []


def test_update_debtor_sends_identifier_plus_changed_fields(wefact):
    wefact.queue(ok("debtor", "edit", debtor={"DebtorCode": "DB10000", "EmailAddress": "new@x.be"}))
    server.update_debtor({"EmailAddress": "new@x.be"}, DebtorCode="DB10000")
    assert wefact.last["action"] == "edit"
    assert wefact.last["DebtorCode"] == "DB10000" and wefact.last["EmailAddress"] == "new@x.be"


# -- invoices --------------------------------------------------------------

def test_list_invoices_status_and_date_ranges(wefact):
    wefact.queue(ok("invoice", "list", totalresults=0, currentresults=0, offset=0, invoices=[]))
    server.list_invoices(status=2, paybefore_to="2026-07-29", date_from="2026-01-01")
    r = wefact.last
    assert r["status"] == "2"
    assert r["paybefore[to]"] == "2026-07-29" and r["date[from]"] == "2026-01-01"
    assert "paybefore[from]" not in r and "status_from" not in r


def test_create_invoice_encodes_invoice_lines(wefact):
    wefact.queue(ok("invoice", "add", invoice={"InvoiceCode": "[concept]0001", "Status": 0}))
    result = server.create_invoice(
        "DB10000",
        [{"Description": "Maandelijkse hosting", "PriceExcl": 25, "TaxCode": "V21"}],
        fields={"ReferenceNumber": "PO-1"},
    )
    assert result["invoice"]["Status"] == 0
    r = wefact.last
    assert r["controller"] == "invoice" and r["action"] == "add"
    assert r["DebtorCode"] == "DB10000" and r["ReferenceNumber"] == "PO-1"
    assert r["InvoiceLines[0][Description]"] == "Maandelijkse hosting"
    assert r["InvoiceLines[0][PriceExcl]"] == "25"
    assert "Status" not in r  # stays a concept unless caller sets it


def test_create_invoice_without_lines_is_rejected(wefact):
    assert server.create_invoice("DB10000", [])["status"] == "error"
    assert wefact.requests == []


def test_send_invoice_refuses_without_confirm(wefact):
    result = server.send_invoice(InvoiceCode="[concept]0001")
    assert result["status"] == "error" and "confirm" in result["message"]
    assert wefact.requests == []


def test_send_invoice_with_confirm_calls_sendbyemail(wefact):
    wefact.queue(ok("invoice", "sendbyemail", success=["verzonden"], invoice={"InvoiceCode": "F2026-0001", "Status": 2}))
    result = server.send_invoice(InvoiceCode="[concept]0001", confirm=True)
    assert result["invoice"]["InvoiceCode"] == "F2026-0001"
    assert wefact.last["action"] == "sendbyemail" and wefact.last["InvoiceCode"] == "[concept]0001"


def test_credit_invoice_confirm_guard_and_call(wefact):
    assert server.credit_invoice(InvoiceCode="F2026-0001")["status"] == "error"
    wefact.queue(ok("invoice", "credit", invoice={"InvoiceCode": "F2026-0002", "Status": 8}))
    result = server.credit_invoice(InvoiceCode="F2026-0001", confirm=True)
    assert result["invoice"]["Status"] == 8
    assert wefact.last["action"] == "credit"


def test_mark_invoice_paid_sends_paydate_and_method(wefact):
    wefact.queue(ok("invoice", "markaspaid", success=["Factuur 2026010001 is betaald"]))
    result = server.mark_invoice_paid(InvoiceCode="2026010001", PayDate="2026-08-28", PaymentMethod="wire")
    assert result["success"] == ["Factuur 2026010001 is betaald"]
    r = wefact.last
    assert r["action"] == "markaspaid" and r["PayDate"] == "2026-08-28" and r["PaymentMethod"] == "wire"


def test_tool_returns_wefact_api_error_as_dict(wefact):
    wefact.queue(err("invoice", "markaspaid", "Conceptfacturen kunnen niet als betaald gemarkeerd worden"))
    result = server.mark_invoice_paid(InvoiceCode="[concept]0001")
    assert result["status"] == "error"
    assert result["errors"] == ["Conceptfacturen kunnen niet als betaald gemarkeerd worden"]


# -- products / subscriptions / purchase invoices --------------------------

def test_products(wefact):
    wefact.queue(ok("product", "list", totalresults=1, currentresults=1, offset=0, products=[{"ProductCode": "P0001"}]))
    assert server.list_products(searchfor="hosting")["products"][0]["ProductCode"] == "P0001"
    assert wefact.last["searchfor"] == "hosting"
    wefact.queue(ok("product", "show", product={"ProductCode": "P0001"}))
    assert server.get_product(ProductCode="P0001")["product"]["ProductCode"] == "P0001"
    assert wefact.last["action"] == "show"


def test_subscriptions(wefact):
    wefact.queue(ok("subscription", "list", totalresults=1, currentresults=1, offset=0,
                    subscriptions=[{"Identifier": 7, "TerminationDate": "2026-09-30"}]))
    result = server.list_subscriptions(status="terminated")
    assert result["subscriptions"][0]["Identifier"] == 7
    assert wefact.last["status"] == "terminated"
    wefact.queue(ok("subscription", "show", subscription={"Identifier": 7}))
    assert server.get_subscription(7)["subscription"]["Identifier"] == 7
    assert wefact.last["Identifier"] == "7"


def test_credit_invoices_map_to_creditinvoice_controller(wefact):
    wefact.queue(ok("creditinvoice", "list", totalresults=1, currentresults=1, offset=0,
                    creditinvoices=[{"CreditInvoiceCode": "CF0002"}]))
    assert server.list_credit_invoices(status=1)["creditinvoices"][0]["CreditInvoiceCode"] == "CF0002"
    assert wefact.last["controller"] == "creditinvoice" and wefact.last["status"] == "1"
    wefact.queue(ok("creditinvoice", "show", creditinvoice={"CreditInvoiceCode": "CF0002"}))
    server.get_credit_invoice(CreditInvoiceCode="CF0002")
    assert wefact.last["action"] == "show" and wefact.last["CreditInvoiceCode"] == "CF0002"


# -- escape hatch ----------------------------------------------------------

def test_wefact_request_passes_any_controller_action_and_nested_params(wefact):
    wefact.queue(ok("subscription", "edit", subscription={"Identifier": 1, "PriceExcl": 30}))
    result = server.wefact_request("subscription", "edit", {"Identifier": 1, "Subscription": {"PriceExcl": 30}})
    assert result["subscription"]["PriceExcl"] == 30
    r = wefact.last
    assert r["controller"] == "subscription" and r["action"] == "edit"
    assert r["Identifier"] == "1" and r["Subscription[PriceExcl]"] == "30"


# -- through the MCP layer -------------------------------------------------

def test_tools_are_registered_and_callable_via_mcp(wefact):
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    expected = {
        "list_debtors", "get_debtor", "create_debtor", "update_debtor",
        "list_invoices", "get_invoice", "create_invoice", "send_invoice",
        "credit_invoice", "mark_invoice_paid", "list_products", "get_product",
        "list_subscriptions", "get_subscription", "list_credit_invoices",
        "get_credit_invoice", "wefact_request",
    }
    assert expected <= names

    wefact.queue(ok("invoice", "show", invoice={"InvoiceCode": "F2026-0001", "AmountOutstanding": "25.00"}))
    content = asyncio.run(server.mcp.call_tool("get_invoice", {"InvoiceCode": "F2026-0001"}))
    # FastMCP returns (unstructured content, structured result) or a content list
    blocks = content[0] if isinstance(content, tuple) else content
    payload = json.loads(blocks[0].text)
    assert payload["invoice"]["AmountOutstanding"] == "25.00"


def test_missing_env_key_gives_clear_error(monkeypatch):
    monkeypatch.setattr(server, "_client", None)
    monkeypatch.delenv("WEFACT_API_KEY", raising=False)
    result = server.get_debtor(DebtorCode="DB1")
    assert result["status"] == "error" and "WEFACT_API_KEY" in result["message"]


def test_whoami_summarises_connection(wefact):
    wefact.queue(ok("debtor", "list", totalresults=42, currentresults=1, offset=0, debtors=[{"DebtorCode": "DB10000"}]))
    result = server.whoami()
    assert result == {"status": "success", "endpoint": "https://api.mijnwefact.nl/v2/",
                      "totalresults": 42, "first_debtor_code": "DB10000"}
    assert wefact.last["limit"] == "1"


def test_whoami_reports_blocked_ip(wefact):
    wefact.queue("IP currently in firewall", status_code=403)
    result = server.whoami()
    assert result["status"] == "error" and result["http_status"] == 403
