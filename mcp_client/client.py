import json
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.types import LoggingMessageNotificationParams, PromptReference

class MCPClient:
    def __init__(self, command: str, args: list[str], env: Optional[dict] = None):
        self.command = command
        self.args = args
        self.env = env
        self._exit_stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def connect(self):
        server_params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env=self.env,
        )
        read, write = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(
                read,
                write,
                logging_callback=self._log_callback,
            )
        )
        await self._session.initialize()

    async def ask(self, internal_prompt: str) -> str:
        if not self._session:
            await self.connect()

        result = await self._session.call_tool(
            name="query",
            arguments={"question": internal_prompt},
        )

        try:
            return result.content[0].text if result.content else "No response"
        except (IndexError, AttributeError):
            return str(result.content) if result.content else "No response"
    
    async def _log_callback(self, params: LoggingMessageNotificationParams):
        # This receives ctx.info(), ctx.warning(), etc.
        print(f"[{params.level.upper()}] {params.data}")

    # async def list_tools(self):
    #     if self._session is None:
    #         await self.connect()

    #     return (await self._session.list_tools()).tools

    # async def call_tool(self, name: str, arguments: dict):
    #     if self._session is None:
    #         await self.connect()

    #     result = await self._session.call_tool(
    #         name=name,
    #         arguments=arguments,
    #     )
    #     return result

    async def close(self):
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

        

