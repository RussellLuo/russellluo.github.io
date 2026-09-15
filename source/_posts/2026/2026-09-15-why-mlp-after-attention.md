categories:
- AI

tags:
- 从零学大模型
- LLM
- GPT-2
- llama.cpp

title: 从零学大模型：Attention 之后为什么还需要 MLP？
---

![GPT-2 中 MLP 的位置](gpt2-model-overview.svg)

上一篇[《Self-Attention —— 多头注意力》](/2026/09/multi-head-self-attention)介绍了如何将 12 个 Attention Head 的结果重新组合为 `A_l [T,768]`。`A_l` 再通过第一条 Residual Connection 与 Block 的输入 `X_l` 相加，得到已经包含上下文信息的 Hidden State `H_l [T,768]`。

但在 GPT-2 Block 中，Self-Attention 后面还有一个 MLP（多层感知机）子层。既然 Self-Attention 已经让每个位置读取了上下文，为什么还需要这个 MLP？

## Attention 与 MLP 的分工

Attention 和 MLP 都会更新 Hidden State，但它们处理信息的方式不同。

![Attention 与 MLP 的功能对比](attention-vs-mlp.svg)

Self-Attention 的关键作用是让每个 Token 位置读取可见上下文。对于第 `i` 个位置，Self-Attention 先计算 `Q_i` 与各位置 Key 的匹配程度，再对位置 `0 ... i` 的 Value 加权求和。因此，该位置的输出会直接依赖多个可见位置。

MLP 不再读取其他位置，而是对每个位置已经包含上下文信息的 Hidden State 进行非线性特征变换。

因此，二者的侧重点可以概括为：Attention 主要在不同 Token 位置之间混合信息；MLP 主要在每个 Token 位置内部变换特征。

## GPT-2 MLP 的整体结构

MLP 通常由输入层、一个或多个隐藏层和输出层组成。GPT-2 每个 Block 中的 MLP 采用一个隐藏层和一个输出层；按不计输入层的常见约定，这称为“两层 MLP”。

下面以 GPT-2 Small 为例。图中，`T` 表示 Token 数量，`D = 768` 表示 Hidden State 的维度，`M = 3072 = 4D` 表示 MLP 隐藏层的宽度。

![GPT-2 MLP 的完整数据流](gpt2-mlp-flow.svg)

第 `l` 个 Block 中，`H_l` 先经过 LayerNorm 得到 MLP 输入 `Z_l`。隐藏层通过 Up Projection（升维投影）生成激活前的值 `U_l`，再经 GELU 得到输出 `G_l`。GELU 是逐元素激活函数，用于引入非线性。

输出层通过 Down Projection（降维投影）将 `G_l` 组合为 MLP 更新 `M_l`，该更新随后通过第二次 Residual Add 与 `H_l` 相加。这里，`M_l` 表示更新，与表示隐藏层宽度的 `M` 不同。

