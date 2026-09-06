categories:
- AI

tags:
- 从零学大模型
- LLM
- GPT-2
- llama.cpp

title: 从零学大模型：Hidden State 如何流过 GPT-2 Block？
---

![GPT-2 中 12 个 Transformer Block 的位置](gpt2-model-overview.svg)

在上一篇[《Token ID 如何变成向量？》](/2026/08/how-token-ids-become-vectors)中，`How are` 对应的 Token Embedding 与 Position Embedding 相加，得到 shape 为 `[2,768]` 的 Initial Hidden State（初始隐藏状态）。它是第一个 GPT-2 Block 的输入，但还不是模型最终用于预测下一个 Token 的表示。

接下来，Hidden State 会依次流过 12 个 GPT-2 Block。本文先把 Self-Attention 和 MLP 当作两个内部黑盒，重点理解每个 Block 的共同骨架：Pre-Norm、Residual Connection，以及一个 Block 的输出如何成为下一个 Block 的输入；最后再用 llama.cpp 的实际代码和运行结果验证这条数据流。

## GPT-2 Block

Embedding 只完成了输入表示的初始化。真正结合上下文、逐层更新每个 Token 表示的工作，主要发生在这 12 个 Block 中。

一个 GPT-2 Block 包含两个子层：

1. Self-Attention（自注意力），结合可见的上下文更新每个位置的表示。
2. MLP（多层感知机），分别更新每个位置的表示。

> **GPT-2 使用 Causal Self-Attention（因果自注意力）**
>
> 这里的 `Causal` 表示每个位置只能读取自身和此前的位置，不能读取后续位置。

Self-Attention 和 MLP 都采用 Pre-Norm 和 Residual Connection（残差连接），完整数据流如下：

![Hidden State 流过一个 GPT-2 Block 的数据流](gpt2-block-flow.svg)

图中，黑色主路径经过 LayerNorm 和子层，分别产生 Attention 更新 `A_l` 和 MLP 更新 `M_l`；蓝色 Residual Connection 旁路则保留各子层进入 LayerNorm 前的状态。在每个阶段，两条路径都在 `+` 处逐元素相加。

一个 Block 的完整数据流可以分为两个依次执行、结构相同的阶段：

1. **Attention 阶段**：以 `X_l` 为输入，经过 LayerNorm 和 Self-Attention 得到更新 `A_l`；再将 `A_l` 与原始 `X_l` 相加，得到 `H_l`。
2. **MLP 阶段**：以 `H_l` 为输入，经过 LayerNorm 和 MLP 得到更新 `M_l`；再将 `M_l` 与原始 `H_l` 相加，得到 `X_(l + 1)`。

如果第 `l` 个 Block 的输入是 `X_l`，一层数据流可以写成：

```text
A_l       = Attention_l(LN_attn_l(X_l))
H_l       = X_l + A_l

M_l       = MLP_l(LN_ffn_l(H_l))
X_(l + 1) = H_l + M_l
```

## Hidden State

Hidden State 可以理解为模型在当前层对整段 Token 序列的内部表示。对于包含 `T` 个 Token、Hidden size 为 `D` 的输入，它的 shape 是：

```text
[T, D]
```

每个 Token 位置对应一个 `D` 维向量。GPT-2 Small 的 `D = 768`，因此 `How are` 在原理视角下对应：

```text
"How"  的表示 ─┐
              ├─ Hidden State [2, 768]
" are" 的表示 ─┘
```

这里的 Hidden State 不是另一张可以直接翻译回文本的词表，也不是给每个 Token 固定不变的向量。它有三个重要特点：

- 同一位置的向量会随着 Block 的计算不断更新。
- 向量逐渐包含当前位置及其可见上下文的信息。
- Block 输入和输出的 Hidden size 都是 768，因此多个 Block 可以首尾相接。

用 `x_(l,i)` 表示第 `l` 个 Block 输入中第 `i` 个 Token 位置的 Hidden 向量。它不是一个数，而是包含 `D` 个数的一维向量：

```text
x_(l,i) [D] = [x_(l,i,0), x_(l,i,1), ..., x_(l,i,D-1)]
```

将 `T` 个位置的向量按照 Token 顺序纵向排列，就得到整个 Hidden State `X_l`：

```text
X_l [T,D] = [
  x_(l,0)      ← 第 0 个 Token 位置的 D 维向量
  x_(l,1)      ← 第 1 个 Token 位置的 D 维向量
  ...
  x_(l,T-1)    ← 第 T - 1 个 Token 位置的 D 维向量
]
```

其中，`l` 表示 Block 层编号，`i` 表示 Token 在序列中的位置，最后一个下标表示向量内部的维度编号。对于 GPT-2 Small，`D = 768`。

Self-Attention 会在遵守因果约束的前提下，让每个位置从可见位置读取信息；MLP 则对每个位置分别做进一步变换。虽然内部计算不同，但两个子层最终都会回到 `[T,D]`，才能与 Residual Connection 分支逐元素相加。

## Pre-Norm

LayerNorm（层归一化）先对每个 Token 位置的 768 维向量单独归一化，再使用训练得到的 weight 和 bias 做缩放与平移。对一个 Hidden 向量 `x`，可以简写为：

```text
LN(x) = γ ⊙ (x - μ) / sqrt(σ² + ε) + β
```

其中，`μ` 和 `σ²` 由当前 Hidden 向量的 768 个值计算得到；`γ` 和 `β` 分别是训练得到的 weight 和 bias；`ε` 是一个固定的很小正数，用于避免方差过小时分母接近 0。LayerNorm 不会改变 Token 数量或 Hidden size：

```text
输入  [T, D]
输出  [T, D]
```

> **为什么需要 LayerNorm？**
>
> Hidden State 经过不同 Block 后，数值的整体偏移和尺度可能发生变化。LayerNorm 的作用不是增加新的上下文信息，而是让 Attention 和 MLP 获得数值尺度相对可控的输入。

GPT-2 使用 Pre-Norm：LayerNorm 位于 Attention 或 MLP 之前。[GPT-2 原论文](https://cdn.openai.com/better-language-models/language-models.pdf)将其描述为把 LayerNorm 移到每个子 Block 的输入。对一个 Block 来说，顺序是：

```text
X_l → LayerNorm → Attention → Residual Add
H_l → LayerNorm → MLP       → Residual Add
```

Pre-Norm 可以写成 `x + Sublayer(LN(x))`：原始状态 `x` 沿 Residual Connection 主路径直接保留，归一化后的另一份状态则交给子层计算更新。相比将相加结果再归一化的 Post-Norm `LN(x + Sublayer(x))`，Pre-Norm 保留了不经过 LayerNorm 的直接路径，也为训练时的梯度传播提供了更直接的通道。

> **Pre-Norm 为什么更容易训练？**
>
> [Xiong 等人的研究](https://proceedings.mlr.press/v119/xiong20b)表明，在其理论与实验设置下，Pre-Norm Transformer 初始化时的梯度比 Post-Norm 更稳定，对 Learning Rate Warm-up 的依赖也更小。这解释了 Pre-Norm 为什么通常更容易训练，但不表示它在所有场景下都一定优于 Post-Norm。

这些考量主要发生在训练阶段。本文讨论的推理过程只会使用已经训练好的参数完成前向计算，不会继续训练或更新它们。每个 Block 有两组 LayerNorm 参数，分别服务于 Attention 和 MLP。

## Residual Connection

Residual Connection 不直接用子层输出替换原来的 Hidden State，而是保留原状态，再加入子层算出的更新：

```text
新表示 = 原状态 + 子层更新
x_new  = x + F(x)
```

这里的 `F(x)` 表示 LayerNorm 和子层共同算出的更新。在前面的 Block 数据流中，`A_l` 和 `M_l` 分别是两个子层产生的 `F(x)`，而 `X_l` 和 `H_l` 则沿对应的 Residual Connection 旁路直接保留。

不使用 Residual Connection 时，下一层只能接收到子层输出；使用 Residual Connection 后，原状态 `x` 会沿旁路直接传到输出：

```text
无 Residual Connection：x_new = F(x)
有 Residual Connection：x_new = x + F(x)
```

两者的区别在“保持原状态不变”时最容易看出来：

- **无 Residual Connection**：如果模型希望得到 `x_new ≈ x`，就必须让整个子层学会 `F(x) ≈ x`，也就是由子层重新产生一份接近输入的表示。
- **有 Residual Connection**：原状态 `x` 已经通过旁路直接到达输出。子层不需要重新生成 `x`，只需让更新 `F(x) ≈ 0`，就可以得到 `x_new ≈ x`。

用一个简单的线性变换说明：如果 `F(x) = Wx`，没有 Residual Connection 时，需要学到 `W ≈ I`（`I` 表示单位矩阵）才能保持输入；使用 Residual Connection 后，只需让 `W ≈ 0`，旁路就会自动保留 `x`。

这并不表示 `F(x)` 必须始终很小。当子层确实需要改变当前表示时，`F(x)` 可以产生相应大小的更新；`F(x) ≈ 0` 只是在“不需要修改原状态”时的一种特殊情况。

> **Residual Connection 为什么有利于深层训练？**
>
> [He 等人](https://openaccess.thecvf.com/content_cvpr_2016/papers/He_Deep_Residual_Learning_CVPR_2016_paper)在图像识别网络的实验中发现，对于不使用 Residual Connection、只把上一层输出交给下一层的网络，增加深度后训练误差可能反而升高；加入 Residual Connection 后，较深的网络获得了更低的训练误差。这项实验结果支持了前面的设计直觉：让恒等路径直接存在、由子层学习额外变化，有利于深层网络的训练。

无论子层最终加入什么变化，它的输出都必须与原状态具有相同的 shape，才能进行逐元素相加：

| 阶段 | 原理 shape |
|---|---|
| 输入 Hidden State `X_l` | `[T,D]` |
| Attention LayerNorm 输出 | `[T,D]` |
| Attention 更新 `A_l` | `[T,D]` |
| 第一次 Residual Add 结果 `H_l` | `[T,D]` |
| MLP LayerNorm 输出 | `[T,D]` |
| MLP 更新 `M_l` | `[T,D]` |
| 输出 Hidden State `X_(l + 1)` | `[T,D]` |

## 12 个 Block

GPT-2 Small 包含 12 个串联的 Transformer Block。本文沿用 llama.cpp 从 `0` 开始的编号方式，将它们依次记作 `Block 0` 到 `Block 11`：

![12 个 GPT-2 Block 的层间数据流](gpt2-block-stack.svg)

> **为什么要堆叠多个 Block？**
>
> 多个 Block 串联后，每个位置都可以反复读取可见上下文，并经过多轮非线性变换。这样既增加了模型的计算深度，也让前面形成的表示能够被后续 Block 继续组合和更新，为模型表达更复杂的关系提供更大的能力。
>
> 不过，更深并不意味着效果一定更好。[GPT-2 论文](https://cdn.openai.com/better-language-models/language-models.pdf)比较了 12、24、36 和 48 层的四种模型配置，并观察到模型整体容量增加时，多项任务的表现随之提升。但这些配置同时增加了层数、Hidden State 的维度和总参数量，因此不能把提升单独归因于 Block 数量。
>
> 后续的 [Scaling Laws 研究](https://openai.com/index/scaling-laws-for-neural-language-models/)进一步指出，模型的损失主要随模型规模、训练数据量和训练计算量变化；在研究覆盖的较大范围内，宽度与深度等具体形状的影响相对较小。因此，Block 数量应被理解为训练前结合实验效果与计算预算确定的架构超参数，而不是越多越好。

这 12 个 Block 的计算骨架相同，但并不共享参数。每一层都有自己训练得到的 LayerNorm、Attention 和 MLP 参数，因此 Block 0 学到的变换与 Block 11 并不相同。

因此，12 层串联可以概括为：

```text
X_(l + 1) = Block_l(X_l),  l = 0, 1, ..., 11
```

每一层接收上一层的输出，再生成新的 Hidden State。最后一个 Block 的输出还要经过 Final LayerNorm 和 LM Head，才会变成用于预测下一个 Token 的 logits。

## llama.cpp 实战

下面使用 llama.cpp `b10435` 和 GPT-2 Q8_0 模型，从 GGUF 参数、GPT-2 建图源码和运行时 Tensor 三个角度验证 Block 数据流。基础环境和模型准备见[《LLM 如何逐个生成 Token？》](/2026/08/how-llm-generates-next-token/#环境准备)。

进入 llama.cpp 目录，设置模型路径，并构建本篇使用的调试程序：

```bash
cd llama.cpp

GPT2_MODEL=models/QuantFactory/gpt2-GGUF/gpt2.Q8_0.gguf

cmake --build build \
  --target llama-eval-callback \
  --config Release -j
```

### 验证 12 个 Block 的独立参数

先用 `gguf-dump` 查看模型的 Block 数量和每层的 Tensor 数量，再将 Block 0 和 Block 11 的 Tensor 按参数组归类：

```bash
.venv/bin/gguf-dump "$GPT2_MODEL" --json |
  jq '
    .metadata["gpt2.block_count"].value as $block_count |
    def block_tensors($i):
      [.tensors | keys[] | select(startswith("blk.\($i)."))];
    def parameter_groups($i):
      [block_tensors($i)[] | sub("\\.(weight|bias)$"; "")] | unique;
    {
      block_count: $block_count,
      tensor_count_per_block: [
        range(0; $block_count) as $i |
        block_tensors($i) | length
      ],
      block_0_groups: parameter_groups(0),
      block_11_groups: parameter_groups(11)
    }'
```

当前模型的输出如下：

```json
{
  "block_count": 12,
  "tensor_count_per_block": [
    12, 12, 12, 12, 12, 12,
    12, 12, 12, 12, 12, 12
  ],
  "block_0_groups": [
    "blk.0.attn_norm",
    "blk.0.attn_output",
    "blk.0.attn_qkv",
    "blk.0.ffn_down",
    "blk.0.ffn_norm",
    "blk.0.ffn_up"
  ],
  "block_11_groups": [
    "blk.11.attn_norm",
    "blk.11.attn_output",
    "blk.11.attn_qkv",
    "blk.11.ffn_down",
    "blk.11.ffn_norm",
    "blk.11.ffn_up"
  ]
}
```

`block_count` 验证了当前模型包含 12 个 Block，`tensor_count_per_block` 中从第 0 项到第 11 项都为 `12`，说明每层都有 12 个参数 Tensor。命令去掉 Tensor 名称末尾的 `.weight` 和 `.bias` 后，得到每层的 6 个参数组：

| GGUF 参数组 | Block 中的概念 |
|---|---|
| `attn_norm` | Attention 前的 LayerNorm |
| `attn_qkv`、`attn_output` | Attention |
| `ffn_norm` | MLP 前的 LayerNorm |
| `ffn_up`、`ffn_down` | MLP |

每个参数组都包含 weight 和 bias，因此 6 个参数组对应 12 个 Tensor。Block 0 和 Block 11 具有相同的参数组，但完整名称分别以 `blk.0.` 和 `blk.11.` 开头，说明两层的计算骨架相同，却读取各自独立的参数。

Residual Add 没有训练参数，因此不会出现在 GGUF 参数列表中；下一节将从源码中的 `ggml_add()` 确认它在 Block 数据流中的位置。

### 从源码确认 Block 的计算路径

GPT-2 的建图入口是 [`llama_model_gpt2::graph::graph()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/models/gpt2.cpp#L58-L147)。其中，[Block 层循环](https://github.com/ggml-org/llama.cpp/blob/b10435/src/models/gpt2.cpp#L82-L132)的主路径如下：

```cpp
for (int il = 0; il < n_layer; ++il) {
    cur = build_norm(inpL,
            model.layers[il].attn_norm,
            model.layers[il].attn_norm_b,
            LLM_NORM, il);

    // self-attention
    {
        cur = build_attn(/* ... */);
    }

    ggml_tensor * ffn_inp = ggml_add(ctx0, cur, inpL);

    cur = build_norm(ffn_inp,
            model.layers[il].ffn_norm,
            model.layers[il].ffn_norm_b,
            LLM_NORM, il);

    cur = build_ffn(cur, /* ... */);

    cur = ggml_add(ctx0, cur, ffn_inp);

    // input for next layer
    inpL = cur;
}
```

这些代码位置可以与前面的 Block 数据流逐项对应。表中的运行时节点将在下一节用于检查实际计算结果：

| 原理中的表示 | llama.cpp 代码 | 运行时节点 |
|---|---|---|
| 输入 Hidden State `X_l` | 循环开始时的 `inpL` | `inpL`，或上一层的 `l_out-(l-1)` |
| `LN(X_l)` | `cur = build_norm(inpL, ...)` | `attn_norm-l` |
| Attention 更新 `A_l` | `cur = build_attn(...)` | —（无独立节点） |
| `H_l = X_l + A_l` | `ffn_inp = ggml_add(ctx0, cur, inpL)` | `ffn_inp-l` |
| `LN(H_l)` | `cur = build_norm(ffn_inp, ...)` | `ffn_norm-l` |
| MLP 更新 `M_l` | `cur = build_ffn(cur, ...)` | `ffn_out-l` |
| `X_(l + 1) = H_l + M_l` | 第二次 `ggml_add()`，随后执行 `inpL = cur` | `l_out-l` |

两次 `build_norm(..., LLM_NORM, ...)` 都位于对应子层之前，验证了 GPT-2 的 Pre-Norm 结构。两次 `ggml_add()` 则分别对应 Attention 和 MLP 之后的 Residual Add。

源码中的 `cur` 只是建图时反复复用的临时变量，它在不同位置代表不同 Tensor；理解代码时应结合它刚刚经过的操作，而不能把 `cur` 当作一个含义固定的模型概念。

### 用运行时输出验证 shape 与层间连接

使用 `llama-eval-callback` 运行 `How are`，只保留 Block 0 和 Block 1 的关键节点：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' 2>&1 |
  rg 'common_debug_cb_eval: +(attn_norm|ffn_inp|ffn_norm|ffn_out|l_out)-(0|1) ='
```

为了突出数据流，下面只保留了节点名称、输入关系和 shape：

```text
attn_norm-0                                   = {768, 2}
ffn_inp-0 = ADD(...{768, 2}, inpL{768, 2})    = {768, 2}
ffn_norm-0                                    = {768, 2}
ffn_out-0                                     = {768, 2}
l_out-0   = ADD(ffn_out-0,
                ffn_inp-0)                    = {768, 2}

attn_norm-1                                   = {768, 2}
ffn_inp-1 = ADD(...{768, 2}, l_out-0{768, 2}) = {768, 2}
...
l_out-1                                       = {768, 2}
```

这些节点是 `llama-eval-callback` 输出的运行时中间 Tensor，不是前面 `blk.0.attn_norm.weight`、`blk.0.attn_norm.bias` 这类模型参数。节点名中的 `-0` 和 `-1` 分别表示 Block 0 和 Block 1，它们与原理概念的对应关系见上一节表格。输出中的 `...` 表示没有独立回调节点名的 Attention 更新，这里只保留其 shape。

GGML 将 Hidden 维度放在前面，因此 `{768,2}` 对应原理部分的 `[2,768]`。`ffn_inp-0` 和 `l_out-0` 分别是两次 Residual Add 的实际结果，参与相加的 Tensor 与结果都保持相同 shape。Block 0 的 `l_out-0` 又出现在 Block 1 第一次 Residual Add 的输入中，直接验证了“当前层输出成为下一层输入”。

## 小结

本文从 Block 父视角说明了 Hidden State 如何逐层更新：

- Hidden State 以 `[T,D]` 的 shape 流过 Block；Attention 和 MLP 会更新其中的表示，但不会改变 Token 数量和 Hidden size。
- Attention 和 MLP 都采用 Pre-Norm 和 Residual Connection：先对输入进行 LayerNorm，再由子层计算更新，最后与原状态逐元素相加。
- GPT-2 Small 串联了 12 个计算骨架相同、参数各自独立的 Block；每个 Block 的输出都会成为下一个 Block 的输入。
