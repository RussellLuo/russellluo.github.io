categories:
- AI

tags:
- Claude Code

title: 揭秘Claude Code：自主式编程
---

> Learn about Claude Code, Anthropic's agentic coding tool that lives in your terminal and helps you turn ideas into code faster than ever before.

Claude Code在[官方文档][1]中自称是一款Agentic（自主式，或智能体驱动）编程工具，它能够帮助开发者更高效地将想法转化为代码。那么，何为自主式编程？其背后的核心原理与技术实现又是怎样的？本文将围绕这一主题展开讨论，深入剖析Claude Code的技术架构与独到之处。

## 什么是自主式编程？

与传统基于静态提示词的单步代码生成工具不同，自主式编程系统以**目标驱动、多步执行**为核心特征。这些由大语言模型（LLM）驱动的系统能够自主执行软件开发任务，通过推理、决策、使用外部工具（如编译器、调试器、测试运行器）并基于反馈迭代优化输出结果。

[自主式编程系统][2]通常具有以下显著特点：

- **高度自主性**：能够在没有持续人工监督的情况下自主决策和执行操作
- **环境交互性**：在执行过程中与外部工具和环境进行动态交互
- **迭代优化能力**：基于中间反馈不断改进输出质量
- **目标导向性**：追求高层次的任务目标，而非仅仅对一次性指令进行响应

自主式编程代表了软件开发自动化的重要转变，从基于规则的自动化、传统机器学习模型或单次LLM调用，转向真正参与软件开发全过程的智能系统。这一变革为智能代码辅助、自主调试测试、自动化代码维护甚至自我进化的软件系统开辟了全新可能性。

## Claude Code的核心架构

![Claude Code自主式编程架构](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-agentic-coding-architecture.png)

如图所示，Claude Code作为典型的自主式编程工具，其核心架构包含以下几个关键组件：

- **自主执行循环**：Claude Code将大语言模型嵌入到一个执行循环中，使其能够与开发环境进行持续交互。当接收到用户的自然语言提示后，系统会从操作系统和工作区收集额外上下文信息（如文件摘要、环境状态等）。

- **多步推理机制**：在推理循环中，大语言模型会将复杂任务分解为多个子目标，生成代码或做出决策，并判断是否需要调用外部工具——包括文件读写、终端命令执行等操作。

- **迭代优化过程**：工具执行的结果会返回至循环中，作为进一步优化的反馈。这个迭代过程持续进行，直到自主系统完成任务或达到停止条件，最终结果将实时返回给用户。

## 案例分析：你好，世界！

为了更好地理解Claude Code的核心架构，让我们通过一个实际案例来观察其工作流程。

简单起见，我们来创建一个Python版的Hello World函数：

![Hello World：输入提示词](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-helloworld-prompt.png)

![Hello World：生成代码](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-helloworld-generation.png)

![Hello World：写入文件](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/files/claude-code-helloworld-writefile.png)

从上述执行过程中，借助[mitmproxy][3]可以捕获到两条数据流：

```
================================================================================
FLOW #1 - ID: 6a662989-33d0-4e86-a984-8c39f90ed9e7
================================================================================

📤 REQUEST:
----------------------------------------
System:
  System[0]:
    type: text
    text: You are Claude Code, Anthropic's official CLI for Claude.
    cache_control: {'type': 'ephemeral'}
  System[1]:
    type: text
    text: 
You are an interactive CLI tool that helps users with software engineering tasks. Use the instructions below and the tools available to you to assist the user.

...

Messages:
  Message[0]:
    role: user
    content:
      Content[0]:
        type: text
        text:
          <system-reminder>
          This is a reminder that your todo list is currently empty. DO NOT mention this to the user explicitly because they are already aware. If you are working on tasks that would benefit from a todo list please use the TodoWrite tool to create one. If not, please feel free to ignore. Again do not mention this message to the user.
          </system-reminder>
      Content[1]:
        type: text
        text:
          <system-reminder>
          As you answer the user's questions, you can use the following context:
          # important-instruction-reminders
          Do what has been asked; nothing more, nothing less.
          NEVER create files unless they're absolutely necessary for achieving your goal.
          ALWAYS prefer editing an existing file to creating a new one.
          NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
          
                
                IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.
          </system-reminder>
          
      Content[2]:
        type: text
        cache_control: {'type': 'ephemeral'}
        text:
          create a hello world function in python
Tools:
...

  Tool[8]:
    Name: Write
    Description: Writes a file to the local filesystem.

Usage:
- This tool will overwrite the existing file if there is one at the provided path.
- If this is an existing file, you MUST use the Read tool first to read the file's contents. This tool will fail if you did not read the file first.
- ALWAYS prefer editing existing files in the codebase. NEVER write new files unless explicitly required.
- NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
- Only use emojis if the user explicitly requests it. Avoid writing emojis to files unless asked.
    Input Schema:
      Type: object
      Required: file_path, content
      Properties: file_path, content

...

📥 RESPONSE:
----------------------------------------
📡 Parsed SSE Response:
  Tool: Write (ID: toolu_bdrk_01Tv5P8iPpKfvXkD7jGmjLFr) - {"file_path": "/Users/russellluo/Projects/demo/hello_world.py", "content": "def hello_world():\n    print(\"Hello, World!\")\n\nif __name__ == \"__main__\":\n    hello_world()"}

================================================================================
```

