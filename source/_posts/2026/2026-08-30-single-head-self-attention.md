categories:
- AI

tags:
- 从零学大模型
- LLM
- GPT-2
- llama.cpp

title: 从零学大模型：Self-Attention —— 单头注意力
---

![GPT-2 中 Self-Attention 的位置](gpt2-model-overview.svg)

在上一篇[《Hidden State 如何流过 GPT-2 Block？》](/2026/08/how-hidden-state-flows-through-gpt2-block)中，我们只跟踪了 Self-Attention 在 Block 中的输入和输出：LayerNorm 处理后的 Hidden State 进入 Self-Attention，产生的 Attention 更新再通过 Residual Connection 加回原 Hidden State。本篇继续展开内部计算，观察它如何读取可见上下文。

GPT-2 同时使用多个 Attention Head（注意力头，以下简称 Head）。本文先说明单个 Head 与整体 Self-Attention 的关系，再以 `How are` 中的 `" are"` 为例，完整跟踪从 Q、K、V，到匹配分数、Causal Mask（因果掩码）、Softmax，再到 Value 加权求和的过程。单头视角不是额外的执行阶段，而是从多头并行计算中抽出的一条分支。

## 为什么需要 Self-Attention

先看两个结构相同的句子：

```text
这种水果叫苹果，它很甜。
这家公司叫苹果，它生产手机。
```

两句话都有“苹果”和“它”，但上下文不同。“水果”和“公司”会影响“苹果”在当前句子中的表示；处理“它”时，也需要结合此前位置的信息。也就是说，一个位置的表示不能只包含当前 Token，还需要聚合可见上下文。

回到本文使用的 `"How are"`，在第一个 GPT-2 Block 之前，每个位置的 Initial Hidden State 由自己的 Token Embedding 与 Position Embedding 相加得到：

```text
"How"   → x_(0,0) [D]
" are"  → x_(0,1) [D]
```

`x_(0,0)` 和 `x_(0,1)` 已经分别包含“当前是什么 Token”和“当前位于哪里”，但 `" are"` 还没有通过 Attention 聚合 `"How"` 的信息。

Self-Attention 将上下文读取拆成三个部分：

1. Causal Mask 决定当前位置可以读取哪些位置。
2. Q、K 的匹配分数决定各个可见位置应该获得多大权重。
3. 模型使用这些权重对 V 加权求和，得到包含上下文信息的新向量。

如果始终以相同权重汇总所有可见位置的 V，模型就无法根据当前输入决定更侧重哪些位置。Self-Attention 则会根据当前 Hidden State 动态计算 Attention 权重，从可见位置中有选择地汇总信息。

