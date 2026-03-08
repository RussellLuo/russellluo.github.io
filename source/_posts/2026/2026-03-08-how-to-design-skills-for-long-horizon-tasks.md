categories:
- AI

tags:
- MCP

title: 面向长程任务的Skills设计技巧
---

Skills是当前Agent领域最热门的设计范式之一，风头一时无两。这也让很多人形成了一种直觉：

> 只要Skill写得足够详细，Agent就能搞定复杂任务。

在简单任务中，这种想法通常没什么问题。但一旦面对**长程任务**（Long-horizon tasks），效果往往大打折扣，甚至根本无法完成。

那么问题就来了——当处理长程任务时，Skills应该如何设计？

## 长程任务为什么困难

在Agent系统中，**长程任务**是指那些需要**持续几十分钟、数小时甚至几天时间**才能完成的任务，例如：

- 自动化软件开发流程
- 深度技术调研
- 长链路业务流程执行

这类任务通常具有三个特点：

1. 步骤数量多
2. 执行时间长
3. 上下文持续增长

从LLM的角度来看，本质问题在于：

> 任务执行过程中产生的token会不断累积，进而导致上下文膨胀，甚至会超出LLM的上下文限制。

## 有了Skills为什么还需要上下文工程

针对上述问题，Anthropic在[Effective context engineering for AI agents][1]中进行了深入探讨，并从上下文工程（Context engineering）的角度出发，提出了3种解决方案：

- **压缩**（Compaction）：在上下文接近上限时，通过高保真摘要压缩历史对话并重启上下文窗口，以维持长程任务的连贯性。
- **Subagents**（Sub-agent architectures）：将复杂任务拆分给多个拥有独立上下文的专用Subagent处理，并由主Agent进行高层规划与结果整合，从而突破上下文限制并提升复杂任务的处理能力。
- **结构化笔记**（Structured note-taking）：让Agent定期将重要信息记录到上下文之外的持久存储中，并在需要时拉回，以保持跨复杂任务的关键上下文和依赖的技术。

细心的读者可能已经注意到，上述文章发表于Skills推出之前，那么Skills是否已经解决了长程任务的问题呢？答案是否定的。

关于Skills，我们在[谈谈Agent Skills的底层原理][2]中探讨过：它的三层加载技术（亦即Progressive Disclosure），本质上是一种Context Offloading策略。但有一点需要补充的是，Progressive Disclosure的设计是为了“**让通用Agent具备处理各种特定任务的能力，但无需一次性加载所有特定任务的知识**”，而不是为了更好地处理某个长程任务。

因此，即使有了Skills，我们仍然需要结合上下文工程的方法来应对长程任务。对于上述3种方法，**压缩**需要Agent系统本身支持（Claude Code等工具已经支持）。本文主要从使用者的角度出发，探讨如何利用**Subagents**和**结构化笔记**来优化Skills的设计。

## 一个简化案例：开发流程Agent

假设我们希望构建一个Agent，用于自动化软件开发流程。

实际的开发流程通常会涉及众多环节，这里为了简化讨论，我们只考虑以下三个步骤：

- **Issue → Code**：根据Issue生成代码
- **Code → Tests**：为代码生成测试
- **Code → Review**：进行代码审查

针对这个流程，我们可以写一个“大Skill”：

```
---
name: dev-workflow
description: Complete development workflow for handling issues.
---

You help developers with three workflow tasks:

1. Issue to Code: Generate code from issue description.
2. Code to Tests: Generate tests for the generated code.
3. Code to Review: Perform code review on the generated code.
```

如果在Claude Code中使用这个Skill，执行过程中的Context大致如下：

```
[System] You are Claude Code.
[User] Complete issue.md
[Tool Call] Read(.claude/skills/dev-workflow/SKILL.md)
[Tool Output] <the skill instructions>
[Tool Call] Read(issue.md)
[Tool Output] <issue description>]
[Assistant] <generated code>
[Tool Call] Write(code.py)
[Tool Output] <success>
[Assistant] <generated tests>
[Tool Call] Write(tests.py)
[Tool Output] <success>
[Tool Call] Bash(python tests.py)
[Tool Output] <test results>
[Assistant] <generated review report>
[Tool Call] Write(review.md)
[Tool Output] <success>
[Assistant] <final output>
```

可以看到，3个任务共享同一个LLM上下文，随着任务的推进，上下文会不断膨胀。在真实场景中，如果Issue的需求比较复杂，上下文膨胀问题会更加严重，甚至可能导致任务失败。

