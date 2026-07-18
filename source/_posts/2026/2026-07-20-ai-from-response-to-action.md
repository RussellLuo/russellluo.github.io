categories:
- AI

title: 从回答到行动：AI 如何工作，我们如何成长
---

## AI 正在融入我们的生活

<img alt="AI应用全景图" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/ai-application-overview.png" />

如果说过去的人工智能更多存在于实验室和专业领域，那么今天，AI 已经来到我们身边。从学习辅导、内容创作，到软件开发、办公协作，再到医疗、科研、自动驾驶和机器人，AI 正在进入越来越多真实场景。

## AI 应用的三次跃迁

AI 的范围远不止大语言模型，还包括计算机视觉、语音识别、推荐系统、机器学习、机器人控制等多个领域。它的能力可以体现在感知、预测、生成、决策和行动等不同环节。

近年来，以大模型为重要推动力的新一轮 AI 应用浪潮正在展开：AI 先从对话工具进入工作流程，再从协作助手发展为自主执行任务的 Agent，最后与视觉、传感器、机器人和控制系统结合，进一步进入物理世界。

### 第一跃迁：从 Chatbot 到 Copilot

<img alt="第一跃迁" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/ai-application-first-transition.png" />

从 Chatbot 到 Copilot，关键变化是 AI 从独立的对话工具进入具体任务环境，利用任务上下文，在人的操作过程中持续提供协助。人仍主导任务目标、执行步骤和关键操作，AI 负责协作，而不是独立完成任务。

#### 学习：从通用答疑到个性化学习助手

<div style="display:flex; gap:20px;">

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**Chatbot**

学生：

> 植物细胞和动物细胞有什么区别？

AI 根据通用知识回答问题。

学生仍需要：

* 补充课程背景
* 判断回答是否符合教材
* 自己整理考试重点
* 自己安排后续练习

**典型特征**

针对单个问题作答，依赖用户补充上下文。

</div>

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**Copilot**

学生在学习空间中添加：

* 生物教材 PDF
* 课堂笔记
* 课程大纲

然后提出目标：

> 根据这些资料，帮我复习考试中的植物细胞和动物细胞。

AI 可以：

1. 根据课程大纲确定考试范围
2. 结合教材和笔记解释知识点
3. 比较植物细胞与动物细胞
4. 通过测验发现薄弱点
5. 根据测验结果调整后续学习内容

**典型特征**

基于课程材料和学习目标持续提供协助。

</div>

</div>

**代表产品**

