categories:
- AI

tags:
- AI必知必会

title: AI必知必会：Function Calling
---

<style>
th {
  display: none;
}

th, tr, td {
  background-color: transparent !important;
}
</style>

从ChatGPT的横空出世，到OpenClaw的一夜爆火，AI技术的发展可谓日新月异。如果说LLM是最强大脑，那么赋予它手和脚，使其从对话框中走出来的，正是Function Calling。

[Function Calling][1]（函数调用）有时也称为[Tool Use][2]（工具使用）。按照OpenAI的官方定义，Function Calling为LLM提供了一种强大且灵活的方式，使其**能够与外部系统交互并获取训练数据之外的信息**。

要理解Function Calling的真正价值，我们需要先来了解其背后的应用场景。

## 应用场景

现实生活中，我们常常需要与各种系统和服务进行交互，以获取所需的信息或完成特定的任务。例如，查询天气、预订机票、支付账单、控制智能家居设备等。

以天气查询为例：

> What is the weather like in Chengdu?

为了处理这个任务，AI系统通常需要执行以下操作：
1. 理解用户的自然语言输入，并将其转化为结构化的指令或意图（这里的意图是“查询天气”，参数是“成都”）。
2. 根据指令调用相应的API或服务，得到结果（这里的结果可能包括温度、湿度等）。
3. 将结果加以整理和格式化，再以自然语言的形式返回给用户（例如，“今天成都的气温是22度，湿度为60%”）。

由此可见，这类AI系统的本质在于：

> 自然语言 → 结构化语义 → 触发系统动作

其中，从自然语言到结构化语义的转换，是整个流程的核心。

## NLU

在LLM出现之前，这类任务通常由传统的自然语言理解（Natural Language Understanding, NLU）来完成。作为NLP的一个子集，[NLU技术][3]主要包括意图识别（Intent Recognition）和槽位填充（Slot Filling）两个子任务。

上述天气查询的例子，经过NLU处理后，得到的结构化输出大致是这样的：

|   |   |   |   |   |   |   |   |   |
|---|---|---|---|---|---|---|---|---|
| **query** | What | is | the | weather | like | in | Chengdu | ? |
| **slots** | O    | O  | O   | O       | O    | O  | B-loc | O |
| **intent** | get_weather |    |    |    |    |    |    |    |

然而，NLU技术存在一些明显的局限性：
- 所有意图必须预定义（分类）
- 所有槽位必须事先建模（序列标注）
- 泛化能力差，新场景需要重新训练模型
- 多步推理能力几乎为0

## Prompt Engineering

LLM兴起以后，其强大的生成式语义推理、结构约束和泛化能力，完美地解决了NLU的诸多痛点。然而，早期的LLM并不具备Function Calling的能力（如[DeepSeek-R1][4]）。于是，人们主要通过Prompt Engineering（提示词工程）的方式，引导LLM生成符合预期的结构化数据。

例如，针对天气查询的例子，可以设计如下Prompt：

> You are an assistant that can perform actions based on user requests. Your responses should be in JSON format with the following structure:
>
> ```json
> {
>   "name": "action_name",
>   "arguments": {
>     "key1": "value1",
>     "key2": "value2"
>    }
> }
> ```
>
> Query: What is the weather like in Chengdu?

发给LLM后，就能得到如下JSON格式的文本输出：

```json
{
  "name": "get_weather",
  "arguments": {
    "location": "Chengdu"
  }
}
```

## Structured Output

上述方式虽然有效，但是稳定性不高。随着模型能力的演进，很多LLM开始原生地支持[JSON mode][5]，后来又进一步支持了[Structured Output][6]（结构化输出），生成结构化数据的能力得到了显著提升。

使用Structured Output，可以非常稳定地生成结构化数据。有些SDK（如OpenAI Python SDK），甚至还提供了与数据验证库（如Pydantic）的无缝集成，进一步增强了类型检查和数据验证的功能。例如：

```python
from openai import OpenAI
from pydantic import BaseModel, Field

client = OpenAI()

class Arguments(BaseModel):
    location: str

class Query(BaseModel):
    name: str = Field(..., description="Action to perform")
    arguments: Arguments = Field(..., description="Arguments for the action")

response = client.responses.parse(
    model="gpt-4o-2024-08-06",
    input=[
        {
            "role": "system",
            "content": "Extract the query information.",
        },
        {
            "role": "user",
            "content": "What is the weather like in Chengdu?",
        },
    ],
    text_format=Query,
)

print(response.output_parsed)

# Output:
# name='getWeather' arguments=Arguments(location='Chengdu')
```

## Structured Output vs Function Calling

事实上，在OpenAI的生态中，Function Calling（[于2023年6月推出][7]）先于Structured Output（[于2024年8月推出][8]）出现。

早期的Function Calling有时会“幻觉”出不符合格式的JSON，而Structured Output则可以确保输出严格遵循Schema。因此，Structured Output也可以看作是Function Calling能力的底层升级（[Strict mode][9]）。

从形式上来看，虽然Structured Output和Function Calling都会让LLM生成结构化的数据（通常是JSON），但它们解决的问题维度并不相同：

|   |   |   |
|---|---|---|
|             | **Structured Output** | **Function Calling** |
| **主要目的** | 严格保证每一条输出都符合格式 | 由LLM灵活决定是否调用工具、调用哪个工具 |
| **适用场景** | 数据提取、实体识别、表单生成等 | 智能体（Agent）、检索增强（RAG）等 |

## Function Calling

由上述分析可见，Function Calling的核心在于**由LLM灵活决定是否调用工具、调用哪个工具**。仍然以天气查询为例，如果我们将思维模式从“结构化输出”转变为“工具调用”，整体的处理逻辑就会截然不同。

