# Changelog

## v1.0.0 — 2026-08-28

First public release.

- 18 MCP tools: debtors (list/get/create/update), invoices (list/get/create/send/credit/mark paid), products, subscriptions, purchase invoices, `whoami`, and the generic `wefact_request` escape hatch.
- Parameter names identical to the WeFact API docs; nested structures encoded as `InvoiceLines[0][ProductCode]` form fields.
- Retry with exponential backoff on network errors, 429 and 5xx; never on 403 (IP blocked).
- Pagination over all pages with WeFact's maximum page size (1000).
- `send_invoice` and `credit_invoice` require `confirm=true`; `create_invoice` always creates a concept.
- Structured error objects (`status`, `controller`, `action`, `message`, `errors`, `http_status`).
- 33 tests without network (httpx.MockTransport); CI on Python 3.10 and 3.12.
- Condensed WeFact v2 API reference in `docs/`, Dutch install guide in `INSTALL.md`.