```
================================================================================
FLOW #2 - ID: 5b84e626-298d-4f35-a4c2-d22b1c0ab1ab
================================================================================

📤 REQUEST:
----------------------------------------
System:
...

Messages:
  Message[0]:
    role: user
    content:
      Content[0]:
        type: text
        text:
          <system-reminder>
          This is a reminder that your todo list is currently empty. DO NOT mention this to the user explicitly because they are already aware. If you are working on tasks that would benefit
 from a todo list please use the TodoWrite tool to create one. If not, please feel free to ignore. Again do not mention this message to the user.
          </system-reminder>
      Content Item 2:
        type: text
        text (expanded):
          <system-reminder>
          As you answer the user's questions, you can use the following context:
          # important-instruction-reminders
          Do what has been asked; nothing more, nothing less.
          NEVER create files unless they're absolutely necessary for achieving your goal.
          ALWAYS prefer editing an existing file to creating a new one.
          NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
          
                
                IMPORTANT: this context may or may not be relevant to your tasks. You should not respond to this context unless it is highly relevant to your task.
          </system-reminder>
          
      Content[1]:
        type: text
        text:
          create a hello world function in python
  Message[1]:
    role: assistant
    content:
      Content[0]:
        type: text
        text:
          (no content)
      Content[1]:
        type: tool_use
        id: toolu_bdrk_01Tv5P8iPpKfvXkD7jGmjLFr
        name: Write
        input: {'file_path': '/Users/russellluo/Projects/demo/hello_world.py', 'content': 'def hello_world():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    hello_world()'}
        cache_control: {'type': 'ephemeral'}
  Message[2]:
    role: user
    content:
      Content[0]:
        tool_use_id: toolu_bdrk_01Tv5P8iPpKfvXkD7jGmjLFr
        type: tool_result
        content: File created successfully at: /Users/russellluo/Projects/demo/hello_world.py
        cache_control: {'type': 'ephemeral'}
Tools:
...

📥 RESPONSE:
----------------------------------------
📡 Parsed SSE Response:
  Created `hello_world.py` with a simple hello world function.

================================================================================
```

从数据流中可以看出，Claude Code处理“创建Hello World函数”这种简单任务，背后也是一个典型的多步、交互式的自主执行循环。其特点总结如下：

1.  **清晰的“思考-行动-观察”循环**
    - **思考与行动（FLOW #1）**：这是循环的起点。LLM接收系统上下文和用户指令（`create a hello world function in python`）后，经过内部推理，**决定采取行动**——使用`Write`工具，它生成了完整的代码内容并指定了文件路径。
    - **观察与完成（FLOW #2）**：这是循环的下一步。经用户确认后，`Write`工具被执行，系统于是接收到了执行结果（`File created successfully at...`）。LLM“观察”到这个反馈后，判定任务已成功完成，于是**决定结束循环**，并生成最终响应给用户（`Created 'hello_world.py' with a simple hello world function.`）。

