categories:
- AI

tags:
- 从零学大模型
- LLM
- GPT-2
- llama.cpp

title: 从零学大模型：Self-Attention —— 多头注意力
---

![GPT-2 中 Self-Attention 的位置](gpt2-model-overview.svg)

上一篇[《Self-Attention —— 单头注意力》](/2026/08/single-head-self-attention)从一个 Attention Head（注意力头，以下简称 Head）的视角，跟踪了 Q、K、V、Causal Mask、Softmax 和 Value 加权求和。单个 Head 最终为每个 Token 位置产生一个 `D_h` 维输出；在 GPT-2 Small 中，对应的 shape 是 `[T,64]`。

但完整的 Self-Attention 需要产生 `[T,768]` 的 Attention 更新，才能与 GPT-2 Block 的 Residual Connection 主路径相加。中间缺少的部分正是 Multi-Head Attention（多头注意力）：GPT-2 如何并行计算多个 Head，再把它们重新组合成一个 `[T,768]` 的输出？

## 为什么需要多个 Head

对于同一个 Token 位置，单个 Head 只会产生一组 Attention 权重。这组权重决定了当前位置从前文各个位置读取多少信息，然后用同一组权重对 Value 进行加权求和。

但在理解一句话时，当前位置往往需要同时参考多种线索。例如，当 GPT-2 读到：

```text
The cat sat on the mat because it was
```

并准备预测下一个 Token 时，它可能需要同时关注：

- `it was`，判断局部的语法和常见搭配；
- `cat` 或 `mat`，推测 `it` 指代的对象；
- `because`，理解前后内容之间的因果关系。

如果只有一个 Head，这些线索需要共同影响同一组 Attention 权重。Multi-Head Attention 则提供多组不同的投影视角：每个 Head 都可以形成自己的 Attention 权重并汇总上下文，最后再把各个 Head 的结果合并起来。

可以把两者的区别简单理解为：

```text
单头：同一个位置 → 一组 Attention 权重 → 一份上下文结果
多头：同一个位置 → 多组独立的 Attention 权重 → 多份上下文结果 → 合并
```

这些“局部搭配”、“指代关系”和“因果关系”只是帮助理解的假想视角，并不表示训练时会为每个 Head 预先指定固定职责。

