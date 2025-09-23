categories:
- AI

tags:
- Claude Code

title: Claude Code伴侣：可视化管理新体验
---

## 引言

Claude Code伴侣（即[Claude Code Mate][1]，以下简称CCM）最初的定位是一个极简的LLM代理工具，旨在帮助开发者快速用上Claude Code和切换各种大模型。所以CCM一开始选择了纯命令行交互，以及通过YAML文件进行配置。这种方式既简洁高效，也符合开发者的使用习惯。

距离CCM第一版发布（[轻松解锁Claude Code：国内用户的多元模型新玩法][2]）已经过去了近一个月，随着自己使用的增多，以及零星收到的一些用户反馈，我发现CCM存在以下问题：

1. **模型管理不直观**：用户如果不查阅[LiteLLM文档][3]，很难知道CCM支持哪些模型，以及如何配置这些模型（比如OpenAI兼容的模型，需要加上`openai/`前缀）。
2. **没有用量统计**：用户在CCM中无法查看自己的用量情况，包括各个模型的请求数、输入/输出Token数和费用消耗等信息。

为了解决这些问题，我决定为CCM引入一个可视化管理后台，以提升用户体验。

## PostgreSQL小插曲

了解LiteLLM的朋友可能知道，LiteLLM Proxy其实原本就提供[Admin UI][4]。然而，它对数据库的选择有特定偏好：仅支持PostgreSQL，并且明确表示[不考虑SQLite等其他轻量级选项][5]。

这意味着，如果要启用Admin UI，用户必须要先安装和配置PostgreSQL。这显然与CCM的初衷——提供一个简单易用的工具——是相违背的。

幸运的是，经过一番调研，我找到了一个Python库[pgserver][6]，可以实现：

- **可嵌入**：通过pip安装依赖库，即可自动下载PostgreSQL
- **零配置**：无需用户手动设置数据库环境
- **跨平台**：支持Windows、macOS和Linux
- **无Docker**：不需要额外安装和配置Docker

于是在pgserver的帮助下，CCM成功引入了Admin UI，并做到了用户无感。

## 快速开始

为了保持轻量级，CCM默认不包含UI功能。如果要启用UI功能，可以通过以下命令安装：

```bash
# 使用uv（推荐）
uv pip install --system --python 3.12 "claude-code-mate[ui]"
# 或者使用pip
pip install "claude-code-mate[ui]"
```

安装后，使用以下命令启动UI：

```bash
ccm ui
```

打开Admin UI后，使用默认的用户名和密码（`admin`和`sk-1234567890`）登录，即可进入管理后台。

## 可视化管理后台

LiteLLM Proxy提供的Admin UI功能很强大，其中就包括CCM第一版缺失的模型管理和用量统计功能。

### 模型管理

![模型管理界面](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/images/litellm-admin-ui-models.png)

LiteLLM内置支持众多提供商的模型，包括但不限于：

- 知名官方模型（如Anthropic、OpenAI和DeepSeek等）
- 聚合平台的模型（如OpenRouter等）
- OpenAI兼容模型
- Ollama本地模型

用户可以通过界面：

- 轻松添加、编辑和删除模型，无需了解LiteLLM的特殊前缀规则。
- 设置输入/输出的Token价格，以便准确计算费用。
- 修改一些高级参数，如TPM/RPM、超时时间和max_tokens等。

### 用量统计

![用量统计界面](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/images/litellm-admin-ui-usage.png)

通过用量统计功能，用户可以清晰地看到：

- 总（或按模型）的请求次数，以及成功和失败的次数。
- 总（或按模型）的Token数量，以及输入和输出的Token数量。
- 总（或按模型）的费用消耗情况等。

### 其他功能

除了上述两个功能外，Admin UI还提供了以下一些实用功能：

- **模型测试（Test Key）**：快速测试模型的可用性和效果。
- **日志查看（Logs）**：实时查看请求日志，便于调试和排查问题。

![模型测试界面](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/images/litellm-admin-ui-test-key.png)

![日志界面](https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2025/images/litellm-admin-ui-logs.png)

以上只列举了Admin UI的部分功能，对于其他功能感兴趣的读者，可以进一步参考[LiteLLM Proxy文档][4]。

## 结语

欢迎大家体验Claude Code Mate的新UI功能！需要说明的是，该功能只在macOS（我的开发环境）进行了测试，尚未在Windows和Linux上进行全面验证。如果你有任何问题或建议，欢迎随时在[GitHub仓库][1]中提出。


[1]: https://github.com/RussellLuo/claude-code-mate
[2]: https://russellluo.com/2025/08/easily-unlock-claude-code
[3]: https://docs.litellm.ai/docs/providers
[4]: https://docs.litellm.ai/docs/proxy/ui
[5]: https://github.com/BerriAI/litellm/issues/4583
[6]: https://github.com/orm011/pgserver