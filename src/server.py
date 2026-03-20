"""Agent Interface Validator — Lighthouse for AI agent accessibility."""

from mcp.server.fastmcp import FastMCP
from src.tools.validator_tools import register_validator_tools

mcp = FastMCP(
    "Agent Interface Validator",
    instructions=(
        "Like Google Lighthouse for websites, but for AI agent accessibility. "
        "Test APIs and services to check if they are properly accessible to "
        "AI agents. Get scores, recommendations and actionable fixes."
    ),
)

register_validator_tools(mcp)

def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