## 技巧一：使用1个主Agent和3个Subagent

利用**Subagents**的思路，一种策略是创建3个独立的Subagent，分别负责开发、测试和审查（参考[Create custom subagents][3]）。

开发Subagent（位于`.claude/agents/code-developer.md`）：

```
---
name: code-developer
description: Generate code from issue description.
---

You are a code developer. Your task is to generate code based on the provided issue description.
```

测试Subagent（位于`.claude/agents/code-tester.md`）：

```
---
name: code-tester
description: Generate tests for the provided code.
---

You are a code tester. Your task is to generate tests for the provided code.
```

审查Subagent（位于`.claude/agents/code-reviewer.md`）：

```
---
name: code-reviewer
description: Perform code review on the provided code.
---

You are a code reviewer. Your task is to perform code review on the provided code.
```

有了这3个Subagent之后，我们再创建一个Skill（位于`.claude/skills/effective-dev-workflow/SKILL.md`），指导主Agent调用这3个Subagent：

```
---
name: effective-dev-workflow
description: Complete development workflow for handling issues.
---

You are a project manager. Your task is to manage the development workflow for handling issues.

Here are the steps you need to follow:

1. Issue to Code: Use the `code-developer` agent to generate code from the issue description.
2. Code to Tests: Use the `code-tester` agent to generate tests for the generated code.
3. Code to Review: Use the `code-reviewer` agent to perform code review on the generated code.
```

同样地，我们可以在Claude Code中使用这个Skill，但执行过程中会产生4个独立的Context。

主Agent的Context：

```
[System] You are Claude Code.
[User] Complete issue.md
[Tool Call] Read(.claude/skills/effective-dev-workflow/SKILL.md)
[Tool Output] <the skill instructions>
[Tool Call] Read(issue.md)
[Tool Output] <issue description>
[Tool Call] Task(code-developer, "Generate code and save it as code.py")
[Tool Output] <final output from code-developer>
[Tool Call] Task(code-tester, "Generate tests for the code in code.py and save them as tests.py")
[Tool Output] <final output from code-tester>
[Tool Call] Task(code-reviewer, "Perform code review on the code in code.py and save the report as review.md")
[Tool Output] <final output from code-reviewer>
[Assistant] <final conclusion>
```

开发Subagent的Context：

```
[System] You are Claude Code.\nYou are a code developer...
[User] Generate code and save it as code.py
[Assistant] <generated code>
[Tool Call] Write(code.py)
[Tool Output] <success>
[Assistant] <final output>
```

测试Subagent的Context：

```
[System] You are Claude Code.\nYou are a code tester...
[User] Generate tests for the code in code.py and save them as tests.py
[Tool Call] Read(code.py)
[Tool Output] <code content>
[Assistant] <generated tests>
[Tool Call] Write(tests.py)
[Tool Output] <success>
[Tool Call] Bash(python tests.py)
[Tool Output] <test results>
[Assistant] <final output>
```

审查Subagent的Context：

```
[System] You are Claude Code.\nYou are a code reviewer...
[User] Perform code review on the code in code.py and save the report as review.md
[Tool Call] Read(code.py)
[Tool Output] <code content>
[Assistant] <generated review report>
[Tool Call] Write(review.md)
[Tool Output] <success>
[Assistant] <final output>
```

由上可见：

- 主Agent只关注高层次的任务调度，每个Subagent只返回关键结果，大大减少了主Agent的上下文负担。
- 同时，每个Subagent也都有自己独立的上下文，不会相互干扰，从而有效避免了上下文膨胀的问题。

## 技巧二：使用3个独立的Skill

利用**结构化笔记**的思路，我们也可以创建3个独立的Skill，分别负责开发、测试和审查。

开发Skill（位于`.claude/skills/code-developer/SKILL.md`）：

```
---
name: code-developer
description: Generate code from issue description.
---

You are a code developer. Your task is to generate code based on the provided issue description.

There is a {project_root}/NOTES.md file that records the progress of the task:
- Please review this file before starting the task.
- After completing the task, record the key progress in this file.
```

测试Skill（位于`.claude/skills/code-tester/SKILL.md`）：

```
---
name: code-tester
description: Generate tests for the provided code.
---

You are a code tester. Your task is to generate tests for the provided code.

There is a {project_root}/NOTES.md file that records the progress of the task:
- Please review this file before starting the task.
- After completing the task, record the key progress in this file.
```

审查Skill（位于`.claude/skills/code-reviewer/SKILL.md`）：

