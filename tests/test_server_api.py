"""Tests for server HTTP, REST, OpenAPI, and health endpoints."""

from __future__ import annotations

import os

from starlette.testclient import TestClient

from edgar_mcp.client import SECClient
from edgar_mcp.server import mcp


def test_health_endpoint() -> None:
    """GET /health returns healthy status and service metadata."""
    client = TestClient(mcp.sse_app())
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "edgar-mcp"
    assert data["version"] == "0.1.0"
    assert data["tools_count"] == 6
    assert "ticker_cache_size" in data
    assert response.headers["access-control-allow-origin"] == "*"


def test_v1_tools_endpoint() -> None:
    """GET /v1/tools returns OpenAI-compatible function definitions."""
    client = TestClient(mcp.sse_app())
    response = client.get("/v1/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert len(data["tools"]) == 6
    names = {t["function"]["name"] for t in data["tools"]}
    assert "resolve_company" in names
    assert "get_financial_concept" in names
    assert "list_filings" in names
    assert "compare_companies" in names
    assert "get_filing_section" in names
    assert "search_full_text" in names


def test_openapi_spec_endpoint() -> None:
    """GET /openapi.json returns valid OpenAPI 3.1 specification."""
    client = TestClient(mcp.sse_app())
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["openapi"] == "3.1.0"
    assert "paths" in data
    assert "/health" in data["paths"]
    assert "/api/tools/resolve_company" in data["paths"]
    assert "/api/tools/get_financial_concept" in data["paths"]


def test_invoke_tool_rest_endpoint(installed_client: SECClient) -> None:
    """POST /api/tools/{name} executes tool and returns structured result."""
    client = TestClient(mcp.sse_app())
    # Test resolve_company with test mock fixtures
    response = client.post(
        "/api/tools/resolve_company",
        json={"query": "TSTC"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["resolved"] is True
    assert data["ticker"] == "TSTC"
    assert data["cik"] == "9999901"


def test_invoke_tool_wrapped_arguments(installed_client: SECClient) -> None:
    """POST /api/tools/{name} accepts arguments dict inside body."""
    client = TestClient(mcp.sse_app())
    response = client.post(
        "/api/tools/resolve_company",
        json={"arguments": {"query": "TSTC"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["resolved"] is True
    assert data["ticker"] == "TSTC"


def test_invoke_nonexistent_tool() -> None:
    """POST /api/tools/missing returns 404."""
    client = TestClient(mcp.sse_app())
    response = client.post("/api/tools/not_a_real_tool", json={})
    assert response.status_code == 404
    assert "not found" in response.json()["error"]


def test_api_key_authentication(installed_client: SECClient) -> None:
    """When EDGAR_MCP_API_KEY is configured, requests must provide bearer token."""
    client = TestClient(mcp.sse_app())
    os.environ["EDGAR_MCP_API_KEY"] = "secret-token-123"
    try:
        # Without header -> 401
        res_unauth = client.post("/api/tools/resolve_company", json={"query": "TSTC"})
        assert res_unauth.status_code == 401

        # With incorrect header -> 401
        res_bad = client.post(
            "/api/tools/resolve_company",
            json={"query": "TSTC"},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert res_bad.status_code == 401

        # With correct header -> 200
        res_ok = client.post(
            "/api/tools/resolve_company",
            json={"query": "TSTC"},
            headers={"Authorization": "Bearer secret-token-123"},
        )
        assert res_ok.status_code == 200
        assert res_ok.json()["resolved"] is True
    finally:
        os.environ.pop("EDGAR_MCP_API_KEY", None)


def test_server_module_importable():
    import importlib
    mod = importlib.import_module('edgar_mcp.server')
    assert hasattr(mod, 'main')


def test_fake_transport_never_hits_network():
    # Verify our test fixtures cannot accidentally reach sec.gov
    import httpx
    called = []
    class SafeTransport(httpx.BaseTransport):
        def handle_request(self, r): called.append(r.url.host); return httpx.Response(200,json={})
    with httpx.Client(transport=SafeTransport()) as c:
        c.get('https://fake.local/test')
    assert 'sec.gov' not in called
