import json
from typing import Optional
from contextlib import AsyncExitStack
import httpx
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from mcp.types import LoggingMessageNotificationParams, PromptReference
from mcp.client.sse import sse_client

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

    async def ask(self, internal_prompt: str, command: str, git_info: dict | None) -> str:
        if not self._session:
            await self.connect()

        result = await self._session.call_tool(
            name="query",
            arguments={"question": internal_prompt, "command": command, "git_info": git_info},
        )

        try:
            return result.content[0].text if result.content else "No response"
        except (IndexError, AttributeError):
            return str(result.content) if result.content else "No response"
        
    async def run_command(self, command: str, prompt: str, git_info: dict | None = None) -> str:
        return await self.ask(prompt, command, git_info)
    
    async def warmup(self):
        if not self._session:
            await self.connect()
    
    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        if not self._session:
            await self.connect()
        
        result = await self._session.call_tool(
            name=tool_name,
            arguments=arguments
        )

        if result.content and len(result.content) > 0:
            return result.content[0].text if hasattr(result.content[0], 'text') else str(result.content[0])
        
        return str(result)
    
    async def read_resource(self, uri: str):
        if not self._session:
            await self.connect()
        
        result = await self._session.read_resource(uri=uri)
  
        if result.contents and len(result.contents) > 0:
            return result.contents[0].text
        return None

    async def _log_callback(self, params: LoggingMessageNotificationParams):
        # This receives ctx.info(), ctx.warning(), etc.
        print(f"[{params.level.upper()}] {params.data}")

    async def close(self):
        await self._exit_stack.aclose()
        self._session = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

        

class MCPHTTPClient:
    def __init__(self, base_url: str = "http://127.0.0.1:3000/mcp"):
        self.base_url = base_url
        self._http_client = httpx.AsyncClient(timeout=300.0)
        self._session_id = None

    async def _post(self, message: dict):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        
        response = await self._http_client.post(
            self.base_url,
            json=message,
            headers=headers
        )
        
        if "Mcp-Session-Id" in response.headers:
            self._session_id = response.headers["Mcp-Session-Id"]
        
        content_type = response.headers.get("Content-Type", "")
        
        if "text/event-stream" in content_type:
            # parse SSE stream
            lines = response.text.strip().split('\n')
            events = []
            for line in lines:
                if line.startswith('data: '):
                    json_data = line[6:]  # remove 'data: ' prefix
                    events.append(json.loads(json_data))
            if not events:
                raise Exception("No data in SSE stream")
            return events[-1]  # get the last item in events which is the llm response for user command
        else:
            if response.content:
                try:
                    return response.json()
                except ValueError:
                    return None
            return None

    async def connect(self):
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "dev-assistant-client",
                    "version": "1.0.0"
                }
            }
        }
        
        result = await self._post(init_message)
        
        if "error" in result:
            raise Exception(f"Initialize failed: {result['error']}")
        
        # send initialized notification
        initialized_message = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        await self._post(initialized_message)

    async def ask(self, internal_prompt: str, command: str, git_info: dict | None) -> str:
        if not self._session_id:
            await self.connect()

        message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "query",
                "arguments": {
                    "question": internal_prompt,
                    "command": command,
                    "git_info": git_info
                }
            }
        }
        
        result = await self._post(message)
        
        if "error" in result:
            raise Exception(f"Tool call failed: {result['error']}")
        
        content = result.get("result", {}).get("content", [])
        if content and len(content) > 0:
            return content[0].get("text", "No response")
        
        return "No response"
        
    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        if not self._session_id:
            await self.connect()
        
        message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        result = await self._post(message)
        
        if "error" in result:
            raise Exception(f"Tool call failed: {result['error']}")
        
        content = result.get("result", {}).get("content", [])
        if content and len(content) > 0:
            return content[0].get("text", str(content[0]))
        
        return str(result)
    
    async def read_resource(self, uri: str):
        if not self._session_id:
            await self.connect()
        
        message = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "resources/read",
            "params": {
                "uri": uri
            }
        }
        
        result = await self._post(message)
        
        if "error" in result:
            raise Exception(f"Resource read failed: {result}")
        
        contents = result.get("result", {}).get("contents", [])
        if contents and len(contents) > 0:
            return contents[0].get("text", "")
        
        return None

    async def close(self):
        if self._session_id:
            try:
                await self._http_client.delete(
                    self.base_url,
                    headers={"Mcp-Session-Id": self._session_id}
                )
            except:
                pass
        
        await self._http_client.aclose()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()