```
---
name: code-reviewer
description: Perform code review on the provided code.
---

You are a code reviewer. Your task is to perform code review on the provided code.

There is a {project_root}/NOTES.md file that records the progress of the task:
- Please review this file before starting the task.
- After completing the task, record the key progress in this file.
```

然后，我们**在3个不同的会话里分别调用这3个Skill**，从而会产生3个独立的Context。

开发Skill的Context：

```
[System] You are Claude Code.
[User] Complete issue.md
[Tool Call] Read(.claude/skills/code-developer/SKILL.md)
[Tool Output] <the skill instructions>
[Tool Call] Read(issue.md)
[Tool Output] <issue description>
[Tool Call] Read(NOTES.md)
[Tool Output] <notes content>
[Assistant] <generated code>
[Tool Call] Write(code.py)
[Tool Output] <success>
[Tool Call] Write(NOTES.md, "# Task Progress\n## Completed Tasks\n### 2026-03-08: Generated code and created code.py")
[Tool Output] <success>
[Assistant] <final output>
```

> 此时，`NOTES.md`的内容如下：
> ```
> # Task Progress
> ## Completed Tasks
> ### 2026-03-08: Generated code and created code.py
> ```

测试Skill的Context：

```
[System] You are Claude Code.
[User] Generate tests for code.py
[Tool Call] Read(.claude/skills/code-tester/SKILL.md)
[Tool Output] <the skill instructions>
[Tool Call] Read(code.py)
[Tool Output] <code content>
[Tool Call] Read(NOTES.md)
[Tool Output] <notes content>
[Assistant] <generated tests>
[Tool Call] Write(tests.py)
[Tool Output] <success>
[Tool Call] Bash(python tests.py)
[Tool Output] <test results>
[Tool Call] Edit(NOTES.md, "\n### 2026-03-08: Generated tests and created tests.py")
[Tool Output] <success>
[Assistant] <final output>
```

> 此时，`NOTES.md`的内容如下：
> ```
> # Task Progress
> ## Completed Tasks
> ### 2026-03-08: Generated code and created code.py
> ### 2026-03-08: Generated tests and created tests.py
> ```

审查Skill的Context：

```
[System] You are Claude Code.
[User] Perform code review on code.py
[Tool Call] Read(.claude/skills/code-reviewer/SKILL.md)
[Tool Output] <the skill instructions>
[Tool Call] Read(code.py)
[Tool Output] <code content>
[Tool Call] Read(NOTES.md)
[Tool Output] <notes content>
[Assistant] <generated review report>
[Tool Call] Write(review.md)
[Tool Output] <success>
[Tool Call] Edit(NOTES.md, "\n### 2026-03-08: Performed code review and created review.md")
[Tool Output] <success>
[Assistant] <final output>
```

> 此时，`NOTES.md`的内容如下：
> ```
> # Task Progress
> ## Completed Tasks
> ### 2026-03-08: Generated code and created code.py
> ### 2026-03-08: Generated tests and created tests.py
> ### 2026-03-08: Performed code review and created review.md
> ```

由上可见：

- 因为每个Skill都在不同的会话中被调用，所以它们之间不会共享上下文，从而避免了上下文膨胀的问题。
- 每个Skill都通过`NOTES.md`文件来读取和记录关键进度，从而实现了跨Skill（跨会话）的信息传递，保证了整体任务的连贯性。

值得说明的是，这个技巧的本质是**基于独立会话的多Agent协作**。这里不同的Skill，实际上只是给每个Agent添加了不同的知识，使其能够执行特定的任务。

关于多Agent协作完成复杂任务的更多内容，Anthropic在另一篇文章[Effective harnesses for long-running agents][4]作了详细介绍，感兴趣的读者可以进一步阅读。

## 结语

Skills是一种强大的能力封装方式，但面对长程任务时，它并不是解决一切问题的银弹——LLM的上下文限制始终是绕不过去的瓶颈。

更实用的思路是将Skills与上下文工程结合起来：

- 通过 Subagents 拆分上下文，让不同角色各自处理独立子任务；
- 通过结构化笔记在上下文之外保存关键状态，实现跨会话的信息传递。

Skills负责告诉Agent“怎么做”，上下文工程决定Agent“能走多远”。两者结合，才是应对长程任务的完整答案。


[1]: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
[2]: https://russellluo.com/2026/01/how-agent-skills-work-under-the-hood
[3]: https://code.claude.com/docs/en/sub-agents
[4]: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents