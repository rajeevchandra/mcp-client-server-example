import asyncio
import json
import sys
from typing import Optional
from contextlib import AsyncExitStack

import openai
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Setup Ollama (OpenAI-compatible local model)
openai.api_base = "http://localhost:11434/v1"
openai.api_key = "ollama"  # placeholder (Ollama doesn't need real auth)

class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path])
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        print("\n✅ Connected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            }
        } for tool in response.tools]

        response = openai.ChatCompletion.create(
            model="mistral-nemo",  # or mistral, codellama, etc.
            messages=messages,
            tools=available_tools,
            tool_choice="auto",
            temperature=0.7,
        )

        final_text = []
        for choice in response.choices:
            message = choice.message
            if message.get("tool_calls"):
                for tool_call in message["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    result = await self.session.call_tool(tool_name, tool_args)
                    final_text.append(f"[Tool: {tool_name} | Args: {tool_args}]\nResult: {result.content}")
                    messages.append({"role": "function", "name": tool_name, "content": result.content})
            elif message.get("content"):
                final_text.append(message["content"])

        return "\n".join(final_text)

    async def chat_loop(self):
        print("\n🧠 MCP Ollama Client Started! Type your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("Usage: python ollama_client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
