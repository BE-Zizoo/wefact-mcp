import httpx
import pytest

from wefact_mcp.client import WeFactClient, WeFactError, flatten_params
from tests.conftest import err, ok


# -- form encoding ---------------------------------------------------------

def test_flatten_nested_lists_and_dicts_use_php_bracket_notation():
    fields = flatten_params({
        "DebtorCode": "DB10000",
        "InvoiceLines": [{"ProductCode": "P0001", "Number": 2}, {"Description": "Reiskosten"}],
        "modified": {"from": "2026-01-01 00:00:00"},
        "Groups": [1, 2],
        "Flag": True,
        "Empty": None,
    })
    assert ("DebtorCode", "DB10000") in fields
    assert ("InvoiceLines[0][ProductCode]", "P0001") in fields
    assert ("InvoiceLines[0][Number]", "2") in fields
    assert ("InvoiceLines[1][Description]", "Reiskosten") in fields
    assert ("modified[from]", "2026-01-01 00:00:00") in fields
    assert ("Groups[1]", "2") in fields
    assert ("Flag", "1") in fields
    assert ("Empty", "") in fields


def test_request_posts_api_key_controller_action_as_form(wefact):
    from wefact_mcp import server
    wefact.queue(ok("debtor", "show", debtor={"DebtorCode": "DB10000"}))
    server.get_client().request("debtor", "show", {"DebtorCode": "DB10000"})
    assert wefact.last == {"api_key": "test-key", "controller": "debtor",
                           "action": "show", "DebtorCode": "DB10000"}


# -- error handling --------------------------------------------------------

def test_api_status_error_raises_structured_wefact_error(wefact):
    from wefact_mcp import server
    wefact.queue(err("invoice", "show", "Factuur F9999 bestaat niet"))
    with pytest.raises(WeFactError) as info:
        server.get_client().request("invoice", "show", {"InvoiceCode": "F9999"})
    d = info.value.to_dict()
    assert d["status"] == "error"
    assert d["controller"] == "invoice" and d["action"] == "show"
    assert d["errors"] == ["Factuur F9999 bestaat niet"]
    assert d["http_status"] == 200


def test_http_403_ip_blocked_is_not_retried(wefact):
    from wefact_mcp import server
    wefact.queue("IP currently in firewall", status_code=403)
    with pytest.raises(WeFactError) as info:
        server.get_client().request("debtor", "list")
    assert info.value.http_status == 403
    assert len(wefact.requests) == 1


def test_non_json_body_raises(wefact):
    from wefact_mcp import server
    wefact.queue("<html>maintenance</html>", status_code=200)
    with pytest.raises(WeFactError, match="non-JSON"):
        server.get_client().request("debtor", "list")


def test_missing_api_key_rejected():
    with pytest.raises(ValueError):
        WeFactClient("")


# -- retry / backoff -------------------------------------------------------

def test_retries_on_5xx_with_exponential_backoff_then_succeeds():
    delays = []
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json=ok("debtor", "list", debtors=[], totalresults=0))

    client = WeFactClient("k", transport=httpx.MockTransport(handler),
                          sleep=delays.append, backoff_base=0.5, max_retries=3)
    assert client.request("debtor", "list")["status"] == "success"
    assert calls["n"] == 3
    assert delays == [0.5, 1.0]


def test_retries_on_network_error_then_gives_up():
    delays = []

    def handler(request):
        raise httpx.ConnectError("boom")

    client = WeFactClient("k", transport=httpx.MockTransport(handler),
                          sleep=delays.append, max_retries=2)
    with pytest.raises(WeFactError, match="Network error after 3 attempts"):
        client.request("debtor", "list")
    assert delays == [0.5, 1.0]


def test_429_rate_limit_is_retried():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, text="slow down")
        return httpx.Response(200, json=ok("product", "list", products=[], totalresults=0))

    client = WeFactClient("k", transport=httpx.MockTransport(handler), sleep=lambda _: None)
    client.request("product", "list")
    assert calls["n"] == 2


# -- pagination ------------------------------------------------------------

def test_list_all_walks_pages_until_totalresults(wefact):
    from wefact_mcp import server
    wefact.queue(ok("debtor", "list", totalresults=5, currentresults=2, offset=0,
                    debtors=[{"DebtorCode": "DB1"}, {"DebtorCode": "DB2"}]))
    wefact.queue(ok("debtor", "list", totalresults=5, currentresults=2, offset=2,
                    debtors=[{"DebtorCode": "DB3"}, {"DebtorCode": "DB4"}]))
    wefact.queue(ok("debtor", "list", totalresults=5, currentresults=1, offset=4,
                    debtors=[{"DebtorCode": "DB5"}]))
    result = server.get_client().list_all("debtor", {"searchfor": "x"}, page_size=2)
    assert [d["DebtorCode"] for d in result["debtors"]] == ["DB1", "DB2", "DB3", "DB4", "DB5"]
    assert result["totalresults"] == 5 and result["currentresults"] == 5
    assert [r["offset"] for r in wefact.requests] == ["0", "2", "4"]
    assert all(r["limit"] == "2" and r["searchfor"] == "x" for r in wefact.requests)


def test_list_all_stops_on_empty_page_and_missing_key(wefact):
    from wefact_mcp import server
    # WeFact omits the plural key when there are zero results
    wefact.queue(ok("subscription", "list", totalresults=0, currentresults=0, offset=0))
    result = server.get_client().list_all("subscription")
    assert result == {"totalresults": 0, "currentresults": 0, "subscriptions": []}
    assert len(wefact.requests) == 1