以上是 GPT-2 的具体结构。其他模型的前馈网络可以采用不同的激活函数或[门控结构](https://arxiv.org/abs/2002.05202)，并不都遵循“Up Projection → GELU → Down Projection”的串行流程。

## 为什么采用“扩展 → 非线性 → 再组合”

前面提到的 Up Projection 和 Down Projection 都是线性投影：把输入按固定权重加权求和，再加上偏置。

但模型需要学习的关系可能更复杂。例如，假设某个输出分量只应在两条线索同时出现时明显增大，其他情况下保持接近零。固定的加权相加无法准确表达这种关系。Up Projection 先组合输入，GELU 再对组合结果进行非线性变换，使 MLP 能够学习这类依赖特征组合的关系。

即使隐藏层保持 768 维，GELU 也能引入非线性。扩展到 3072 维，则提供了更多隐藏单元。每个单元使用各自的权重和偏置组合输入，再经过 GELU 产生一个数值。这样的扩展不是把输入复制四遍，也不意味着保存了四倍“知识”。

这些额外的非线性计算结果可供 Down Projection 组合，使 MLP 能表达更复杂的输入与输出关系。不过，加宽隐藏层也会增加参数量和计算量。

下图以单个 Token 位置为例，两列 3072 维向量分别表示隐藏层激活前后的数值。圆点表示向量分量，数量和连线仅作示意；颜色变化用于示意 GELU 前后各分量数值的变化。

![GPT-2 MLP 的扩展、非线性与再组合](mlp-computation-workspace.svg)

从 3072 维降回 768 维，并不会让前面的扩展失去意义。每个输出分量都可以综合多个非线性中间结果，因此输出虽然仍是 768 个数，却能表达更复杂的输入与输出关系。

单独看 Down Projection，它无法无损保留任意 3072 维输入。但 MLP 的目标是利用这些中间结果生成所需的更新，而非保存全部中间值。Down Projection 因此是在组合前面的计算结果，并不是把 Up Projection 的操作逆转回去。

> **隐藏层会学到什么？**
>
> [Geva 等人的研究](https://aclanthology.org/2021.emnlp-main.446/)发现，一些隐藏单元（神经元）会对特定的文本模式产生较强响应，即遇到这类输入时，激活后的输出值较大。
>
> 对应到本文的 GPT-2 流程，隐藏单元的激活值就是 GELU 后的向量分量。可以把这类单元直观地看作训练得到的“模式探测器”，但这不意味着每个单元都对应一个固定概念；同一个单元也可能对多种文本模式产生响应。

## Position-wise：逐位置计算，共享参数

GPT-2 的 MLP 也常被称为 FFN（Feed-Forward Network，前馈网络）或 Position-wise FFN。`Position-wise` 表示：在同一 Block 内，每个 Token 位置独立完成 MLP 变换，所有位置共享同一组参数。

把 `H_l` 中第 `i` 个位置的向量记为 `h_(l,i) [D]`，这个位置经过 LayerNorm 和 MLP 后得到更新 `m_(l,i) [D]`：

```text
m_(l,i) = MLP_l(LN_ffn_l(h_(l,i)))    [D]
```

`m_(l,i)` 的计算只读取当前位置的 `h_(l,i)`，而其中已包含 Attention 引入的上下文信息。因此，逐位置计算并不意味着忽略上下文。

实现中，`T` 个位置可以组织成矩阵批量计算，这不改变逐位置计算的含义。不同 Block 则使用各自独立的参数。

## GPT-2 MLP 的三步计算

下面依次展开 Up Projection、GELU 和 Down Projection，公式省略权重和 bias 的层下标 `l`。

### Up Projection：从 768 维扩展到 3072 维

第一层线性投影使用 `W_up [768,3072]` 和 `b_up [3072]`：

```text
U_l = Z_l W_up + b_up

[T,768] × [768,3072] + [3072]
→ [T,3072]
```

`W_up` 有 3072 列，每一列把 768 个输入值加权组合成一个中间值。因此，每个 Token 位置会得到 3072 个输出，组成 `U_l [T,3072]`。

> **为什么中间维度是 3072？**
>
> [GPT-2 技术报告](https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf)表 2 给出的 117M 模型（通常称为 GPT-2 Small）隐藏维度为 `D = 768`；在 [OpenAI 官方实现](https://github.com/openai/gpt-2/blob/master/src/model.py)中，每个 Block 都以 `nx * 4` 作为 MLP 的中间维度。因此，GPT-2 Small 中有 `M = 4D = 3072`。
>
> 四倍宽度并非 GPT-2 独有：[《Attention Is All You Need》](https://proceedings.neurips.cc/paper/7181-attention-is-all-you-need.pdf)第 3.3 节的逐位置前馈网络采用 `512 → 2048 → 512`。它是一种常见的架构配置，并非所有 Transformer 都必须遵循，也不表示四倍维度在理论上最优。

### GELU：在线性投影之间加入非线性

Up Projection 之后，GPT-2 对每个位置的 3072 个中间值逐元素应用 GELU（Gaussian Error Linear Unit）。[GELU 原论文](https://arxiv.org/abs/1606.08415)将其定义为 `GELU(x) = xΦ(x)`，其中 `Φ(x)` 是标准高斯分布的累积分布函数。与 ReLU 根据输入正负进行硬截断不同，GELU 会根据输入值连续调节输出。

如果 `t` 表示 Token 位置、`j` 表示隐藏单元编号，可以写成：

```text
G_l[t,j] = GELU(U_l[t,j])
```

GELU 不改变 Tensor shape，输入和输出都是 `[T,3072]`；它只以非线性方式改变各元素的取值。

为什么两个线性层之间需要这样的非线性？如果去掉 GELU，那么 MLP 只剩两次连续的仿射变换：

```text
(x W_up + b_up) W_down + b_down
= x (W_up W_down) + (b_up W_down + b_down)
```

即使中间维度扩展到 3072，两次投影仍可合并为一次从 768 维到 768 维的仿射变换。GELU 在两者之间引入非线性，使 MLP 能表达更复杂的映射。

> **为什么选择 GELU？**
>
> MLP 需要在线性投影之间加入非线性，但并不限定必须使用 GELU。[原始 Transformer](https://proceedings.neurips.cc/paper/7181-attention-is-all-you-need.pdf) 使用 ReLU；GPT-2 则选择 GELU。
>
> 相比 ReLU，GELU 在零附近的变化更平滑；[原论文](https://arxiv.org/abs/1606.08415)也通过实验比较了 GELU、ReLU 和 ELU。因此，GELU 是一种有实验支持的架构选择，并非理论上唯一或必然最优的答案。
>
> 其他模型也可以采用不同的激活函数，或使用[带 gate 的 FFN](https://arxiv.org/abs/2002.05202)；后者还会改变内部结构。

### Down Projection：回到 768 维

第二层线性投影使用 `W_down [3072,768]` 和 `b_down [768]`：

```text
M_l = G_l W_down + b_down

[T,3072] × [3072,768] + [768]
→ [T,768]
```

Down Projection 将 3072 维中间结果重新组合成 768 维 MLP 更新 `M_l`。它必须回到 Hidden size `D`，因为接下来要通过第二次 Residual Add 与原来的 `H_l [T,D]` 逐元素相加：

```text
X_(l + 1) = H_l + M_l    [T,D]
```

整个过程中 Token 数量始终为 `T`，只有特征维在 MLP 内部暂时从 `D` 扩展到 `M`，再回到 `D`。

## llama.cpp 实战

下面使用 llama.cpp `b10435` 和 GPT-2 Q8_0 模型，从 GGUF 参数、运行时 Tensor 和源码三个角度验证 MLP。基础环境和模型准备见[《LLM 如何逐个生成 Token？》](/2026/08/how-llm-generates-next-token/#环境准备)。

进入 llama.cpp 目录，设置模型路径，并构建调试程序：

```bash
cd llama.cpp

GPT2_MODEL=models/QuantFactory/gpt2-GGUF/gpt2.Q8_0.gguf

cmake --build build \
  --target llama-eval-callback \
  --config Release -j
```

### 核对 FFN 参数

先从 GGUF 中读取 Hidden size、FFN 中间维度，以及 Block 0 的 LayerNorm、Up Projection 和 Down Projection 参数：

```bash
.venv/bin/gguf-dump "$GPT2_MODEL" --json |
  jq '{
    hidden_size: .metadata["gpt2.embedding_length"].value,
    intermediate_size: .metadata["gpt2.feed_forward_length"].value,
    ffn_norm_weight_shape: .tensors["blk.0.ffn_norm.weight"].shape,
    ffn_norm_bias_shape: .tensors["blk.0.ffn_norm.bias"].shape,
    ffn_up_weight_shape: .tensors["blk.0.ffn_up.weight"].shape,
    ffn_up_bias_shape: .tensors["blk.0.ffn_up.bias"].shape,
    ffn_down_weight_shape: .tensors["blk.0.ffn_down.weight"].shape,
    ffn_down_bias_shape: .tensors["blk.0.ffn_down.bias"].shape
  }'
```

当前模型的输出为：

```json
{
  "hidden_size": 768,
  "intermediate_size": 3072,
  "ffn_norm_weight_shape": [768],
  "ffn_norm_bias_shape": [768],
  "ffn_up_weight_shape": [768, 3072],
  "ffn_up_bias_shape": [3072],
  "ffn_down_weight_shape": [3072, 768],
  "ffn_down_bias_shape": [768]
}
```

输出确认了 `D = 768`、`M = 3072`，两组投影权重对应 `768 → 3072 → 768`。LayerNorm 不改变 Hidden size，其 weight 和 bias 均为 768 维；两次投影的 bias 则分别匹配各自的输出维度。

### 跟踪 MLP 的运行时 shape

以 `How are` 为输入运行调试程序，筛选 Block 0 的 MLP 相关输出：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' \
  2>&1 |
  rg 'common_debug_cb_eval: +(ffn_inp-0|ffn_norm-0|ffn_up-0|ffn_up_b-0|ffn_gelu-0|ffn_down-0|ffn_out-0|l_out-0) ='
```

筛选后的关键输出如下：

```text
common_debug_cb_eval:                ffn_inp-0 = (f32)        ADD(node_24{768, 2, 1, 1}, inpL{768, 2, 1, 1}}) = {768, 2, 1, 1}
common_debug_cb_eval:               ffn_norm-0 = (f32)        ADD(norm_w-0{768, 2, 1, 1}, blk.0.ffn_norm.bias{768, 1, 1, 1}}) = {768, 2, 1, 1}
common_debug_cb_eval:                 ffn_up-0 = (f32)    MUL_MAT(blk.0.ffn_up.weight{768, 3072, 1, 1}, ffn_norm-0{768, 2, 1, 1}}) = {3072, 2, 1, 1}
common_debug_cb_eval:               ffn_up_b-0 = (f32)        ADD(ffn_up-0{3072, 2, 1, 1}, blk.0.ffn_up.bias{3072, 1, 1, 1}}) = {3072, 2, 1, 1}
common_debug_cb_eval:               ffn_gelu-0 = (f32)       GELU(ffn_up_b-0{3072, 2, 1, 1}, }) = {3072, 2, 1, 1}
common_debug_cb_eval:               ffn_down-0 = (f32)    MUL_MAT(blk.0.ffn_down.weight{3072, 768, 1, 1}, ffn_gelu-0{3072, 2, 1, 1}}) = {768, 2, 1, 1}
common_debug_cb_eval:                ffn_out-0 = (f32)        ADD(ffn_down-0{768, 2, 1, 1}, blk.0.ffn_down.bias{768, 1, 1, 1}}) = {768, 2, 1, 1}
common_debug_cb_eval:                  l_out-0 = (f32)        ADD(ffn_out-0{768, 2, 1, 1}, ffn_inp-0{768, 2, 1, 1}}) = {768, 2, 1, 1}
```

llama.cpp / GGML 按 `{特征维, Token 维, ...}` 显示运行时 Tensor，与前文使用的 `[T,特征维]` 顺序相反：

| 运行时节点 | 运行时 shape | 逻辑含义 |
|---|---|---|
| `ffn_inp-0` | `{768,2}` | MLP 输入 `H_0 [2,768]` |
| `ffn_norm-0` | `{768,2}` | LayerNorm 输出 `Z_0 [2,768]` |
| `ffn_up-0` | `{3072,2}` | Up Projection 矩阵乘法结果，尚未加 `b_up` |
| `ffn_up_b-0` | `{3072,2}` | 加上 `b_up` 后的完整输出 `U_0 [2,3072]` |
| `ffn_gelu-0` | `{3072,2}` | 逐元素 GELU 输出 `G_0 [2,3072]` |
| `ffn_down-0` | `{768,2}` | Down Projection 矩阵乘法结果，尚未加 `b_down` |
| `ffn_out-0` | `{768,2}` | 加上 `b_down` 后的 MLP 更新 `M_0 [2,768]` |
| `l_out-0` | `{768,2}` | Residual Add 输出 `X_1 [2,768]` |

`How are` 对应两个 Token，因此从 `ffn_inp-0` 到 `l_out-0`，Tensor 的第二维始终为 `2`。在每次 `MUL_MAT` 中，同一张权重矩阵分别作用于两个位置的向量，只改变特征维，不混合不同位置的信息。这正是 Position-wise 的运行时表现。

阅读这段输出时，重点关注等号左侧的节点名、操作类型和最右侧的 shape；中间的上游 Tensor 名称及自动编号可能随计算图变化。

### 对照 GPT-2 建图代码

GPT-2 在 [`llama_model_gpt2::graph::graph()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/models/gpt2.cpp#L104-L125) 中先完成第一次 Residual Add，得到 MLP 输入 `ffn_inp`，随后依次执行 MLP 前的 LayerNorm、`build_ffn()` 和第二次 Residual Add：

```cpp
// add the input
ggml_tensor * ffn_inp = ggml_add(ctx0, cur, inpL);
cb(ffn_inp, "ffn_inp", il);

// FF
{
    cur = build_norm(ffn_inp,
            model.layers[il].ffn_norm,
            model.layers[il].ffn_norm_b,
            LLM_NORM, il);
    cb(cur, "ffn_norm", il);

    cur = build_ffn(cur,
            model.layers[il].ffn_up,   model.layers[il].ffn_up_b,   NULL,
            NULL,                      NULL,                        NULL,
            model.layers[il].ffn_down, model.layers[il].ffn_down_b, NULL,
            NULL,
            LLM_FFN_GELU, LLM_FFN_SEQ, il);
    cb(cur, "ffn_out", il);
}

cur = ggml_add(ctx0, cur, ffn_inp);
```

按通用 `build_ffn()` 的参数顺序，关键实参如下：

| `build_ffn()` 形参 | GPT-2 传入的实参 |
|---|---|
| `up / up_b` | `ffn_up / ffn_up_b` |
| `gate / gate_b / gate_s` | `NULL / NULL / NULL` |
| `down / down_b` | `ffn_down / ffn_down_b` |
| `type_op` | `LLM_FFN_GELU` |
| `type_gate` | `LLM_FFN_SEQ` |

`up` 和 `down` 对应两次线性投影，`type_op` 选择 GELU。`LLM_FFN_SEQ` 只是 gate 的连接类型，本身不代表“无 gate”；真正的依据是 `gate`、`gate_b` 和 `gate_s` 均为 `NULL`。因此，GPT-2 走的是无 gate 的 `up → GELU → down` 路径。

在通用的 [`build_ffn()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/llama-graph.cpp#L1669-L1868) 中，源码先构造 Up Projection 和 bias 节点：

```cpp
ggml_tensor * tmp = up ? build_lora_mm(up, cur) : cur;
cb(tmp, "ffn_up", il);

if (up_b) {
    tmp = ggml_add(ctx0, tmp, up_b);
    cb(tmp, "ffn_up_b", il);
}
```

GPT-2 未传入 gate，因此 `cur` 直接接收 Up Projection 的结果 `tmp`，随后进入 GELU。

`LLM_FFN_GELU` 分支随后构造 `ggml_gelu()` 节点：

```cpp
case LLM_FFN_GELU:
    if (gate && type_gate == LLM_FFN_PAR) {
        // GEGLU 路径
    } else {
        cur = ggml_gelu(ctx0, cur);
        cb(cur, "ffn_gelu", il);
    }
    break;
```

最后再完成 Down Projection 和 bias：

```cpp
if (down) {
    cur = build_lora_mm(down, cur);
}

if (down_b) {
    cb(cur, "ffn_down", il);
    cur = ggml_add(ctx0, cur, down_b);
}
```

原理与源码可以汇总为：

| 原理概念 | GPT-2 Small 中的形式 | llama.cpp 中的入口 |
|---|---|---|
| MLP Pre-Norm | `[T,768] → [T,768]` | `build_norm(..., LLM_NORM, ...)` |
| Up Projection | `[T,768] → [T,3072]` | `build_ffn()` 中 `build_lora_mm(up, cur)` + bias |
| GELU | `[T,3072] → [T,3072]` | `ggml_gelu()` |
| 无 gate | 不存在额外 gate Tensor | GPT-2 调用中的 `gate/gate_b/gate_s == NULL` |
| Down Projection | `[T,3072] → [T,768]` | `build_lora_mm(down, cur)` + bias |
| 第二次 Residual Add | `H_l + M_l` | `ggml_add(ctx0, cur, ffn_inp)` |

这些 C++ 调用用于构建 GGML 计算图，定义节点、依赖关系和 Tensor shape，并不立即执行数值计算。前面的回调输出才是计算图执行后的结果。

## 小结

本文介绍了 GPT-2 中 MLP 的作用与计算过程：

- Attention 在不同 Token 位置之间混合信息；MLP 使用共享参数，逐位置对包含上下文信息的 Hidden State 进行非线性变换。
- GPT-2 Small 使用无 gate 的 `768 → 3072 → GELU → 768` MLP。中间的 3072 维提供临时的计算工作区，GELU 在两次线性投影之间引入非线性。
- Down Projection 将非线性中间响应组合成与输入维度相同的 MLP 更新 `M_l [T,768]`。