> **为什么使用 12 个 Head？**
>
> [GPT-2 论文](https://cdn.openai.com/better-language-models/language-models.pdf)将最小模型的 Hidden size 设为 768，[OpenAI 官方实现](https://github.com/openai/gpt-2/blob/master/src/model.py)进一步将 Head 数量设为 12，因此每个 Head 的维度为 `768 / 12 = 64`。
>
> [《Attention Is All You Need》](https://proceedings.neurips.cc/paper/7181-attention-is-all-you-need.pdf)指出，多头注意力可以让模型同时关注不同位置和不同表示子空间的信息。原论文也将每个 Head 的维度设为 64，并说明缩小单个 Head 的维度后，多头计算的总成本可以与一个全维度单头保持在相近水平。
>
> 因此，`12 × 64` 应理解为 GPT-2 Small 采用的一组架构配置，而不是 Attention 公式推导出的唯一答案。在 Hidden size 固定时，更多 Head 意味着每个 Head 的维度更小，需要在 Head 数量与单个 Head 的表示宽度之间权衡，并不是越多越好。

## 从一个 Head 到完整 Self-Attention

第 `l` 个 Block 的 Attention 输入仍记为 `Z_l [T,D]`，完整的 Attention 更新记为 `A_l [T,D]`：

```text
Z_l = LN_attn_l(X_l)       [T,D]
A_l = Attention_l(Z_l)     [T,D]
```

上一篇只展开了其中一个 Head，得到第 `h` 个 Head 的输出 `O_h [T,D_h]`。GPT-2 Small 同时计算 12 个这样的结果，再经过 Concat（拼接）和 Output Projection（输出投影）得到 `A_l`：

![GPT-2 Multi-Head Attention 的完整数据流](multi-head-attention-flow.svg)

单头注意力只是 Multi-Head Attention 的一个局部视角，而不是独立的模型阶段。下面沿图中的数据流依次展开：先看 GPT-2 如何一次产生全部 Head 所需的 Q、K、V，再看各个 Head 如何并行计算，并通过 Concat 和 Output Projection 合并结果。

## GPT-2 为什么使用 Fused QKV

Q、K、V 的线性投影都以 `Z_l` 为输入。Fused QKV（融合 QKV 投影）将这三次投影合并为一次：把三组权重和偏置沿输出维拼接，一次得到 `[T,3D]`，再拆分为 Q、K、V。

这只改变参数和计算的组织方式：Q、K、V 仍分别使用，参数量和 Attention 公式不变。**Fused QKV 的主要考虑是计算效率**：把三次共享同一输入的投影合并为一次矩阵乘法，可以减少算子调度和对 `Z_l` 的重复读取，也更利于高效使用底层矩阵乘法内核。

上一篇从单个 Head 的视角分别写出了 Q、K、V 投影。把 12 个 Head 合在一起看，整体 Q、K、V 都是 `[T,D]`：

```text
Q = Z_l W_Q + b_Q    [T,D]
K = Z_l W_K + b_K    [T,D]
V = Z_l W_V + b_V    [T,D]
```

其中，`W_Q` 可以看成 12 个 `[D,D_h]` 的 `W_Q^(h)` 沿输出维拼在一起；`W_K`、`W_V` 同理。GPT-2 进一步把三组整体参数合并为一组 Fused QKV 参数：

```text
W_QKV = Concat(W_Q, W_K, W_V)    [D,3D]
b_QKV = Concat(b_Q, b_K, b_V)    [3D]
```

于是，Q、K、V 可以通过一次线性投影同时得到：

```text
QKV = Z_l W_QKV + b_QKV    [T,3D]
```

对于 GPT-2 Small：

```text
[T,768] × [768,2304] + [2304]
→ QKV [T,2304]
```

## QKV 拆分与 Multi-Head View

GPT-2 Small 的 Hidden size 为 `D = 768`，Head 数量为 `H = 12`，所以每个 Head 的维度是：

```text
D_h = D / H = 768 / 12 = 64
```

得到 Fused QKV 后，图中的 Split（拆分）先沿最后一个维度取得 Q、K、V 三段，Multi-Head View（多头视图）再把每段组织成 12 个 64 维 Head：

```text
QKV [T,2304]
→ Q / K / V              各自 [T,768]
→ Multi-Head View        各自 [12,T,64]
```

这里并不是先把 `Z_l [T,768]` 切成 12 份，再把每一份交给一个 Head。每个 Head 都读取完整的 `Z_l`，但使用各自的 Q、K、V 投影参数，把输入映射到不同的 64 维表示子空间。

## 多个 Head 的并行计算

上一篇的单头公式对 `h = 0, 1, ..., 11` 都成立：

```text
O_h = softmax(Q_h K_h^T / sqrt(D_h) + M) V_h
```

这里的“并行”是指，底层会把 12 个 Head 组织在一起计算，而不是按照 `Head 0 → Head 1 → ...` 的顺序逐个执行。

12 个 Head 使用相同的 Causal Mask 规则，但各自的 Q、K、V 以及由此得到的 Attention 权重通常不同。所有 Head 的输出合在一起是 `[H,T,D_h]`；这让模型可以同时保留多组上下文读取结果，而不必把所有匹配关系压进一组权重。

## Concat：恢复 Hidden 维度

每个 Head 都产生一个 `[T,64]` 的输出：

```text
O_0, O_1, ..., O_11    每个 [T,64]
```

Concat 沿特征维依次拼接同一 Token 位置在 12 个 Head 中的输出：

```text
O_cat = Concat(O_0, O_1, ..., O_11)    [T,12 × 64] = [T,768]
```

Token 数量 `T` 没有改变。这里也不是把 12 个结果逐元素相加：相加仍然只会得到 64 维，Concat 则保留每个 Head 的 64 维结果，把它们组成一个 768 维向量。

以某个 Token 位置 `i` 为例：

```text
o_i^(0)  [64] ─┐
o_i^(1)  [64]  │
...            ├─ Concat → o_cat_i [768]
o_i^(11) [64] ─┘
```

Concat 本身没有训练参数，只负责重新组织各 Head 的输出。它恢复了 Hidden 维度，但还不是 GPT-2 最终使用的 Attention 更新。

## Output Projection：组合多个 Head

Concat 之后已经得到 `O_cat [T,768]`，但它只把 12 个 Head 的结果并排放置，并没有学习如何组合它们。如果直接将 `O_cat` 作为 Attention 更新，那么前 64 维只来自 Head 0，接下来的 64 维只来自 Head 1，以此类推。

GPT-2 使用训练得到的权重 `W_O` 和偏置 `b_O` 完成 Output Projection：

```text
A_l = O_cat W_O + b_O
```

对应 shape 为：

```text
O_cat    [T,768]
W_O      [768,768]
b_O      [768]
A_l      [T,768]
```

为了理解这一次矩阵乘法如何组合多个 Head，可以重新标出 `O_cat` 中原有的 Head 边界：

```text
O_cat = [O_0 | O_1 | ... | O_11]
```

再沿相同边界，将 `W_O` 中与这些输入维度对应的行分成 12 个 `[64,768]` 的子矩阵：

```text
          [ W_O^(0)  ]
          [ W_O^(1)  ]
W_O   =   [    ⋮     ]
          [ W_O^(11) ]
```

根据分块矩阵乘法：

```text
A_l
= O_0 W_O^(0) + O_1 W_O^(1) + ... + O_11 W_O^(11) + b_O
```

每个 `W_O^(h)` 都将对应 Head 的 64 维输出映射到全部 768 个输出维度，因此每个 Head 都能影响任意一个输出维度，最终的 `A_l` 也就能够组合 12 个 Head 的结果。

这里的分块只是数学上的等价写法；GPT-2 实际仍使用一组完整的 `W_O [768,768]` 执行一次 Output Projection，而不是分别计算 12 次。

## 完整 shape 主线

将前面的步骤连起来，可以得到一次 GPT-2 Multi-Head Attention 的逻辑 shape：

| 阶段 | 逻辑 shape | GPT-2 Small（`T=2`） |
|---|---|---|
| Attention 输入 `Z_l` | `[T,D]` | `[2,768]` |
| Fused QKV 输出 `QKV` | `[T,3D]` | `[2,2304]` |
| `Q` / `K` / `V` 多头视图 | 各自 `[H,T,D_h]` | 各自 `[12,2,64]` |
| Attention 分数 / 权重 | 各自 `[H,T,T]` | 各自 `[12,2,2]` |
| 各 Head 的输出 | `[H,T,D_h]` | `[12,2,64]` |
| Concat 结果 `O_cat` | `[T,D]` | `[2,768]` |
| Output Projection `A_l` | `[T,D]` | `[2,768]` |

这条主线中，Token 数量始终为 `T`。Concat 将多个 Head 合并回 Hidden size `D`，Output Projection 保持 `[T,D]`，并通过可学习参数组合多个 Head 的结果。

## llama.cpp 实战

下面使用 llama.cpp `b10435` 和 GPT-2 Q8_0 模型，核对参数 shape 与运行时 Tensor，再对照源码确认完整计算路径。基础环境和模型准备见[《LLM 如何逐个生成 Token？》](/2026/08/how-llm-generates-next-token/#环境准备)。

进入 llama.cpp 目录，设置模型路径，并确保调试程序已经构建：

```bash
cd llama.cpp

GPT2_MODEL=models/QuantFactory/gpt2-GGUF/gpt2.Q8_0.gguf

cmake --build build \
  --target llama-eval-callback \
  --config Release -j
```

### 核对多头参数

先从 GGUF 中读取 Hidden size、Head 数量，以及 Block 0 的 Fused QKV 和 Output Projection 参数的 shape：

```bash
.venv/bin/gguf-dump "$GPT2_MODEL" --json |
  jq '{
    hidden_size: .metadata["gpt2.embedding_length"].value,
    head_count: .metadata["gpt2.attention.head_count"].value,
    qkv_weight_shape: .tensors["blk.0.attn_qkv.weight"].shape,
    qkv_bias_shape: .tensors["blk.0.attn_qkv.bias"].shape,
    output_weight_shape: .tensors["blk.0.attn_output.weight"].shape,
    output_bias_shape: .tensors["blk.0.attn_output.bias"].shape
  }'
```

当前模型的输出为：

```json
{
  "hidden_size": 768,
  "head_count": 12,
  "qkv_weight_shape": [768, 2304],
  "qkv_bias_shape": [2304],
  "output_weight_shape": [768, 768],
  "output_bias_shape": [768]
}
```

`hidden_size: 768`、`head_count: 12` 对应 `D = 768`、`H = 12`，因此 `D_h = 64`。

Fused QKV 的权重和偏置分别是 `[768,2304]` 与 `[2304]`，对应 `W_QKV [D,3D]` 和 `b_QKV [3D]`，其中 `2304 = 3 × 768`。Output Projection 的参数是 `[768,768]` 与 `[768]`，对应 `W_O [D,D]` 和 `b_O [D]`，输出维度仍保持为 768。

### 核对多头合并的运行时 shape

对 `How are` 运行一次回调，并只保留 Block 0 中与多头主线相关的节点：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' \
  --flash-attn off \
  2>&1 |
  rg 'common_debug_cb_eval: +(wqkv_b-0|Qcur-0|Kcur-0|Vcur-0|kqv-0|kqv_out-0) ='
```

裁剪后的输出如下：

```text
wqkv_b-0       = {2304, 2, 1, 1}
Qcur-0         = {64, 12, 2, 1}
Vcur-0         = {64, 12, 2, 1}
Kcur-0         = {64, 12, 2, 1}
kqv-0          = {64, 2, 12, 1}
kqv_out-0      = {768, 2, 1, 1}
```

回调中的 `Vcur-0` 先于 `Kcur-0` 出现，是计算图的实际调度顺序；逻辑上仍按 Q、K、V 阅读。

llama.cpp / GGML 显示的维度顺序与前文使用的逻辑 shape 不同，下面逐项对应。为简洁起见，表中省略末尾为 `1` 的维度：

| 运行时节点 | 运行时 shape | 逻辑含义 |
|---|---|---|
| `wqkv_b-0` | `{2304,2}` | Fused QKV `[2,2304]` |
| `Qcur-0` / `Kcur-0` / `Vcur-0` | 各自 `{64,12,2}` | Q、K、V 的多头视图，各自 `[12,2,64]` |
| `kqv-0` | `{64,2,12}` | 12 个 Head 的输出 `[12,2,64]` |
| `kqv_out-0` | `{768,2}` | Concat 后的 `O_cat [2,768]` |

`Qcur-0`、`Kcur-0` 和 `Vcur-0` 显示，Fused QKV 被组织成了 12 个 64 维 Head；`kqv_out-0` 的 `{768,2}` 则说明 12 个 Head 的结果已经合并回 768 维。

当前源码没有给 Output Projection 的结果设置独立、稳定的回调名，但可以用参数名定位 Block 0 的矩阵乘法和 bias 相加：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' \
  --flash-attn off \
  2>&1 |
  rg 'common_debug_cb_eval: .*blk\.0\.attn_output\.(weight|bias)'
```

当前输出为：

```text
common_debug_cb_eval:                  node_28 = (f32)    MUL_MAT(blk.0.attn_output.weight{768, 768, 1, 1}, kqv_out-0{768, 2, 1, 1}}) = {768, 2, 1, 1}
common_debug_cb_eval:                  node_29 = (f32)        ADD(node_28{768, 2, 1, 1}, blk.0.attn_output.bias{768, 1, 1, 1}}) = {768, 2, 1, 1}
```

第一行对应 `O_cat [2,768]` 乘以 `W_O [768,768]`，第二行再加上 `b_O [768]`，直接得到 Output Projection 的 `A_0 [2,768]`。`node_28` 和 `node_29` 是自动生成的节点名，可能随计算图变化；这里通过稳定的 `blk.0.attn_output.weight` 和 `blk.0.attn_output.bias` 识别这两个操作。

### 对比两个 Head 的 Attention 权重

继续保留 `kq_soft_max-0` 的数值：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' \
  --flash-attn off \
  2>&1 |
  sed -n '/kq_soft_max-0 =/,/sum =/p'
```

`kq_soft_max-0` 的运行时 shape 是 `{256,2,12,1}`。输出按 Head 分组，每个 Head 包含 Query 0 和 Query 1 两行，每行前两个数对应本次输入的两个有效 Key 位置。下面取出 Head 0 和 Head 1。

对于 Query 0 / `"How"`，Causal Mask 只允许读取第一个位置，所以两个 Head 的有效权重都是 `[1.0000,0.0000]`。更有区分度的是 Query 1 / `" are"`：

| Head | 对 `"How"` 的权重 | 对 `" are"` 的权重 |
|---:|---:|---:|
| Head 0 | 0.9534 | 0.0466 |
| Head 1 | 0.0049 | 0.9951 |

在 Block 0 的这次输入中，两个 Head 面对相同输入和相同可见范围，却得到明显不同的 Attention 权重。这直接显示它们不是对同一单头结果的简单复制；但只凭这两个数值，还不能给它们赋予固定的语言学含义。

### 对照源码

GPT-2 在 [`llama_model_gpt2::graph::graph()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/models/gpt2.cpp#L89-L97) 中先调用 `build_qkv()`，再把 Q、K、V 和缩放因子传入 `build_attn()`：

```cpp
auto [Qcur, Kcur, Vcur] = build_qkv(model.layers[il], cur,
        n_embd_head, n_head, n_head_kv, il);

cur = build_attn(inp_attn,
        model.layers[il].wo, model.layers[il].wo_b, model.layers[il].wo_s,
        Qcur, Kcur, Vcur, nullptr, nullptr, nullptr,
        1.0f/sqrtf(float(n_embd_head)), il);
```

`n_head_kv` 表示 Key/Value Head 数；GPT-2 中它与 `n_head` 相同，都是 12，因此 Q、K、V 都按 12 个 Head 组织。

在 [`build_qkv()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/llama-graph.cpp#L1592-L1665) 中，GPT-2 进入 Fused QKV 分支。源码先完成一次矩阵乘法和 bias 相加，再通过三个带不同 offset 的 `ggml_view_3d()` 取得 Q、K、V：

```cpp
ggml_tensor * qkv = build_lora_mm(layer.wqkv, cur, layer.wqkv_s);
qkv = ggml_add(ctx0, qkv, layer.wqkv_b);

Qcur = ggml_view_3d(ctx0, qkv, n_embd_head, n_head,    n_tokens,
        /* ... */, 0);
Kcur = ggml_view_3d(ctx0, qkv, n_embd_head, n_head_kv, n_tokens,
        /* ... */, ggml_row_size(qkv->type, n_embd_q));
Vcur = ggml_view_3d(ctx0, qkv, n_embd_head, n_head_kv, n_tokens,
        /* ... */, ggml_row_size(qkv->type, n_embd_q + n_embd_kv));
```

`ggml_view_3d()` 没有再次计算投影，也没有复制出三份新结果；它通过 shape、stride 和 offset 解释 Fused QKV 中的不同区域，并把 Head 维显式组织出来。

关闭 Flash Attention 后，[`build_attn_mha()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/llama-graph.cpp#L2566-L2622) 会在包含 Head 维的 Tensor 上完成上一篇已经验证的 `kq → kq_soft_max → kqv`。得到所有 Head 的 `kqv` 后，同一函数继续完成 Head 合并：

```cpp
cur = ggml_permute(ctx0, kqv, 0, 2, 1, 3);
cur = ggml_cont_2d(ctx0, cur,
        cur->ne[0]*cur->ne[1], cur->ne[2]*cur->ne[3]);
```

这里没有一个名为 `concat` 的 GGML 节点。`ggml_permute()` 先把 Head 维移到适合拼接的位置，`ggml_cont_2d()` 再把结果整理成连续的二维 Tensor `[D,T]`；它在逻辑上对应 `Concat(O_0,...,O_11) [T,D]`。

最后，[`build_attn()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/llama-graph.cpp#L2745-L2817) 使用 `wo` 和 `wo_b` 完成 Output Projection：

```cpp
ggml_tensor * cur = build_attn_mha(/* ... */);

cur = build_lora_mm(wo, cur, wo_s);
cur = ggml_add(ctx0, cur, wo_b);
```

原理与源码可以汇总为：

| 原理概念 | GPT-2 Small 中的形式 | llama.cpp 中的入口 |
|---|---|---|
| Fused QKV | `[T,768] → [T,2304]` | `build_qkv()` 中 `build_lora_mm(layer.wqkv, cur, ...)` |
| 拆分 Q / K / V | `[T,2304] → 3 × [12,T,64]` | 三个不同 offset 的 `ggml_view_3d()` |
| 12 个 Head 的 Attention 计算 | `[12,T,64] → [12,T,T] → [12,T,64]` | `build_attn_mha()` 中 `kq → kq_soft_max → kqv`（上一篇已验证） |
| Concat | `[12,T,64] → [T,768]` | `ggml_permute()` + `ggml_cont_2d()` |
| Output Projection | `[T,768] → [T,768]` | `build_attn()` 中 `build_lora_mm(wo, ...)` + bias |

这些 C++ 调用只是在构建 GGML 计算图，定义节点、依赖关系和 Tensor shape，并未立即执行数值计算。前面的回调输出才来自后端执行后的 Tensor；完整的建图与执行调用链留到第 11 篇。

## 小结

本文从完整 Self-Attention 的视角，说明了 GPT-2 如何并行计算多个 Head，并将它们重新组合为 Attention 更新：

- Multi-Head Attention 让 12 个 Head 使用各自的投影参数读取同一个 `Z_l [T,768]`；它们是并行分支，不是 12 个先后阶段。
- GPT-2 用一次 Fused QKV 投影得到 `[T,2304]`，再把 Q、K、V 分别组织成 `[12,T,64]`。
- 12 个 Head 的结果经 Concat 回到 `[T,768]`，Output Projection 再通过线性变换混合这些特征，得到完整的 Attention 更新 `A_l [T,768]`。
