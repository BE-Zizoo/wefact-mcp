# Changelog

## v1.0.2 — 2026-10-16

- Claude Desktop extension: every release now ships `wefact-mcp.mcpb` — install via double-click or Settings → Extensions, enter your API key in Claude's own settings UI. Windows + Python 3.14; all dependencies bundled, no venv or JSON config needed.
- New `packaging/build_mcpb.py` builds the bundle (version and dependencies read from `pyproject.toml`); the release workflow builds and attaches it automatically.
- README and INSTALL.md document the extension route.

## v1.0.1 — 2026-10-16

- Pin `mcp>=1.10,<2`: the MCP Python SDK 2.x renamed FastMCP to MCPServer and broke the 1.x API, so fresh installs failed with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`. Existing installs: run `pip install "mcp<2"` inside the venv, or re-run `pip install -e ".[dev]"` after `git pull`.
- README: install and client-config instructions split into separate Windows (PowerShell), cmd.exe and macOS/Linux blocks — the old single block mixed `source`/`cp` with PowerShell.

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
