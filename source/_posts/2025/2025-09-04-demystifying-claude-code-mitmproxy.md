categories:
- AI

tags:
- Claude Code

title: 揭秘Claude Code：网络分析利器mitmproxy
---

当使用Claude Code这样的AI编程助手，在惊叹于它神奇能力的同时，你是否也曾好奇：它究竟是如何工作的？作为一款AI应用，Claude Code的魔法隐藏在它与大型语言模型（LLM）的每一次对话中。但遗憾的是，Claude Code是闭源软件，我们无法从源代码中寻找答案。

那么，如何才能揭开它的神秘面纱呢？突破口就藏在网络通信中！通过抓取和分析Claude Code与后端服务的网络流量，我们可以从中洞悉它的核心工作机制。今天，就让我们借助mitmproxy这个强大工具，开启这段技术探索之旅。

## 为什么需要网络分析？

在AI应用领域，提示词工程堪称核心机密。Claude Code的出色表现，既得益于Claude模型本身强大的能力，也离不开其精心设计的提示词模板和与LLM的交互策略。通过网络流量分析，我们可以：

- 还原系统提示词（System Prompt）的设计
- 分析不同任务对应的用户提示词（User Prompt）
- 探索Agent的内部工具调用（Tools）
- 研究上下文管理机制（Context Management）
- 了解模型参数的配置细节和优化策略

这种“逆向工程”不仅能满足技术好奇心，更能为我们的AI应用开发提供宝贵参考。

## mitmproxy：网络分析的瑞士军刀

[mitmproxy][1]是一个免费、开源的交互式HTTPS代理，可以用于拦截、检查、修改和重放网络流量。它提供了三个命令行/控制台工具：
1. **mitmproxy**：一个基于ncurses的交互式工具，提供了一个带有快捷键的终端界面，允许用户实时查看和操作流量。这是最强大的交互模式。
2. **mitmdump**：一个类似于tcpdump的命令行工具，不提供交互式界面，而是将捕获的流量直接输出到控制台或保存到文件。它非常适合与其它命令行工具（如grep，jq）结合使用，进行自动化日志记录和批量处理。
3. **mitmweb**：一个基于Web的图形化界面，在浏览器中提供一个类似开发者工具的界面，对于不习惯命令行操作的用户来说更加友好。

对于Python开发者而言，安装mitmproxy只需一行命令（查看[其他安装方式][2]）：

```bash
uvx mitmproxy
# or `pip install mitmproxy`
```

由于现代应用普遍使用HTTPS，我们还需要安装[CA证书][3]:：

```bash
mitmproxy
```

