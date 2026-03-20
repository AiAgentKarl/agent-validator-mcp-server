"""Validator-Tools — API-Endpunkte auf Agent-Zugänglichkeit testen."""

import json
import httpx
from mcp.server.fastmcp import FastMCP


def register_validator_tools(mcp: FastMCP):

    @mcp.tool()
    async def validate_api_endpoint(
        url: str, method: str = "GET", expected_format: str = "json"
    ) -> dict:
        """Test a single API endpoint for agent accessibility.

        Checks response format, status codes, documentation quality,
        and gives a score from 0-100.

        Args:
            url: The API endpoint URL to test
            method: HTTP method (GET, POST, etc.)
            expected_format: Expected response format (json, xml, text)
        """
        checks = []
        score = 0
        max_score = 100

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                if method.upper() == "GET":
                    resp = await client.get(url)
                else:
                    resp = await client.request(method.upper(), url)

                # Check 1: Erreichbarkeit (20 Punkte)
                if resp.status_code < 500:
                    score += 20
                    checks.append({"check": "reachable", "passed": True, "score": 20,
                                   "detail": f"Status {resp.status_code}"})
                else:
                    checks.append({"check": "reachable", "passed": False, "score": 0,
                                   "detail": f"Server error {resp.status_code}"})

                # Check 2: JSON-Response (20 Punkte)
                content_type = resp.headers.get("content-type", "")
                if "json" in content_type:
                    score += 20
                    checks.append({"check": "json_response", "passed": True, "score": 20})
                    try:
                        data = resp.json()
                        # Check 3: Strukturierte Daten (15 Punkte)
                        if isinstance(data, (dict, list)):
                            score += 15
                            checks.append({"check": "structured_data", "passed": True, "score": 15})
                        else:
                            checks.append({"check": "structured_data", "passed": False, "score": 0})
                    except Exception:
                        checks.append({"check": "structured_data", "passed": False, "score": 0,
                                       "detail": "JSON parse error"})
                else:
                    checks.append({"check": "json_response", "passed": False, "score": 0,
                                   "detail": f"Content-Type: {content_type}"})

                # Check 4: CORS-Headers (10 Punkte)
                cors = resp.headers.get("access-control-allow-origin", "")
                if cors:
                    score += 10
                    checks.append({"check": "cors_enabled", "passed": True, "score": 10})
                else:
                    checks.append({"check": "cors_enabled", "passed": False, "score": 0,
                                   "detail": "No CORS headers"})

                # Check 5: Antwortzeit (15 Punkte)
                elapsed_ms = resp.elapsed.total_seconds() * 1000
                if elapsed_ms < 500:
                    score += 15
                    checks.append({"check": "fast_response", "passed": True, "score": 15,
                                   "detail": f"{elapsed_ms:.0f}ms"})
                elif elapsed_ms < 2000:
                    score += 8
                    checks.append({"check": "fast_response", "passed": True, "score": 8,
                                   "detail": f"{elapsed_ms:.0f}ms (acceptable)"})
                else:
                    checks.append({"check": "fast_response", "passed": False, "score": 0,
                                   "detail": f"{elapsed_ms:.0f}ms (too slow)"})

                # Check 6: Fehlerbehandlung (10 Punkte)
                if resp.status_code == 200:
                    score += 5
                if resp.status_code in (400, 401, 403, 404, 422):
                    score += 10
                    checks.append({"check": "proper_error_codes", "passed": True, "score": 10,
                                   "detail": "Uses standard HTTP error codes"})

                # Check 7: Rate-Limit-Headers (10 Punkte)
                rate_headers = [h for h in resp.headers if "rate" in h.lower() or "limit" in h.lower()]
                if rate_headers:
                    score += 10
                    checks.append({"check": "rate_limit_info", "passed": True, "score": 10})
                else:
                    checks.append({"check": "rate_limit_info", "passed": False, "score": 0,
                                   "detail": "No rate limit headers"})

            except httpx.ConnectError:
                checks.append({"check": "reachable", "passed": False, "score": 0,
                               "detail": "Connection failed"})
            except httpx.TimeoutException:
                checks.append({"check": "reachable", "passed": False, "score": 0,
                               "detail": "Request timed out"})

        # Bewertung
        if score >= 80:
            grade = "A — Excellent agent accessibility"
        elif score >= 60:
            grade = "B — Good, minor improvements recommended"
        elif score >= 40:
            grade = "C — Fair, significant improvements needed"
        elif score >= 20:
            grade = "D — Poor agent accessibility"
        else:
            grade = "F — Not agent-accessible"

        return {
            "url": url,
            "method": method,
            "score": min(score, max_score),
            "max_score": max_score,
            "grade": grade,
            "checks": checks,
            "recommendations": _get_recommendations(checks),
        }

    @mcp.tool()
    async def validate_openapi_spec(spec_url: str) -> dict:
        """Validate an OpenAPI spec for agent-friendliness.

        Checks if the API documentation is good enough for AI agents
        to use the API effectively.

        Args:
            spec_url: URL to OpenAPI/Swagger spec
        """
        score = 0
        checks = []

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(spec_url)
                resp.raise_for_status()
                spec = resp.json()
            except Exception as e:
                return {"error": f"Could not fetch spec: {e}"}

        # Check: Info-Sektion
        info = spec.get("info", {})
        if info.get("title") and info.get("description"):
            score += 15
            checks.append({"check": "api_description", "passed": True, "score": 15})
        else:
            checks.append({"check": "api_description", "passed": False, "score": 0,
                           "detail": "Missing title or description"})

        # Check: Endpoints vorhanden
        paths = spec.get("paths", {})
        if len(paths) > 0:
            score += 15
            checks.append({"check": "endpoints_defined", "passed": True, "score": 15,
                           "detail": f"{len(paths)} endpoints"})
        else:
            checks.append({"check": "endpoints_defined", "passed": False, "score": 0})

        # Check: Operation descriptions
        described = 0
        total_ops = 0
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    total_ops += 1
                    if details.get("description") or details.get("summary"):
                        described += 1

        if total_ops > 0:
            desc_pct = (described / total_ops) * 100
            if desc_pct >= 80:
                score += 20
                checks.append({"check": "operation_descriptions", "passed": True, "score": 20,
                               "detail": f"{desc_pct:.0f}% of operations described"})
            elif desc_pct >= 50:
                score += 10
                checks.append({"check": "operation_descriptions", "passed": True, "score": 10,
                               "detail": f"{desc_pct:.0f}% described (improve to 80%+)"})
            else:
                checks.append({"check": "operation_descriptions", "passed": False, "score": 0,
                               "detail": f"Only {desc_pct:.0f}% described"})

        # Check: Parameter descriptions
        params_described = 0
        total_params = 0
        for path, methods in paths.items():
            for method, details in methods.items():
                for p in details.get("parameters", []):
                    total_params += 1
                    if p.get("description"):
                        params_described += 1

        if total_params > 0:
            param_pct = (params_described / total_params) * 100
            if param_pct >= 80:
                score += 15
                checks.append({"check": "parameter_descriptions", "passed": True, "score": 15})
            else:
                checks.append({"check": "parameter_descriptions", "passed": False, "score": 0,
                               "detail": f"Only {param_pct:.0f}% of parameters described"})
        else:
            score += 10
            checks.append({"check": "parameter_descriptions", "passed": True, "score": 10,
                           "detail": "No parameters to check"})

        # Check: Schemas/Models
        schemas = spec.get("components", {}).get("schemas", {}) or spec.get("definitions", {})
        if schemas:
            score += 15
            checks.append({"check": "response_schemas", "passed": True, "score": 15,
                           "detail": f"{len(schemas)} schemas defined"})
        else:
            checks.append({"check": "response_schemas", "passed": False, "score": 0})

        # Check: Auth info
        security = spec.get("components", {}).get("securitySchemes", {}) or spec.get("securityDefinitions", {})
        if security:
            score += 10
            checks.append({"check": "auth_documented", "passed": True, "score": 10})
        else:
            checks.append({"check": "auth_documented", "passed": False, "score": 0})

        # Check: Server URLs
        servers = spec.get("servers", [])
        if servers or spec.get("host"):
            score += 10
            checks.append({"check": "server_urls", "passed": True, "score": 10})
        else:
            checks.append({"check": "server_urls", "passed": False, "score": 0,
                           "detail": "No server URLs defined"})

        grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D" if score >= 20 else "F"

        return {
            "spec_url": spec_url,
            "api_name": info.get("title", "Unknown"),
            "score": score,
            "grade": grade,
            "total_endpoints": len(paths),
            "total_operations": total_ops,
            "checks": checks,
            "recommendations": _get_recommendations(checks),
        }

    @mcp.tool()
    async def check_agent_interface_url(domain: str) -> dict:
        """Check if a domain hosts an Agent Interface spec.

        Looks for the spec at the well-known URL:
        https://domain/.well-known/agent-interface.json

        Args:
            domain: Domain to check (e.g. "example.com")
        """
        if not domain.startswith("http"):
            url = f"https://{domain}/.well-known/agent-interface.json"
        else:
            url = f"{domain.rstrip('/')}/.well-known/agent-interface.json"

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    spec = resp.json()
                    business = spec.get("business", {})
                    return {
                        "domain": domain,
                        "has_agent_interface": True,
                        "business_name": business.get("name", "Unknown"),
                        "capabilities_count": len(spec.get("capabilities", [])),
                        "spec_version": spec.get("agent_interface", "unknown"),
                        "url": url,
                    }
                else:
                    return {
                        "domain": domain,
                        "has_agent_interface": False,
                        "status_code": resp.status_code,
                        "message": "No Agent Interface spec found at well-known URL.",
                    }
            except Exception as e:
                return {
                    "domain": domain,
                    "has_agent_interface": False,
                    "error": str(e),
                }


def _get_recommendations(checks: list) -> list[str]:
    """Empfehlungen basierend auf fehlgeschlagenen Checks."""
    recs = []
    for c in checks:
        if not c.get("passed", True):
            name = c.get("check", "")
            if name == "json_response":
                recs.append("Return JSON responses with Content-Type: application/json")
            elif name == "cors_enabled":
                recs.append("Add CORS headers (Access-Control-Allow-Origin) for cross-origin access")
            elif name == "fast_response":
                recs.append("Optimize response time to under 500ms for better agent experience")
            elif name == "rate_limit_info":
                recs.append("Add rate limit headers (X-RateLimit-Limit, X-RateLimit-Remaining)")
            elif name == "operation_descriptions":
                recs.append("Add descriptions to all API operations so agents understand what each endpoint does")
            elif name == "parameter_descriptions":
                recs.append("Describe all parameters — agents need clear descriptions to use them correctly")
            elif name == "response_schemas":
                recs.append("Define response schemas so agents know what data format to expect")
            elif name == "auth_documented":
                recs.append("Document authentication requirements clearly")
            elif name == "api_description":
                recs.append("Add a title and description to your API spec")
    return recs
