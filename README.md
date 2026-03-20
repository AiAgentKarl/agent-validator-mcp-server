# Agent Interface Validator 🔍

**Lighthouse for AI agents** — test if APIs and services are properly accessible to AI agents. Get scores, grades, and actionable recommendations.

## Installation

```bash
pip install agent-validator-mcp-server
```

```json
{"mcpServers": {"validator": {"command": "uvx", "args": ["agent-validator-mcp-server"]}}}
```

## Tools

| Tool | Description |
|------|-------------|
| `validate_api_endpoint` | Test a single API endpoint (score 0-100) |
| `validate_openapi_spec` | Check an OpenAPI spec for agent-friendliness |
| `check_agent_interface_url` | Check if a domain has an Agent Interface spec |

## License

MIT