<img alt="Function Calling" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/openai-function-calling-steps.png" width="500" height="800" />

如图所示，使用Function Calling来处理天气查询，整体的流程大致如下：
1. 向模型发送用户请求，并明确声明其可调用的工具列表（如`get_weather(location)`）。
2. 模型根据请求，决定需要调用的工具名称（如`get_weather`）及相应的参数（如`{"location": "chengdu"}`）。
3. 应用程序解析工具调用请求后，执行对应的代码，并获取结果（如`{"temperature": 14}`）。
4. 应用程序携带工具调用的结果，再次向模型发起请求。
5. 模型据此生成最终的回复（如`It's currently 14°C in Chengdu.`），或者再次调用其他工具。

对应于上述流程，下面给出一个可运行的Python示例：

```python
import json
from openai import OpenAI

client = OpenAI()

# 1. Define a list of callable tools for the model
# (Note that `parameters` are defined in JSON Schema)
tools = [
    {
        "type": "function",
        "name": "get_weather",
        "description": "Retrieves current weather for the given location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City e.g. Beijng, Chegndu"
                }
            },
            "required": ["location"],
            "additionalProperties": False
        },
        "strict": True
    },
]

def get_weather(location: str) -> str:
    # Here you would normally make an API call to a weather service
    return '{"temperature": 14}'

# Create a running input list we will add to over time
input_list = [
    {"role": "user", "content": "What is the weather like in Chengdu?"},
]

# 2. Prompt the model with tools defined
response = client.responses.create(
    model="gpt-5",
    tools=tools,
    input=input_list,
)

# Save function call outputs for subsequent requests
input_list += response.output

for item in response.output:
    if item.type == "function_call":
        if item.name == "get_weather":
            # 3. Execute the function logic for `get_weather`
            location = json.loads(item.arguments)["location"]
            output = get_weather(location)
            
            # 4. Provide function call results to the model
            input_list.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": output,
            })

response = client.responses.create(
    model="gpt-5",
    instructions="You are a helpful assistant.",
    tools=tools,
    input=input_list,
)

# 5. The model should be able to give a response!
print(response.output_text)

# Output:
# The current temperature in Chengdu is about 14°C.
```

## 框架封装

至此，我们已了解了Function Calling的基本原理与使用方式。但在实际应用中，若每个工具都需要手动编写JSON Schema，其开发复杂度势必大幅增加。因此，众多开发框架对此进行了封装，以提供更高层次的抽象。

例如，使用[LangChain][10]提供的`@tool`装饰器，便能轻松地将Python函数注册为LLM可调用的工具：

```python
from langchain.chat_models import init_chat_model
from langchain.tools import tool

model = init_chat_model("gpt-5")

@tool
def get_weather(location: str) -> str:
    """Retrieves current weather for the given location."""
    return f"It's sunny in {location}."

# 1. Bind (potentially multiple) tools to the model
model_with_tools = model.bind_tools([get_weather])

# 2. Model generates tool calls
messages = [{"role": "user", "content": "What's the weather like in Chengdu?"}]
ai_msg = model_with_tools.invoke(messages)
messages.append(ai_msg)

for tool_call in ai_msg.tool_calls:
    # 3. Execute the tool with the generated arguments
    tool_result = get_weather.invoke(tool_call)
    # 4. Pass results back to model
    messages.append(tool_result)

# 5. Model generates the final response
final_response = model_with_tools.invoke(messages)
print(final_response.text)

# Output:
# It's sunny in Chengdu right now.
```

如今，Agent已成为主流，上述工具执行循环（Tool Execution Loop）也演进为ReAct Agent的核心范式。为此，很多框架进一步对整个Agent模式进行了抽象，从而将Function Calling的复杂性封装在高层API之下，大幅降低了开发门槛。

例如，借助LangChain提供的`create_agent`函数，只需寥寥数行代码，就能构建出一个完整的天气查询Agent：

```python
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool

model = init_chat_model("gpt-5")

@tool
def get_weather(location: str) -> str:
    """Retrieves current weather for the given location."""
    return f"It's sunny in {location}."

agent = create_agent(model, tools=[get_weather])
result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather like in Chengdu?"}]}
)
print(result["messages"][-1].content)

# Output:
# It’s sunny in Chengdu right now.
```

## 结语

本文从实际应用出发，梳理了从传统NLU到Prompt Engineering，再到Structured Output和Function Calling的技术演进脉络，并对比了后两者的功能定位差异。同时，介绍了如何使用框架来简化Function Calling的开发流程。

在Claude Code、OpenClaw等智能体日益普及的当下，Function Calling作为LLM的核心能力，已成为驱动这些Agent的重要技术基石。随着这项技术的广泛应用，工具生态的开放性与标准化也愈发关键。在此趋势下，MCP（模型上下文协议）已逐渐成为行业的事实标准，我们将在后续的文章中继续探讨这一话题。


[1]: https://platform.openai.com/docs/guides/function-calling
[2]: https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
[3]: https://arxiv.org/abs/2101.08091
[4]: https://github.com/deepseek-ai/DeepSeek-R1/issues/9#issuecomment-2604747754
[5]: https://platform.openai.com/docs/guides/structured-outputs#json-mode
[6]: https://platform.openai.com/docs/guides/structured-outputs
[7]: https://openai.com/index/function-calling-and-other-api-updates/
[8]: https://openai.com/index/introducing-structured-outputs-in-the-api/
[9]: https://platform.openai.com/docs/guides/function-calling#strict-mode
[10]: https://docs.langchain.com/oss/python/langchain/models#tool-calling