* [Google Gemini（Study Notebooks）](https://blog.google/products-and-platforms/products/education/iste-students-2026/)
* [Khanmigo](https://www.khanmigo.ai/)

#### 办公：从内容生成到工作助手

<div style="display:flex; gap:20px;">

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**Chatbot**

用户：

> 根据这份会议记录生成一份会议纪要。

AI：

> 提炼议题、结论和待办事项，生成一份会议纪要。

任务结束。

**典型特征**

根据一次提示生成内容，任务完成即结束。

</div>

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**Copilot**

AI 进入整个工作流程：

会议前：

* 根据主题生成会议材料

会议中：

* 自动记录讨论内容

会议后：

* 总结关键结论
* 提取待办事项
* 生成跟进邮件

**典型特征**

利用会议上下文贯穿整个工作流程。

</div>

</div>

**代表产品**

* [Microsoft 365 Copilot](https://learn.microsoft.com/en-us/training/modules/manage-meetings-collaboration/)
* [飞书（智能会议纪要）](https://www.feishu.cn/content/article/7577317993749269689)

### 第二跃迁：从 Copilot 到 Agent

<img alt="第二跃迁" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/ai-application-second-transition.png" />

从 Copilot 到 Agent，关键变化是 AI 从协助人操作，发展为围绕目标自主拆解任务、调用工具、执行操作，并根据结果调整后续步骤。人从逐步操作任务，转向提出目标和检查结果。

#### 软件开发：从代码建议到自主执行开发任务

<div style="display:flex; gap:20px;">

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**Copilot**

开发者：

> 这段登录代码为什么会报错？

Copilot 根据当前文件和选中的代码：

* 分析错误原因
* 给出修改建议
* 生成局部代码修改

开发者仍然需要：

* 定位其他相关文件
* 审查并应用修改
* 运行测试
* 根据结果继续修复

**典型特征**

围绕当前代码提供建议，执行步骤由人完成。

</div>

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**Agent**

开发者：

> 修复用户登录失败的问题，并提交一个 PR。

AI Agent：

1. 阅读代码仓库
2. 理解项目架构
3. 找到相关模块
4. 复现并定位问题
5. 修改相关代码
6. 编写并运行测试
7. 根据测试结果继续修复
8. 创建 Pull Request

**典型特征**

围绕目标自主调用工具并完成开发任务。

</div>

</div>

**代表产品**

* [OpenAI Codex](https://openai.com/codex/)
* [Claude Code](https://code.claude.com/docs/en/overview)

#### 图形界面操作：从操作指导到自主执行

<div style="display:flex; gap:20px;">

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**Copilot**

用户：

> 如何在 Blender 中制作一个大炮模型？

Copilot 可以：

* 说明建模步骤
* 推荐使用的 Blender 工具
* 生成 Blender Python 脚本
* 解答操作过程中的问题

用户仍需要打开 Blender，并逐步完成建模操作。

**典型特征**

提供操作指导，界面操作由人完成。

</div>

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**Agent**

用户：

> 在 Blender 中创建一个大炮的 3D 模型。

Agent：

1. 观察 Blender 当前界面
2. 创建并调整基础几何体
3. 使用移动、缩放和旋转等工具
4. 根据模型状态继续修改
5. 完成 3D 模型

**典型特征**

直接操作界面并根据结果调整后续动作。

</div>

</div>

**代表产品**

* [ChatGPT / Codex（Computer Use）](https://x.com/evayzh/thread/2075374512401711203)

### 第三跃迁：从数字 AI 到物理 AI

<img alt="第三跃迁" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/ai-application-third-transition.png" />

从数字 AI 到物理 AI，关键变化是 AI 不再只处理文字、代码和数据，而是能够通过传感器感知环境、做出决策，并控制车辆或机器人。物理 AI 并非由单一大模型驱动，而是大模型、专用模型、传感器、控制算法与硬件共同作用的系统。

#### 自动驾驶：从辅助决策到自主驾驶

<div style="display:flex; gap:20px;">

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**数字 AI**

AI 可以：

* 分析路况
* 预测拥堵
* 规划路线

它向人提供建议，车辆仍由人驾驶。

**典型特征**

分析道路信息，辅助人做决策。

</div>

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**物理 AI**

自动驾驶系统：

* 通过摄像头和雷达感知环境
* 识别车辆、行人与交通规则
* 规划路线并决定转向、变道或减速
* 控制车辆转向、加速和刹车

**典型特征**

感知道路环境，自主决策并控制车辆。

</div>

</div>

**代表产品**

* [Waymo One](https://waymo.com/rides/)
* [百度萝卜快跑](https://www.apollogo.com/)

#### 机器人：从固定执行到自主感知与行动

<div style="display:flex; gap:20px;">

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**预编程机器人**

工厂机械臂通常按照预设程序工作：

* 在固定位置执行固定动作
* 根据预设规则响应传感器信号
* 完成明确、重复的任务

任务或环境发生变化时，通常需要重新配置或编程。

**典型特征**

按预设程序执行固定任务。

</div>

<div style="flex:1; padding:16px; border:1px solid #ddd; border-radius:8px;">

**自主机器人**

面对“把桌上的杯子放到厨房”这样的任务，自主机器人需要：

* 感知杯子、桌子和周围环境
* 理解任务目标
* 规划移动、抓取和避障动作
* 根据执行结果不断调整
* 控制身体完成任务

**典型特征**

根据任务、环境和反馈自主规划并行动。

</div>

</div>

**代表产品**

* [Figure 03](https://www.figure.ai/news/introducing-figure-03)
* [优必选 Walker S2](https://www.ubtrobot.com/cn/humanoid/products/walker-s2)

## Agent 如何工作

<img alt="Codex Agent" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/ai-application-codex-agent.png" />

AI Agent 不是“更会聊天的 AI”，而是一个围绕目标持续行动的智能执行系统。以 Codex 这类编程 Agent 为例，它以 LLM 为决策核心，结合上下文、状态、工具和约束，通过 Agent Loop 不断规划、执行、观察和调整，直到任务完成。

> **Agent = LLM + 上下文与状态 + 工具 + 执行循环 + 约束**

在每轮循环中，LLM 根据当前状态决定调用工具、调整计划、请求确认或结束任务；工具返回的日志、错误和测试结果又会成为下一轮决策的依据。这种反馈闭环使 Agent 能够动态处理问题，而不是按照固定流程运行。

实际系统还会通过最大步数、成本预算、权限控制和人工确认等机制限制循环，确保 Agent 的行动安全、可控。

### 实战演示：坦克大战

<img alt="Codex 坦克大战" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/ai-application-codex-tank-game.png" />

向 Agent 提出目标：

> 创建一个坦克大战小游戏，试玩并修复发现的问题。

Agent 将自主完成：

> 规划实现 → 编写代码 → 运行游戏 → Computer Use 试玩 → 发现问题 → 修改代码 → 再次试玩和验证

这个过程展示了 Agent 如何结合代码生成与界面操作，根据实际反馈持续调整，完成从创建到验证的闭环。

## 大模型如何工作

### 软件篇

<img alt="大模型原理：软件篇" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/ai-application-llm-software.png" />

大模型生成回答，本质上是在根据已有内容预测下一个 Token。输入的文字会先被切分成 Token 并转换为向量，再经过多层 Transformer 计算。注意力机制帮助模型判断上下文中哪些信息更重要，最终为下一个 Token 的候选项计算概率。模型选出一个 Token 后，会把它加入上下文并重复这一过程，直到生成完整的回答。

模型的知识并不是以一条条记录的形式存放在内部，而是在海量文本训练中被编码进模型参数。温度和采样策略会影响模型是倾向于选择概率最高的结果，还是保留更多表达上的变化。由于它本质上是一个概率生成系统，回答流畅并不代表内容一定正确；面对冷门事实、过时信息和复杂推理，仍然需要进一步核实。

### 硬件篇

<img alt="大模型原理：硬件篇" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/ai-application-llm-hardware.png" />

这些看似复杂的语言能力，落到硬件层面，主要是大规模的矩阵运算和数据搬运。GPU 拥有大量并行计算单元，能够同时执行许多结构相似的运算，因此成为大模型训练和推理的主力；Tensor Core 等专用单元则进一步提高了矩阵运算效率。不过，大模型的运行速度不仅取决于算力，也受到显存容量和带宽的制约。推理过程中，硬件需要不断读取模型参数、保存上下文缓存并传递中间结果，因此 HBM 和片上缓存同样重要。

一次推理通常分为 Prefill 和 Decode 两个阶段。Prefill 会集中处理用户输入，并为后续生成建立 KV Cache，它主要影响第一个 Token 出现前的等待时间；Decode 则利用缓存逐个生成新的 Token，主要影响回答持续输出的速度。上下文越长，KV Cache 占用的显存越多，数据搬运的成本也越高，因此长对话通常更消耗显存，生成速度也可能随之下降。


## AI 时代，我们如何成长

<img alt="AI 时代，我们如何成长" src="https://raw.githubusercontent.com/RussellLuo/russellluo.github.io/main/source/_posts/2026/images/ai-application-human-growth.png" />

AI 带来的问题不只是“它会不会替代人”，更重要的是我们如何使用它：是把思考外包给 AI，还是借助 AI 学习、实验和验证，在提高效率的同时保持自主性和掌握感。

### 需要警惕

**可靠性与安全**

大模型可能产生幻觉、过时信息和推理错误，Agent 的工具调用还可能把错误判断变成真实行动。把资料和系统权限交给 AI，也会带来隐私泄露、数据滥用和安全攻击等风险。因此，事实核查、结果验证、权限控制和人工确认仍然不可缺少。

**生成更快不等于真正交付**

AI 可以快速生成大量内容和代码，但后续的调试、验证和修正仍可能耗费大量时间。只关注生成数量，而不确认结果是否正确、问题是否解决，就容易把“看起来快”误认为“真正交付快”。

**便利可能削弱人的掌握感**

AI 的即时反馈可能制造一种虚假的心流：人不断提出要求、看到结果快速出现，却没有真正理解问题。随着越来越多分析和判断被交给 AI，人也可能从任务的主导者变成结果的选择者，逐渐削弱独立判断、专业能力和创造力。

### 如何成长

**从替人工作到增强人的能力**

当 AI 工具和组织更强调效率与产出时，个人更需要主动保留提出问题、理解原理、检验结果和承担判断的过程，保护自己的自主性和掌握感。

AI 不应只是替人交出答案的黑盒，也可以成为扩展思考和创造能力的工具。它能够解释概念、查找资料、比较方案并快速构建实验；人则负责确定目标、提出问题和判断结果，通过“边做边学、边问边验证”加深理解，挑战更复杂的问题。

**面向未来的核心能力**

未来的竞争力并不只是“会不会使用 AI”，而是能否把 AI 与自己的专业知识、判断力和创造力结合起来：

> **专业能力 + AI 协作能力 + 判断与创造能力**

专业能力帮助我们理解问题，AI 协作能力提高学习和实践的效率，判断与创造能力则让我们能够识别错误、提出新问题，并对最终结果负责。

> 不要用 AI 逃避思考，而要用 AI 加深思考；不要让 AI 替你完成工作，而要让 AI 帮你掌握工作。
