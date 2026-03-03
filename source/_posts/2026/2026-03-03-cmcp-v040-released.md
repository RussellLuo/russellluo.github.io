categories:
- AI

tags:
- AI必知必会

title: cMCP v0.4.0发布：用配置文件管理你的MCP服务器
---

大家好！今天给大家介绍cMCP v0.4.0的重要更新。

## cMCP是什么？

[cMCP][1]是一个MCP服务器的命令行工具，可以理解为“MCP版的curl” —— 通过命令行就能快速调用和测试MCP服务器的功能。

基本用法：

```bash
# STDIO transport
cmcp 'python server.py' tools/list

# HTTP transport
cmcp http://localhost:8000/mcp tools/call name=add arguments:='{"a": 1, "b": 2}'
```

## v0.4.0新特性：`mcp.json`配置支持

为什么引入`mcp.json`配置文件？

1. **简化命令输入**：以前每次调用都要输入完整的命令或URL以及各种配置参数，比较繁琐。
2. **拥抱生态标准**：MCP生态逐渐形成了[MCP JSON配置标准][2]，主流工具如Cursor、Claude Code都在使用。

有了配置文件，就可以统一管理所有MCP服务器了！

创建配置文件 `.cmcp/mcp.json`（或 `~/.cmcp/mcp.json`）：

```json
{
  "mcpServers": {
    "local-server": {
      "command": "python",
      "args": ["server.py"],
      "env": {"API_KEY": "your-key"}
    },
    "remote-server": {
      "url": "http://localhost:3000/mcp",
      "headers": {"Authorization": "Bearer token"}
    }
  }
}
```

使用起来超级简单：

```bash
# 列出工具
cmcp :local-server tools/list

# 调用工具
cmcp :remote-server tools/call name=add arguments:='{"a": 1, "b": 2}'
```

只需要用 `:server-name` 就能引用预定义的服务器（及配置参数），大大提升效率！

## 兼容性

`mcp.json`配置格式与Cursor、Claude Code完全兼容，可以直接复用现有配置：

```bash
# 使用 Cursor 的配置
cmcp --config .cursor/mcp.json :my-server tools/list

# 使用 Claude Code 的配置
cmcp --config .mcp.json :my-server tools/list
```

## 快速开始

安装：
```bash
pip install cmcp
```

项目地址：https://github.com/RussellLuo/cmcp

欢迎大家体验 cMCP v0.4.0 的新功能！如果有任何问题或建议，欢迎在[GitHub仓库][1]中提出。


[1]: https://github.com/RussellLuo/cmcp
[2]: https://cursor.com/docs/context/mcp#using-mcpjson