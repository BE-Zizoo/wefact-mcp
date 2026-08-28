# wefact-mcp

[![CI](https://github.com/BE-Zizoo/wefact-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/BE-Zizoo/wefact-mcp/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A local [MCP](https://modelcontextprotocol.io) server for the Dutch/Belgian
invoicing platform [WeFact](https://www.wefact.nl). Lets Claude Desktop,
Claude Code, Cursor or any MCP client read and modify your WeFact
administration through plain language.

> "List all outstanding invoices older than 30 days, grouped by customer."
> "Create a draft invoice for DB10000 with one line 'Monthly hosting' at €25."
> "Which subscriptions end next month?"
> "Mark invoice 2026010001 as paid today, bank transfer."

Runs on your own machine over stdio. The API key lives in a local `.env`
and only ever travels to `api.mijnwefact.nl`. No telemetry, no proxy.

**Nederlandstalige installatiehandleiding: [INSTALL.md](INSTALL.md).**

## Tools

| Tool | WeFact controller / action |
|---|---|
| `list_debtors`, `get_debtor`, `create_debtor`, `update_debtor` | `debtor` list / show / add / edit |
| `list_invoices`, `get_invoice`, `create_invoice`, `send_invoice` | `invoice` list / show / add / sendbyemail |
| `credit_invoice`, `mark_invoice_paid` | `invoice` credit / markaspaid |
| `list_products`, `get_product` | `product` list / show |
| `list_subscriptions`, `get_subscription` | `subscription` list / show |
| `list_credit_invoices`, `get_credit_invoice` | `creditinvoice` list / show (purchase invoices, see below) |
| `whoami` | connection check (API key + IP whitelist) |
| `wefact_request` | any controller/action, parameters 1:1 from the docs |

Field names are identical to the [WeFact API docs](https://developer.wefact.com/)
(`DebtorCode`, `InvoiceLines`, `PriceExcl`, `TaxCode`, ...). Nested structures
are passed as JSON lists/objects; the server encodes them into WeFact's
`InvoiceLines[0][ProductCode]` form notation.

Anything without a dedicated tool goes through `wefact_request`:

```json
{ "controller": "subscription", "action": "edit",
  "params": { "Identifier": 12, "Subscription": { "PriceExcl": 30 } } }
```

`docs/wefact-api-reference.md` contains a compact reference of every
controller, action and field, so the model does not need to browse the docs.

### Things worth knowing about WeFact

- **`creditinvoice` = purchase invoices** (invoices *from* suppliers). Credit
  notes you issue *to* customers are ordinary invoices with `Status` 8 →
  `list_invoices(status=8)`.
- Invoice `Status`: `0` concept, `2` sent, `3` partly paid, `4` paid,
  `8` credit invoice, `9` expired.
- `PaymentMethod`: `wire` (bank transfer), `cash`, `card`, `auth` (direct
  debit), `paypal`, `ideal`, `accounting`, `various`, `other`.
- The API is IPv4-only and requires your IP to be whitelisted under
  Settings → API. Rate limit: 200 calls/min, 3 600/hour; exceeding it gets the
  IP blocked (HTTP 403).
- One endpoint, POST only, `application/x-www-form-urlencoded`.

## Safety

- `create_invoice` always creates a **concept** (Status 0). Nothing is sent.
- `send_invoice` and `credit_invoice` refuse unless `confirm=true`, so the
  model has to summarise and get your approval first.
- `mark_invoice_paid` is reversible: `wefact_request("invoice", "markasunpaid", {...})`.
- HTTP 403 is **never** retried (it means "IP blocked"; retrying extends the
  block). Network errors, 429 and 5xx are retried 3× with exponential backoff
  (0.5 s → 1 s → 2 s).
- Every failure comes back as a structured object the model can act on:
  `{"status": "error", "controller", "action", "message", "errors": [...], "http_status"}`.

## Pagination

Every `list_*` tool takes `limit` / `offset` (default 100 / 0) and
`all_pages=true`, which walks all pages using WeFact's maximum page size of
1 000 and stops on `totalresults`. 10 000 debtors = 10 calls.

## Install

Python 3.10+.

```bash
git clone https://github.com/BE-Zizoo/wefact-mcp.git
cd wefact-mcp
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env             # Windows: copy .env.example .env
```

Put your key in `.env` (`WEFACT_API_KEY=...`). Create it in WeFact under
Settings → API and whitelist your IPv4 address on the same page.

```bash
pytest        # 33 tests, no network needed
```

## Configure your MCP client

### Claude Desktop

`%APPDATA%\Claude\claude_desktop_config.json` (Windows) or
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "wefact": {
      "command": "/path/to/wefact-mcp/.venv/bin/python",
      "args": ["-m", "wefact_mcp"],
      "cwd": "/path/to/wefact-mcp"
    }
  }
}
```

On Windows use `"C:\\path\\to\\wefact-mcp\\.venv\\Scripts\\python.exe"`.
`cwd` is what lets the server find your `.env`; alternatively drop `.env` and
pass `"env": { "WEFACT_API_KEY": "..." }` instead. Fully quit and restart
Claude Desktop, then ask: *"Use the wefact `whoami` tool."*

### Claude Code

```bash
claude mcp add wefact -e WEFACT_API_KEY=your-key -- /path/to/wefact-mcp/.venv/bin/python -m wefact_mcp
```

### Cursor and others

Same `command`, `args` and `cwd`.

## Example prompts → tool calls

| Prompt | What the model calls |
|---|---|
| Outstanding invoices older than 30 days, per customer | `list_invoices(status=2, paybefore_to=<today − 30 d>, all_pages=true)` |
| Draft invoice for DB10000, "Monthly hosting" €25 | `create_invoice("DB10000", [{"Description": "Monthly hosting", "PriceExcl": 25, "TaxCode": "V21"}])` |
| Send it | `send_invoice(InvoiceCode="[concept]0001", confirm=true)` — after asking you |
| Subscriptions ending next month | `list_subscriptions(all_pages=true)`, filtered on `TerminationDate` |
| Mark 2026010001 paid today by bank transfer | `mark_invoice_paid(InvoiceCode="2026010001", PayDate="2026-08-28", PaymentMethod="wire")` |
| Raise the VAT code on subscription 12 | `wefact_request("subscription", "edit", {"Identifier": 12, "Subscription": {"TaxCode": "V21"}})` |
| Download invoice PDF | `wefact_request("invoice", "download", {"InvoiceCode": "F2026-0001"})` |
| Send a payment reminder | `wefact_request("invoice", "sendreminderbyemail", {"InvoiceCode": "F2026-0001"})` |

## Project layout

```
wefact_mcp/client.py            HTTP client: form encoding, retry/backoff, pagination, errors
wefact_mcp/server.py            FastMCP tool definitions
tests/                          33 tests against a fake WeFact (httpx.MockTransport)
docs/wefact-api-reference.md    condensed WeFact v2 API reference
INSTALL.md                      Dutch step-by-step install guide
```

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

Adding a tool: write a function in `server.py` decorated with `@tool`, use
WeFact's field names as parameter names, return the raw API response. Raise
`WeFactError` for local validation; the decorator turns it into the
structured error dict.

## Limitations

- Not an official WeFact product. Built against API v2.6 docs; field lists in
  `docs/` may lag behind WeFact's changelog — `wefact_request` always works.
- No IPv6 (WeFact limitation).
- Uses the debtor's configured send method; Peppol/postal sending behaves
  exactly as it does in the WeFact UI.

## License

MIT. See [LICENSE](LICENSE).
