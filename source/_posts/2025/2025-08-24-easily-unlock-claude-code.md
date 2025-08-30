categories:
- 技术

tags:
- AI

title: 轻松解锁Claude Code：国内用户的多元模型新玩法
---

如果你对AI编程助手感兴趣，一定听说过[Claude Code][1]。遗憾的是，由于网络环境和账号限制，国内用户直接使用它非常困难。目前比较流行的方案是借助[Claude Code Router][2]，但经过笔者测试，配置并成功用起来仍有一定门槛。

作为Vibe Coding玩家，笔者尝试实现了一个简易版本的替代方案 —— [Claude Code Mate][3]，不仅能让你用上Claude Code，还能自由切换其他主流大模型。

有意思的是，Claude Code Mate项目本身的大部分代码，也是Vibe Coding的产物（由Claude Code生成）。

## Claude Code Mate

项目地址：https://github.com/RussellLuo/claude-code-mate

Claude Code Mate（以下简称CCM）是一个专门为Claude Code设计的辅助工具，通过内置的[LiteLLM Proxy][4]，让你可以灵活接入多种大模型。它的最大特点是安装便捷、配置简单，适合不想折腾的开发者用户。

## CCM能做什么

1.  无障碍使用Claude Code

    无需直接注册Anthropic账号，只需配置一个第三方API Key（例如通过OpenRouter平台获取），即可在国内网络环境下稳定使用Claude Code。

2.  一键切换多种模型

    除了Claude系列模型，你还可以方便地切换到Gemini、DeepSeek、GPT等其他大模型。只需在配置文件中简单设置，就能按需选用不同模型。

3.  比同类方案更便捷

    其他流行方案如Claude Code Router（CCR）也能实现类似功能，但由于CCR有Router（路由器）和Transformer（转换器）等功能，导致理解和配置较复杂。相比之下，CCM只聚焦于切换不同的模型和提供商，并将所有功能打包成一条命令，安装后简单设置就能使用。

## 快速开始

以OpenRouter为例，只需几步即可完成：

```bash
pip install claude-code-mate

# 启动LiteLLM Proxy
export OPENROUTER_API_KEY=your-api-key
ccm start

# 设置环境变量（按`ccm start`的输出指示）
export ANTHROPIC_BASE_URL=http://0.0.0.0:4000
export ANTHROPIC_AUTH_TOKEN=sk-xxx

# 现在可以正常使用Claude Code了
claude --model claude-3.5-haiku
```

## 总结

Claude Code Mate的优势在于开箱即用和配置简便，特别适合以下用户：

- 想用Claude Code但受限于网络环境的国内用户
- 希望尝试不同大模型并集中管理配置
- 喜欢简洁方案，不想花费太多时间进行其他定制

如果你正在寻找一个简单有效的方式使用Claude Code和切换各种大模型，不妨试试Claude Code Mate这个工具。


[1]: https://www.anthropic.com/claude-code
[2]: https://github.com/musistudio/claude-code-router
[3]: https://github.com/RussellLuo/claude-code-mate
[4]: https://docs.litellm.ai/docs/simple_proxy