运行后访问[mitm.it](http://mitm.it/)，下载并安装对应系统的证书即可。

## Claude Code流量初探

为了演示更直观，我们这里启动mitmweb：

```bash
mitmweb
```

mitmproxy默认监听8080端口（可以通过`-p`参数指定其他端口），因此需要将系统代理设置为该地址：

```bash
export http_proxy=http://127.0.0.1:8080
export https_proxy=http://127.0.0.1:8080
```

随后，我们可以选择一个项目，打开Claude Code并输入`hi`：

![claude-code-input-hi](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-input-hi.png)

如果一切顺利，mitmweb将会捕获到相关的网络流量：

![claude-code-hi-flows-request](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-hi-flows-request.png)

![claude-code-hi-flows-response](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-hi-flows-response.png)

至此，我们成功完成了对Claude Code的首次流量捕获！可以看到，这些流量包含了Claude Code与后端服务之间完整的HTTP请求和响应。在每一条数据流中，请求体包含了与提示词相关的输入信息，而响应体则包含了LLM生成的回答内容。

虽然请求和响应数据已被捕获，不过仔细观察我们会发现：
1. 请求中的JSON数据内容较多，我们主要想分析与提示词有关的内容，如`system`、`messages`和`tools`等字段。
1. 请求中的提示词往往是多行文本，都被显示在同一行，导致信息冗长且难以阅读。
2. 响应中的SSE（Server-Sent Events）数据是以流的形式返回，导致它们被拆分成了多个片段，需要重新拼接起来。

为了解决上述几个问题，我们需要进一步使用mitmproxy的插件机制，来对流量进行定制化的捕获和解析。

## mitmproxy插件机制

mitmproxy的[插件机制][4]基于事件驱动，其核心原理是：mitmproxy在代理流量的生命周期中，会在特定时刻（如收到请求、收到响应、发生错误等）触发预设好的事件。

开发者编写的插件（称为addon）实际上就是一个事件监听器。你通过创建一个类，并定义对应的事件处理方法（如`request(self, flow)`、`response(self, flow)`），mitmproxy就会在相应事件发生时自动调用你的方法。

在这个方法内部，你可以通过操作`flow`对象（它包含了单个HTTP请求/响应的所有信息）来：
1.  **查看（Inspect）**：读取URL、头、内容等。
2.  **过滤（Filter）**：只处理你关心的特定流量。
3.  **修改（Modify）**：改变请求或响应的内容。
4.  **输出（Output）**：将信息打印到控制台或保存到文件。

这种机制让你能以非侵入的方式，对经过代理的流量进行精确的解析和处理。对编写插件感兴趣的读者，可以参考[官方示例][5]了解更多详情。

## Claude Code流量的定制化分析

接下来，我们将借助mitmproxy的插件机制，对Claude Code的流量进行优化分析。

为了兼顾数据捕获的完整性和不同用户对格式化的个性化需求，我们将整个分析流程设计为两个独立的阶段：

1. **流量记录**：捕获所有HTTP请求和响应，并以JSON Lines格式逐行输出，确保数据的完整性，同时便于后续的逐行分析。
2. **格式化输出**：逐行解析流量记录，从JSON请求中提取`system`、`messages`和`tools`等核心字段，并以结构化的方式展示；同时将SSE响应数据流还原为完整的JSON对象，并格式化输出以提升可读性。

最有趣的是，在AI编程时代，我们甚至无需翻阅mitmproxy文档或手动编写代码——Claude Code就能帮我们完成大部分工作。

### 流量记录

首先，从官网下载示例[io-write-flow-file.py](https://docs.mitmproxy.org/stable/addons/examples/#io-write-flow-file)。然后，打开Claude Code，让它参考示例生成mitmproxy插件：

> 参考io-write-flow-file.py，编写一个mitmproxy脚本，用于将请求/响应对写入一行JSON Line

![claude-code-jsonl-writer-prompt](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-jsonl-writer-prompt.png)

生成后的`jsonl-writer.py`插件（[完整版](https://gist.github.com/RussellLuo/799ccc0164bcb485d4c94a15973dab8a#file-mitmproxy_jsonl_writer-py)）可以这样使用：

```bash
mitmweb -s jsonl-writer.py
```

运行后，所有捕获到的流量都会被记录到`flows.jsonl`文件中：

```bash
tail -f flows.jsonl
```

### 格式化输出

同样地，可以让Claude Code生成一个`jsonl-viewer.py`脚本，用于解析`flows.jsonl`文件中的每一行，并对其进行格式化输出：

> 编写一个解析脚本jsonl-viewer.py，可以逐行解析标准输入中的jsonl内容，每一行JSON Line格式如下：
>
> ```
{"request":{"model":"claude-3-5-haiku-20241022","max_tokens":512,"messages":[{"role":"user","content":"Please write a 5-10 word title for the following conversation:\n\n[Last 12 of 14 messages]\n\nUser: \n\nClaude: (no content)\n\nUser: \n\nClaude: (no content)\n\nUser: \n\nClaude: (no content)\n\nUser: \n\nClaude: I've created a mitmproxy addon `json_logger.py` that meets your requirements:\n\n## Key Features:\n\n1. **Request Body Filtering**: For JSON requests, only keeps `system`, `messages`, and `tools` fields\n2. **SSE Response Handling**: Parses Server-Sent Events and concatenates chunks into a structured format\n3. **JSON Lines Output**: Writes each request/response pair as a single JSON line to `requests_responses.jsonl`\n\n## Usage:\n\n```bash\n# Run with mitmproxy\nmitmdump -s json_logger.py\n\n# Or with mitmweb\nmitmweb -s json_logger.py\n```\n\nThe addon captures:\n- URL, HTTP method, and status code\n- Filtered request body (JSON fields: system, messages, tools)\n- Parsed response body (with special SSE chunk concatenation)\n- Content type information\n\nFor SSE responses, it extracts individual chunks and provides both the raw chunks array and concatenated content, making it easy to reconstruct streaming responses.\n\nRespond with the title for the conversation and nothing else."}],"system":[{"type":"text","text":"Summarize this coding conversation in under 50 characters.\nCapture the main task, key files, problems addressed, and current status.","cache_control":{"type":"ephemeral"}}],"temperature":0,"metadata":{"user_id":"user_f3bbbca5b09b9b5ebf3916e21fd50d585787d9b818164f839f3f9b9b4f58bfe2_account__session_08316681-f6ac-4fcb-80c6-142f1e956373"},"stream":true},"response":"event: message_start\ndata: {\"type\": \"message_start\", \"message\": {\"id\": \"msg_2d398cea-df7d-4792-8017-69fd8383b883\", \"type\": \"message\", \"role\": \"assistant\", \"content\": [], \"model\": \"anthropic/claude-3.5-haiku-20241022\", \"stop_reason\": null, \"stop_sequence\": null, \"usage\": {\"input_tokens\": 0, \"output_tokens\": 0}}}\n\nevent: content_block_start\ndata: {\"type\": \"content_block_start\", \"index\": 0, \"content_block\": {\"type\": \"text\", \"text\": \"\"}}\n\nevent: content_block_delta\ndata: {\"type\": \"content_block_delta\", \"index\": 0, \"delta\": {\"type\": \"text_delta\", \"text\": \"M\"}}\n\nevent: content_block_delta\ndata: {\"type\": \"content_block_delta\", \"index\": 0, \"delta\": {\"type\": \"text_delta\", \"text\": \"itmproxy JSON\"}}\n\nevent: content_block_delta\ndata: {\"type\": \"content_block_delta\", \"index\": 0, \"delta\": {\"type\": \"text_delta\", \"text\": \" Logger for\"}}\n\nevent: content_block_delta\ndata: {\"type\": \"content_block_delta\", \"index\": 0, \"delta\": {\"type\": \"text_delta\", \"text\": \" API\"}}\n\nevent: content_block_delta\ndata: {\"type\": \"content_block_delta\", \"index\": 0, \"delta\": {\"type\": \"text_delta\", \"text\": \" Request\"}}\n\nevent: content_block_delta\ndata: {\"type\": \"content_block_delta\", \"index\": 0, \"delta\": {\"type\": \"text_delta\", \"text\": \"/Response Tracking\"}}\n\nevent: content_block_stop\ndata: {\"type\": \"content_block_stop\", \"index\": 0}\n\nevent: message_delta\ndata: {\"type\": \"message_delta\", \"delta\": {\"stop_reason\": \"end_turn\"}, \"usage\": {\"input_tokens\": 284, \"output_tokens\": 11}}\n\nevent: message_stop\ndata: {\"type\": \"message_stop\"}\n\n","flow_id":"75bbd359-8b0c-42ef-a376-fbd4c4660693","duration":2.0904617309570312}
```
>
> 解析要求：
> - 针对request数据，只提取system、messages和tools的内容，相关text和content字段包含多行文本，需要格式化输出
> - 针对response数据，需要将sse拼接成完整的json对象，然后其中的text字段包含多行文本，也需要格式化输出

![claude-code-jsonl-viewer-prompt](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-jsonl-viewer-prompt.png)

生成后的`jsonl-viewer.py`脚本（[完整版](https://gist.github.com/RussellLuo/799ccc0164bcb485d4c94a15973dab8a#file-mitmproxy_jsonl_viewer-py)）可以用于解析`flows.jsonl`文件：

```bash
cat flows.jsonl | python jsonl-viewer.py | less
```

解析后的输出结果如下：

![claude-code-jsonl-viewer-output](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-jsonl-viewer-output.png)

与原始的mitmweb界面相比，经过处理后的数据可读性有了显著提升：
- 每条HTTP数据流独立呈现，请求和响应内容清晰分离
- 提示词内容以整洁的多行文本格式展示，便于直观理解发送给LLM的具体指令
- 响应中的SSE数据流被拼接为完整内容，更易于阅读

通过这种结构化的展示方式，每次AI对话的完整流程都变得清晰可追溯，大大提升了分析和调试的效率。

## 结语

通过本文的探索，我们见证了mitmproxy在流量捕获、插件定制与数据解析方面的卓越能力。同时结合Claude Code的AI辅助，我们可以高效编写和调试mitmproxy插件，为揭秘Claude Code自身的工作原理提供了强大的助力。

魔法的大门已然打开，而深处仍有更多奥秘。从提示词构造、Agent工具调用到上下文管理，Claude Code的核心机制，正静候每一位探索者的到来。


[1]: https://www.mitmproxy.org/
[2]: https://docs.mitmproxy.org/stable/overview/installation/
[3]: https://docs.mitmproxy.org/stable/concepts/certificates/
[4]: https://docs.mitmproxy.org/stable/addons/overview/
[5]: https://docs.mitmproxy.org/stable/addons/examples/