2.  **工具使用的链式依赖**
    整个任务的完成依赖于工具的链式调用和结果传递：

    - **`tool_use` (FLOW #1 响应中)**：LLM发起一个工具调用 (`Write`)。
    - **`tool_result` (FLOW #2 请求中)**：环境执行工具后返回结果，并作为新的上下文输入给LLM。

    这表明自主系统的每一步决策都依赖于上一步执行后的环境状态，形成了一个闭环反馈。

3.  **状态保持与会话连续性**
    - FLOW #2 的请求中包含了完整的对话历史（`Messages[0], [1], [2]`），其中包括最初的用户指令、LLM发起的工具调用以及工具执行的结果。
    - 这保证了LLM在每一步都有完整的上下文，能够理解当前任务所处的状态，从而做出连贯的决策。`tool_use_id`等字段确保了工具调用和结果之间的正确关联。

上述流程其实也是一个LLM工具使用的标准范式，感兴趣的读者可以参考[Tool use with Claude][4]。

## 轻量级原型实现

通过前面的分析，我们已经深入了解了Claude Code的自主式编程原理。现在，让我们利用[Anthropic Python SDK][5]，构建一个轻量级的自主编程助手原型，将理论转化为实践。

下面的实现包含了简化的自主循环和`Write`工具，展示了如何让LLM突破纯文本生成的限制，真正与环境进行交互：

````python
# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-4"

# System prompt for Claude Code
SYSTEM = [
    {
        "type": "text",
        "text": "You are Claude Code, Anthropic's official CLI for Claude.",
    },
    {
        "type": "text",
        "text": f"""
You are an interactive CLI tool that helps users with software engineering tasks. Use the instructions below and the tools available to you to assist the user.

Here is useful information about the environment you are running in:
<env>
Working directory: {CWD}
</env>
""",
    },
]

# Write tool definition
WRITE_TOOL = {
    "name": "Write",
    "description": "Writes a file to the local filesystem.",
    "input_schema": {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "The absolute path to the file to write (must be absolute, not relative)",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file",
            },
        },
        "required": ["file_path", "content"],
        "additionalProperties": False,
    },
}

def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Execute tool function with user confirmation"""
    if tool_name.lower() != "write":
        return f"Error: Unknown tool `{tool_name}`"

    # User confirmation
    while True:
        file_name = os.path.basename(tool_input["file_path"])
        confirmation = (
            input(f"""
```
{tool_input["content"]}
```
Do you want to create `{file_name}`? (Y/N) > """)
            .strip()
            .lower()
        )
        if confirmation == "y":
            return write_file(tool_input["file_path"], tool_input["content"])
        else:
            return f"User rejected write to `{file_name}`"

def write_file(file_path: str, content: str) -> str:
    """Write content to a file at the specified path"""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File created successfully at: {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def run_agent_in_loop(messages: list[dict], max_turns: int = 5) -> None:
    """Run the coding agent in a loop"""
    for turn in range(max_turns):
        # Call Claude
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM,
            tools=[WRITE_TOOL],
            messages=messages,
        )

        response_content = response.content[0]

        # Text response - task completed
        if response_content.type == "text":
            print(f"\n⏺ {response_content.text}")
            break

        # Tool call
        elif response_content.type == "tool_use":
            tool_use = response_content

            # Execute tool
            tool_result = execute_tool(tool_use.name, tool_use.input)

            # Update message history
            messages.extend(
                [
                    {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": tool_use.id,
                                "name": tool_use.name,
                                "input": tool_use.input,
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": tool_result,
                            }
                        ],
                    },
                ]
            )
````

安装相关依赖，并设置API密钥：

```bash
pip install anthropic
export ANTHROPIC_API_KEY=<your_api_key>
```

运行上述代码`lite_claude_code_v1.py`（[完整版][6]），输入指令`create a hello world function in python`，即可看到类似Claude Code的交互式执行过程：

````bash
$ python lite_claude_code_v1.py 
==================================================
🤖 Lite Claude Code (^C to exit)
==================================================

> create a hello world function in python

```
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
```
Do you want to create `hello_world.py`? (Y/N) > y

⏺ I've created a simple Python file with a "Hello, World!" function.
...

> 
````

至此，我们成功地构建了一个轻量级的Claude Code，并让它完成了一个基本的编程任务！感兴趣的读者可以进一步扩展这个原型，例如添加更多的工具（如`Read`、`Bash`等），以增强其功能和实用性。

## 结语

通过本文的探索，我们剖析了Claude Code作为自主式编程工具的核心架构，揭示了其“目标驱动、多步执行”的工作原理。从简单的Hello World案例到背后的数据流分析，我们见证了其如何通过思考-行动-观察的自主循环，打通从自然语言指令到实际代码生成的完整路径。

此外，我们还构建了一个轻量级的自主编程助手原型，展示了如何利用Anthropic SDK，将复杂的交互逻辑简化为可执行的Python代码。这一过程不仅能加深我们对自主式编程的理解，也为未来开发自己的AI辅助工具奠定了基础。


[1]: https://docs.anthropic.com/en/docs/claude-code/overview
[2]: https://arxiv.org/html/2508.11126v1#S2
[3]: https://russellluo.com/2025/09/demystifying-claude-code-mitmproxy
[4]: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview
[5]: https://docs.anthropic.com/en/api/client-sdks#python
[6]: https://github.com/RussellLuo/russellluo.github.io/blob/main/source/_posts/2025/code/lite_claude_code_v1.py