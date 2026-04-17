#!/usr/bin/env python3
"""
MiniMax Token Plan MCP - Web Search Tool
直接通过 MCP 协议调用 search 工具
"""

import sys
import json
import os
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 search.py <query> [query2] [query3] ...", file=sys.stderr)
        sys.exit(1)
    
    queries = sys.argv[1:]
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    api_host = os.environ.get("MINIMAX_API_HOST", "https://api.minimaxi.com")
    
    if not api_key:
        print("Error: MINIMAX_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # 构建请求
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "web_search",
            "arguments": {
                "queries": queries
            }
        }
    }
    
    # 调用 MCP server
    env = os.environ.copy()
    env["MINIMAX_API_KEY"] = api_key
    env["MINIMAX_API_HOST"] = api_host
    
    try:
        proc = subprocess.Popen(
            ["uvx", "--from", "minimax-coding-plan-mcp", "minimax-coding-plan-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True
        )
        
        # 发送请求
        request_line = json.dumps(request) + "\n"
        stdout, stderr = proc.communicate(input=request_line, timeout=60)
        
        if stderr:
            print(f"STDERR: {stderr}", file=sys.stderr)
        
        # 解析响应
        # MCP 可能输出多个 JSON 对象，第一行是初始化，后续是响应
        lines = stdout.strip().split("\n")
        for line in lines:
            if not line.strip():
                continue
            try:
                resp = json.loads(line)
                if "error" in resp:
                    print(f"Error: {resp['error']}", file=sys.stderr)
                    continue
                if "result" in resp:
                    result = resp["result"]
                    if isinstance(result, dict) and "content" in result:
                        for item in result["content"]:
                            if item.get("type") == "text":
                                print(item["text"])
                    elif isinstance(result, dict) and "text" in result:
                        print(result["text"])
            except json.JSONDecodeError:
                continue
                
    except subprocess.TimeoutExpired:
        print("Error: MCP server timed out", file=sys.stderr)
        proc.kill()
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
