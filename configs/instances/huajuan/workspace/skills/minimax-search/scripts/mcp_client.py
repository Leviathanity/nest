#!/usr/bin/env python3
"""
MiniMax Token Plan MCP Client
处理 MCP 协议的初始化和工具调用
"""

import sys
import json
import os
import subprocess

class MCPClient:
    def __init__(self, api_key, api_host):
        self.api_key = api_key
        self.api_host = api_host
        self.proc = None
        self.request_id = 1
        
    def start(self):
        env = os.environ.copy()
        env["MINIMAX_API_KEY"] = self.api_key
        env["MINIMAX_API_HOST"] = self.api_host
        
        self.proc = subprocess.Popen(
            ["uvx", "--from", "minimax-coding-plan-mcp", "minimax-coding-plan-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=1
        )
        
        # 初始化
        init_request = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "minimax-search",
                    "version": "1.0.0"
                }
            }
        }
        
        self._send(init_request)
        # 读取初始化响应
        self._read_response()
        
        # 发送 initialized 通知
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {}
        }
        self._send(initialized_notification)
        
    def _send(self, request):
        line = json.dumps(request) + "\n"
        self.proc.stdin.write(line)
        self.proc.stdin.flush()
        
    def _read_response(self):
        line = self.proc.stdout.readline()
        if line:
            return json.loads(line.strip())
        return None
        
    def call_tool(self, tool_name, arguments):
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        self.request_id += 1
        
        self._send(request)
        response = self._read_response()
        
        if response and "result" in response:
            return response["result"]
        elif response and "error" in response:
            raise Exception(f"MCP Error: {response['error']}")
        return None
        
    def close(self):
        if self.proc:
            self.proc.stdin.close()
            self.proc.wait(timeout=5)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mcp_client.py <query> [query2] [query3] ...", file=sys.stderr)
        sys.exit(1)
    
    queries = sys.argv[1:]
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    api_host = os.environ.get("MINIMAX_API_HOST", "https://api.minimaxi.com")
    
    if not api_key:
        print("Error: MINIMAX_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    client = MCPClient(api_key, api_host)
    
    try:
        client.start()
        result = client.call_tool("web_search", {"query": queries[0] if len(queries) == 1 else " ".join(queries)})
        
        if result and "content" in result:
            for item in result["content"]:
                if item.get("type") == "text":
                    print(item["text"])
        elif result and "text" in result:
            print(result["text"])
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
