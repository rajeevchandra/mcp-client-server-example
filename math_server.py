from mcp.server.fastmcp import FastMCP
from typing import Any

# Initialize FastMCP with a name
mcp = FastMCP("calculator")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Adds two numbers."""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiplies two numbers."""
    return a * b

# Start the MCP server
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