> **为什么 Transformer 使用 Self-Attention？**
>
> 处理序列时，模型需要在不同位置之间传递信息，常见做法有：
>
> - **RNN（循环神经网络）** 需要沿序列逐步传递状态，因此各位置的计算存在顺序依赖。
> - **CNN（卷积神经网络）** 可以并行计算，但使用局部卷积核时，每一层通常只能连接邻近位置，远距离位置需要经过多层才能建立联系。
> - **Self-Attention** 可以在一层内直接连接任意两个允许读取的位置，并对已经给定的序列并行计算各位置。
>
> [Transformer](https://papers.nips.cc/paper/2017/file/3f5ee243547dee91fbd053c1c4a845aa-Paper.pdf) 以 Self-Attention 为核心，兼顾远距离信息交互与并行计算；[GPT-2](https://cdn.openai.com/better-language-models/language-models.pdf) 也基于这一架构。
>
> 这里的“并行”是指一次前向计算可以同时处理多个位置；GPT-2 的自回归生成仍需逐个生成 Token。

## Self-Attention 与单个 Head

上一篇从 Block 的整体视角，把 Self-Attention 写成一个 `[T,D] → [T,D]` 的子层。将 LayerNorm 的输出记为 `Z_l`，可以写成：

```text
Z_l = LN_attn_l(X_l)       [T,D]
A_l = Attention_l(Z_l)     [T,D]
```

其中，`X_l [T,D]` 是第 `l` 个 Block 的输入，`A_l [T,D]` 是完整的 Attention 更新。展开中间过程，可以看到多个 Head 与整体 Self-Attention 的关系：

![GPT-2 Small 中多个 Attention Head 与单个 Head 的关系](multi-head-attention-overview.svg)

GPT-2 Small 的 Hidden size 为 `D = 768`，包含 12 个 Head，因此每个 Head 的维度为：

```text
D_h = D / 12 = 64
```

这里的 `D / 12` 只用于确定每个 Head 的特征宽度，不是把输入 `Z_l` 预先切成 12 份。12 个 Head 使用各自的投影参数，并行读取同一个 `Z_l [T,768]`；每个 Head 都从完整的 `Z_l` 产生一个 `O_h [T,64]`。

12 个 Head 的输出随后沿特征维合并回 `[T,768]`；Token 数量 `T` 不变，也不是逐元素相加。本文只跟踪到 `O_h`。

## 单头上下文读取流程

下面只观察第 `h` 个 Head，并以 `" are"` 位置的 Query 为例，沿图中箭头从上向下跟踪一次上下文读取：

![Z_l 中“ are”位置向量通过一个 Attention Head 读取可见上下文](self-attention-context-reading.svg)

当前 Attention 的输入是 `Z_l [T,D]`。在这个例子中，它包含 `"How"` 和 `" are"` 两个 Token 位置；真正进入当前 Head 的分别是位置向量 `z_(l,0) [D]` 和 `z_(l,1) [D]`。

为了与图中的符号对应，下面用下标 `0`、`1` 表示 Token 位置，用上标 `(h)` 表示当前观察的第 `h` 个 Head。

`" are"` 位置的读取过程可以分成四步：

1. **计算 Q、K、V**：当前 Head 使用三组线性变换，把 `z_(l,0)` 和 `z_(l,1)` 分别投影为各自的 Query、Key 与 Value；其中 `" are"` 的 Query 记为 `q_1^(h)`，后续沿它展开。
2. **计算匹配分数**：`q_1^(h)` 分别与两个输入位置的 Key（`k_0^(h)` 和 `k_1^(h)`）做点积并缩放。
3. **得到 Attention 权重**：Causal Mask 先排除不允许读取的位置，Softmax 再把保留的分数转换成权重 `p_(1,0)` 和 `p_(1,1)`，分别对应 `"How"` 和 `" are"`。
4. **读取 Value**：将两个 Value（`v_0^(h)` 和 `v_1^(h)`）分别乘以对应的权重，再相加得到当前 Head 在 `" are"` 位置的输出 `o_1^(h) [D_h]`。

在处理整段输入的一次前向计算中，Self-Attention 会为序列中的各个位置计算读取结果。“Self”表示 Q、K、V 来自同一段输入序列；“Causal”表示每个位置只能读取自身及此前位置。

## Q、K、V

Q、K、V 都来自同一个 `Z_l`，但使用不同的投影参数，作用也不同：

- **Query**：当前位置用什么特征发起查询。
- **Key**：每个位置用什么特征与 Query 匹配。
- **Value**：匹配后实际汇总的内容向量。

对第 `h` 个 Head，Q、K、V 的计算可以写成：

```text
Q_h = Z_l W_Q^(h) + b_Q^(h)
K_h = Z_l W_K^(h) + b_K^(h)
V_h = Z_l W_V^(h) + b_V^(h)
```

`Z_l W_Q^(h)` 表示矩阵乘法；下文中，相邻书写的矩阵同样表示矩阵乘法。

当前 Head 使用三组训练得到的投影参数：权重矩阵 `W_Q^(h)`、`W_K^(h)`、`W_V^(h)`，以及偏置向量 `b_Q^(h)`、`b_K^(h)`、`b_V^(h)`。这些参数由当前 Head 的所有 Token 位置共用；Q、K、V 则由各位置的当前输入计算，会随输入变化。

三组投影参数及其输出的 shape 是：

```text
W_Q^(h) / W_K^(h) / W_V^(h)  [D, D_h]
b_Q^(h) / b_K^(h) / b_V^(h)  [D_h]
Q_h / K_h / V_h              [T, D_h]
```

小写的 `q_i^(h)`、`k_i^(h)`、`v_i^(h)` 表示第 `i` 个 Token 位置在当前 Head 中的向量；大写的 `Q_h`、`K_h`、`V_h` 则把所有 `T` 个位置的向量按行放在一起。因此：

```text
q_i^(h) = Q_h[i, :]
k_i^(h) = K_h[i, :]
v_i^(h) = V_h[i, :]
```

对于 `"How are"`，图中跟踪的 `q_1^(h)` 就是 `Q_h` 中索引为 `1` 的行，也就是第二行。

## Scaled Dot-Product Attention

Q、K、V 准备好后，当前 Head 会依次计算匹配分数、Attention 权重和 Value 加权结果。这一过程就是 Scaled Dot-Product Attention（缩放点积注意力）。

下面先沿 `q_1^(h)` 的路径逐步展开，再扩展到整个 Head 的矩阵形式。

### 原始匹配分数

一个 Query 与一个 Key 都是 `D_h` 维向量，二者的点积得到一个匹配分数：

```text
score_h(i, j) = q_i^(h) · k_j^(h)
```

对于图中 `" are"` 位置的 `q_1^(h)`：

```text
score_h(1, 0) = q_1^(h) · k_0^(h)
score_h(1, 1) = q_1^(h) · k_1^(h)
```

分数越大，表示 Query `i` 与 Key `j` 在模型学到的特征空间中越匹配，但它还不是 Attention 权重。

### 从分数到 Attention 权重

原始分数要依次经过三个步骤：**缩放 → Causal Mask → Softmax**。

**第一步：缩放。** 随着 `D_h` 增大，点积的典型幅度也会增大，容易使 Softmax 过度集中到少数位置。除以 `sqrt(D_h)` 可以控制分数的典型尺度：

```text
scaled_score_h(i, j) = score_h(i, j) / sqrt(D_h)
```

GPT-2 Small 的单个 Head 为 `D_h = 64`，所以缩放因子是：

```text
1 / sqrt(64) = 1 / 8
```

**第二步：加入 Causal Mask。** GPT-2 是 Decoder-only 模型，使用自回归方式预测下一个 Token。计算位置 `i` 的表示时，只允许读取位置 `0` 到 `i`，不能读取未来位置 `j > i`。

对于当前的 `"How are"`，Causal Mask 可以写成：

```text
                    Key
               "How"   " are"
Query "How"      0       -∞
      " are"     0        0
```

Causal Mask 会加到缩放后的分数上：允许读取的位置加 `0`，不改变分数；未来位置加 `-∞`，经过 Softmax 后权重变成 `0`。因此，`q_0^(h)` 只能读取 `"How"`，`q_1^(h)` 可以读取 `"How"` 和 `" are"`。

扩展到更长序列时，Causal Mask 会形成同样的下三角结构：即使一次输入整段文本，每个位置也只能使用自身及此前位置的信息。

> **Causal Mask 能代替 Position Embedding 吗？**
>
> 不能。Causal Mask 只规定“哪些位置可见”，不能告诉模型当前位置是第几个 Token。GPT-2 的 Position Embedding 通过训练得到，并以绝对位置编号查表；Self-Attention 再使用 Causal Mask 限制信息流向。二者作用不同，不能相互替代。

**第三步：Softmax。** 加入 Causal Mask 后，Softmax 沿每个 Query 对应的那一行计算，把可见位置的分数转换成总和为 `1` 的非负权重。对于 `q_1^(h)`，得到的两个权重是：

```text
[p_(1,0), p_(1,1)]
```

`p_(1,0)` 表示 `" are"` 从 `"How"` 读取信息的权重，`p_(1,1)` 表示它从自身读取信息的权重。

### 用 Attention 权重读取 Value

得到 Attention 权重后，当前 Query 使用这些权重对所有可见位置的 Value 做加权求和：

```text
o_i^(h) = Σ_j p_(i,j) v_j^(h)
```

对于图中的 `" are"`：

```text
o_1^(h) = p_(1,0) v_0^(h) + p_(1,1) v_1^(h)
```

权重作用在 Value 上，而不是直接复制某个 Token，也不是对 Key 做加权求和。计算结果 `o_1^(h) [D_h]` 就是当前 Head 在 `" are"` 位置的输出。

### 整个 Head 的矩阵形式

上面只跟踪了 `q_1^(h)` 的一条路径。实际计算会同时处理所有 Query 位置：

```text
S_h = Q_h K_h^T / sqrt(D_h) + M
P_h = softmax(S_h)
O_h = P_h V_h
```

`K_h^T` 表示 `K_h` 的转置。`K_h [T,D_h]` 转置后变为 `K_h^T [D_h,T]`，因此 `Q_h [T,D_h]` 与 `K_h^T [D_h,T]` 相乘会得到 `[T,T]` 的分数矩阵。

其中：

- `M [T,T]` 是前面 Causal Mask 表格的矩阵形式。
- `S_h [T,T]` 是原始匹配分数经过缩放并加上 `M` 后的分数矩阵。
- `P_h [T,T]` 是 Attention 权重，Softmax 沿每一行计算。
- `O_h [T,D_h]` 是当前 Head 的输出。

位置级符号与矩阵中的元素一一对应：

```text
(Q_h K_h^T)[i,j]  = score_h(i, j) = q_i^(h) · k_j^(h)
S_h[i,j]          = score_h(i, j) / sqrt(D_h) + M[i,j]
P_h[i,:]          = softmax(S_h[i,:])
P_h[i,j]          = p_(i,j)
O_h[i,:]          = o_i^(h)
```

因此，当前 `q_1^(h)` 对应 `P_h` 中索引为 `1` 的第二行，输出 `o_1^(h)` 对应 `O_h` 中索引为 `1` 的第二行。

将三步合并，可得 Scaled Dot-Product Attention 的公式：

```text
O_h = softmax(Q_h K_h^T / sqrt(D_h) + M) V_h
```

### 最小数值例子

下面继续使用 `"How are"` 的两个位置（`T = 2`），并将 Head 维度简化为 `D_h = 4`，把分数、Causal Mask、Softmax 和 Value 加权连起来。

为便于手算，这里只观察一个 Head，省略下标 `h`，并取 `Q = K`。GPT-2 Small 的实际 `D_h` 是 `64`，示例数值不代表真实运行结果。

`Q`、`V` 的两行以及 `K^T` 的两列，都依次对应 `"How"` 和 `" are"`。设：

```text
Q = [
  [1, 0, 1, 1],
  [1, 1, 0, 1]
]

K^T = [
  [1, 1],
  [0, 1],
  [1, 0],
  [1, 1]
]

V = [
  [1, 0, 1, 0],
  [0, 1, 0, 1]
]
```

`Q` 的每一行与 `K^T` 的每一列做点积，得到原始匹配分数：

```text
Q K^T = [
  [3, 2],
  [2, 3]
]
```

再除以 `sqrt(D_h) = sqrt(4) = 2`，得到缩放后的分数：

```text
Q K^T / sqrt(4) = [
  [1.500, 1.000],
  [1.000, 1.500]
]
```

Query 行和 Key 列均按 `"How"`、`" are"` 的顺序排列，Causal Mask 为：

```text
M = [
  [0, -∞],
  [0,  0]
]
```

将 `M` 加到缩放后的分数上，未来位置才会变成 `-∞`：

```text
S = Q K^T / sqrt(4) + M = [
  [1.500,   -∞],
  [1.000, 1.500]
]
```

接着逐行计算 `P = softmax(S)`。`" are"` 对应的第二行计算结果是：

```text
softmax([1.000, 1.500]) ≈ [0.378, 0.622]
```

得到 Attention 权重矩阵：

```text
P = [
  [1.000, 0.000],
  [0.378, 0.622]
]
```

最后用这些权重对 V 加权求和，`" are"` 位置的输出是：

```text
O_1 ≈ 0.378 [1, 0, 1, 0] + 0.622 [0, 1, 0, 1]
    = [0.378, 0.622, 0.378, 0.622]
```

对应的矩阵结果为：

```text
O ≈ [
  [1.000, 0.000, 1.000, 0.000],
  [0.378, 0.622, 0.378, 0.622]
]
```

`"How"` 位置只能读取自己的 `V_0`；`" are"` 位置则从 `V_0` 和 `V_1` 读取信息。至此，一个 Head 的 Causal Self-Attention 计算就完成了。

## 单头 shape 主线

训练完成后，`W_Q^(h)`、`W_K^(h)`、`W_V^(h)` 及其偏置作为模型参数，在推理时保持不变。运行时，当前 `Z_l` 依次产生 `Q_h`、`K_h`、`V_h`、匹配分数、Attention 权重和 `O_h`，这些 Tensor 都会随输入、Block 或 Head 发生变化。因此，“Attention 权重”不是保存在模型文件中的固定参数。

Causal Mask 稍有不同：它的因果规则固定，但具体 Tensor 由当前序列长度和位置关系确定。

前文的 `W_Q^(h)`、`W_K^(h)`、`W_V^(h)` 及其偏置，是按单个 Head 展开的逻辑写法；GPT-2 如何组织多个 Head 的参数留到下一篇。

这条单头计算路径的逻辑 shape 如下：

| 阶段 | 逻辑 shape | GPT-2 Small（`T=2`） |
|---|---|---|
| Attention 输入 `Z_l` | `[T,D]` | `[2,768]` |
| `Q_h` / `K_h` / `V_h` | 各自 `[T,D_h]` | 各自 `[2,64]` |
| Attention 分数 `S_h` / 权重 `P_h` | 各自 `[T,T]` | 各自 `[2,2]` |
| Head 输出 `O_h` | `[T,D_h]` | `[2,64]` |

`O_h` 对应整体视图中的一条 Head 分支，还不是最终的 Attention 更新 `A_l [T,D]`。

## llama.cpp 实战

下面使用 llama.cpp `b10435` 和 GPT-2 Q8_0 模型，从真实运行中选出 `Block 0 / Head 0`，验证单头公式。基础环境和模型准备见[《LLM 如何逐个生成 Token？》](/2026/08/how-llm-generates-next-token/#环境准备)，`gguf-dump` 的安装方式见[《文本如何变成 Token ID？》](/2026/08/how-text-becomes-token-ids/#查看-GGUF-中的-Tokenizer-数据)。

进入 llama.cpp 目录，设置模型路径，并构建本篇使用的调试程序：

```bash
cd llama.cpp

GPT2_MODEL=models/QuantFactory/gpt2-GGUF/gpt2.Q8_0.gguf

cmake --build build \
  --target llama-eval-callback \
  --config Release -j
```

### 确认单个 Head 的逻辑维度

先从 GGUF 元数据读取 Hidden size 和 Head 数，并计算单个 Head 的维度：

```bash
.venv/bin/gguf-dump "$GPT2_MODEL" --json |
  jq '
    (.metadata["gpt2.embedding_length"].value) as $d |
    (.metadata["gpt2.attention.head_count"].value) as $h |
    {
      hidden_size: $d,
      head_count: $h,
      head_dim: ($d / $h)
    }'
```

当前模型的输出为：

```json
{
  "hidden_size": 768,
  "head_count": 12,
  "head_dim": 64
}
```

当前模型的 Hidden size 为 `768`，包含 `12` 个 Head，因此每个 Head 的维度为 `768 / 12 = 64`。本文只选择 `Block 0 / Head 0`，因此后面的 Q、K、V 和输出都按单头逻辑 shape `[T,64]` 阅读，不比较不同 Head。

### 查看运行时 shape

以 `How are` 为输入，筛选 Block 0 的 Attention 中间 Tensor：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' \
  --flash-attn off \
  2>&1 |
  rg 'common_debug_cb_eval: +(Qcur-0|Kcur-0|Vcur-0|kq-0|kq_soft_max-0|kqv-0) ='
```

本次实验使用 `--flash-attn off` 保留 `kq`、`kq_soft_max` 和 `kqv` 三个中间 Tensor，便于逐步检查单头计算过程。

经过裁剪的真实输出如下：

```text
Qcur-0         = {64, 12, 2, 1}
Kcur-0         = {64, 12, 2, 1}
Vcur-0         = {64, 12, 2, 1}
kq-0           = {256, 2, 12, 1}
kq_soft_max-0  = {256, 2, 12, 1}
kqv-0          = {64, 2, 12, 1}
```

节点名末尾的 `-0` 表示 Block 0，不表示 Head 0。对于 Q、K、V，`{64,12,2,1}` 可以记为 `{head_dim, head_count, T, 1}`；前三个维度依次表示每个 Head 的特征数、Head 数和 Token 数。Head 0 就是在 Head 数所在的第二个维度取索引 `0`。

分数 Tensor 的维度顺序不同：在 `{256,2,12,1}` 中，第三个维度 `12` 才是 Head 数，因此 Head 0 是该维度中索引为 `0` 的切片。后面的数值实验都只读取这个切片。

运行时输出采用 GGML 的维度顺序，与前文使用的逻辑 shape 写法不同。只取 Head 0 后，可以按计算顺序理解为：

| 运行时 Tensor | 单头逻辑含义 | 单头逻辑 shape |
|---|---|---|
| `Qcur-0` / `Kcur-0` / `Vcur-0` | `Q_h` / `K_h` / `V_h` | 各自 `[2,64]` |
| `kq-0` | `Q_h K_h^T` 的原始分数 | 有效区域 `[2,2]` |
| `kq_soft_max-0` | 缩放、Causal Mask、Softmax 后的 `P_h` | 有效区域 `[2,2]` |
| `kqv-0` | `P_h V_h` | `[2,64]` |

llama.cpp 会先把本轮 `Kcur-0` 和 `Vcur-0` 写入 KV Cache，再让 Attention 读取 KV Cache 中的 K、V 视图。当前实验从空 KV Cache 开始处理 `How are`，因此前两个有效位置就是本轮产生的 K、V，对应这里的 `K_h`、`V_h`。

`kq-0` 中的 `256` 来自当前 KV Cache 的对齐视图容量。本轮只有 `How` 和 ` are` 两个位置有效，其余槽位会被 Causal Mask 排除；这里的 `256` 不表示输入变成了 256 个 Token。

### 验证单头 Attention 计算

**分数与 Attention 权重。** 保留 `kq-0` 和 `kq_soft_max-0` 的 Tensor 数值：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' \
  --flash-attn off \
  2>&1 |
  sed -n '/kq-0 =/,/sum =/p; /kq_soft_max-0 =/,/sum =/p'
```

从输出中取出 Head 0 的两个 Query，并为每个 Query 只保留前两个 Key 位置：

| Query | `kq` 原始分数 | `kq_soft_max` 权重 |
|---|---|---|
| Query 0 / `How` | `[3.7358, -13.7144]` | `[1.0000, 0.0000]` |
| Query 1 / ` are` | `[-1.3936, -25.5417]` | `[0.9534, 0.0466]` |

`kq` 是尚未缩放的 Q/K 点积分数。GPT-2 Small 的 `kq_scale = 1/8`，所以 `" are"` 的两个可见分数先变成：

```text
[-1.3936 / 8, -25.5417 / 8]
≈ [-0.1742, -3.1927]
```

两个位置对 Query 1 都可见，Softmax 后得到：

```text
[0.9534, 0.0466]
```

Query 0 虽然在 `kq` 中也有两个原始分数，但 `" are"` 对它来说是未来位置，Causal Mask 会把第二项排除，因此最终权重为 `[1.0000, 0.0000]`。这也说明二者职责不同：Q/K 点积决定匹配分数，Causal Mask 决定哪些分数可以参与 Softmax。

**Value 加权。** 继续查看 `Vcur-0` 和 `kqv-0`：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' \
  --flash-attn off \
  2>&1 |
  sed -n '/Vcur-0 =/,/sum =/p; /kqv-0 =/,/sum =/p'
```

将 Head 0 的两个 Value 各保留前 3 维，并列出 Query 1 的两个权重：

```text
v_0^(0) = [-0.1252,  0.0577, 0.0428, ...]   # "How"
v_1^(0) = [ 0.2463, -0.0901, 0.2779, ...]   # " are"

p_(1,0) = 0.9534
p_(1,1) = 0.0466
```

按照单头公式：

```text
o_1^(0)
= 0.9534 × v_0^(0) + 0.0466 × v_1^(0)
≈ [-0.1079, 0.0508, 0.0538, ...]
```

`kqv-0` 中 Query 1 对应位置的前 3 维是：

```text
[-0.1080, 0.0509, 0.0538, ...]
```

上面的数值只保留了 4 位小数，因此手算结果与回调输出存在约 `0.0001` 的舍入误差。在这一误差范围内，两者结果一致，也说明 Attention 权重确实作用在 Value 上，并产生 Head 0 的输出 `O_h [2,64]`。

**改变输入。** 最后把输入扩展为三个 Token `How are you`，再次查看 `kq_soft_max-0`：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are you' \
  --flash-attn off \
  2>&1 |
  sed -n '/kq_soft_max-0 =/,/sum =/p'
```

输出的第一个 Head 切片包含三个 Query；只保留前三个 Key 位置：

```text
Query 0 / "How"  = [1.0000, 0.0000, 0.0000]
Query 1 / " are" = [0.9534, 0.0466, 0.0000]
Query 2 / " you" = [0.8849, 0.0563, 0.0588]
```

Query 0 只能读取位置 0，Query 1 只能读取位置 0～1，Query 2 才能读取全部三个位置。前两个 Query 的权重与 `How are` 实验相同，说明在 `How are you` 这次前向计算中，新增的未来 Token 不会影响此前位置。

### 对照源码

GPT-2 在 [`llama_model_gpt2::graph::graph()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/models/gpt2.cpp#L89-L97) 中先调用 `build_qkv()`，再把 Q、K、V 和 `1/sqrt(D_h)` 传入 `build_attn()`：

```cpp
auto [Qcur, Kcur, Vcur] = build_qkv(model.layers[il], cur,
        n_embd_head, n_head, n_head_kv, il);

cur = build_attn(inp_attn,
        model.layers[il].wo, model.layers[il].wo_b, model.layers[il].wo_s,
        Qcur, Kcur, Vcur, nullptr, nullptr, nullptr,
        1.0f/sqrtf(float(n_embd_head)), il);
```

[`build_qkv()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/llama-graph.cpp#L1592-L1665) 产生包含全部 Head 的 `Qcur`、`Kcur` 和 `Vcur`，随后由 `build_attn()` 继续处理。本文只从这些 Tensor 中选择 Head 0，把它们当作单头计算的输入；GPT-2 如何一次产生并组织所有 Head 的 Q、K、V 留到下一篇。

[`build_attn()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/llama-graph.cpp#L2778-L2793) 再通过 `cpy_k()`、`cpy_v()` 把当前 K、V 写入 KV Cache，并用 `get_k()`、`get_v()` 取得 KV Cache 视图，交给 `build_attn_mha()`。

关闭 Flash Attention 后，[`build_attn_mha()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/llama-graph.cpp#L2566-L2611) 中与单头公式对应的核心操作是：

```cpp
ggml_tensor * kq = ggml_mul_mat(ctx0, k, q);

kq = ggml_soft_max_ext(ctx0, kq, kq_mask, kq_scale,
        hparams.f_max_alibi_bias);

ggml_tensor * kqv = ggml_mul_mat(ctx0, v, kq);
```

逐项对应如下：

| 数学计算 | llama.cpp / GGML |
|---|---|
| `Q_h K_h^T` | `ggml_mul_mat(k, q)` → `kq` |
| 缩放 + Causal Mask + Softmax | `ggml_soft_max_ext(..., kq_mask, kq_scale, ...)` → `kq_soft_max` |
| `P_h V_h` | `ggml_mul_mat(v, kq)` → `kqv` |

虽然函数名是 `build_attn_mha()`，Q、K、V Tensor 也保留了 12 个 Head，但上面三步会沿 Head 维分别计算；只取 Head 0，就得到本文推导的单头公式。

源码没有为缩放、Causal Mask 和 Softmax 分别创建三个节点。`ggml_soft_max_ext()` 同时接收 `kq_scale` 和 `kq_mask`，在一个操作中完成这三步。上述调用只是在构建 GGML 计算图，真正的数值由后端执行。

## 小结

本文以 `"How are"` 中的 `" are"` 为例，从单个 Head 的视角说明了 Self-Attention 如何读取可见上下文：

- 一个 Attention Head 用 Query 与 Key 计算分数，经缩放和 Causal Mask 排除未来位置，再由 Softmax 得到 Attention 权重，最后汇总 Value。
- Q、K、V、Attention 权重和 Head 输出都由当前输入动态产生；训练得到并保存在模型文件中的是投影参数，而不是固定的 Attention 结果。
- GPT-2 Small 并行计算 12 个 Head；单个 Head 输出 `O_h [T,64]`，还不是完整的 Attention 更新 `A_l [T,768]`。
