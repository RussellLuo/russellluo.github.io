categories:
- AI

tags:
- 从零学大模型
- LLM
- GPT-2
- llama.cpp

title: 从零学大模型：Token ID 如何变成向量？
---

在上一篇[《文本如何变成 Token ID？》](/2026/08/how-text-becomes-token-ids)中，`How are` 经过分词后得到 Token ID 序列 `[2437, 389]`。但 Token ID 只是词表中的整数编号，不能直接参与 GPT-2 的向量和矩阵计算。

本文先打开 GPT-2 的模型黑盒，了解 Embedding（嵌入）在完整前向过程中的位置；再说明 Token Embedding 和 Position Embedding 如何得到 Initial Hidden State（初始隐藏状态）；最后用 llama.cpp 查看 GGUF 中的真实参数和运行时结果。

## GPT-2 内部的整体流程

GPT-2 接收 Token ID 序列，依次经过 Embedding、12 个 Transformer Block 和 LM Head，最终得到 logits：

![GPT-2 从 Token ID 到 logits 的内部流程](gpt2-model-overview.svg)

图中蓝色的 Embedding 是本文聚焦的位置；后续文章将依次展开 Transformer Block 的整体骨架、Self-Attention、MLP，以及输出阶段的 Final LayerNorm 与 LM Head。为保持母图简洁，Final LayerNorm 没有单独画出。采样位于 GPT-2 模型边界之外，将在模型内部流程讲完后单独展开。

## 从 Embedding 到 Initial Hidden State

本文从 `[2437, 389]` 出发，展开整体流程图中的 Embedding。具体来说，GPT-2 分别根据 Token ID 和 Position ID 查询两张 Embedding Table，再将两个查表结果逐元素相加，得到 Initial Hidden State，即第一个 GPT-2 Block 的输入。整个过程如下：

![Token Embedding 与 Position Embedding 相加得到 Initial Hidden State](embedding-flow.svg)

图中的符号含义如下：

| 符号 | 含义 | GPT-2 Small / 本文示例 |
|---|---|---:|
| `V` | 词表大小 | 50257 |
| `D` | Hidden / Embedding size | 768 |
| `C` | 最大位置数 | 1024 |
| `T` | 当前输入的 Token 数量 | 2 |

## Token Embedding

Token ID 是 Token 在词表中的整数编号。例如：

```text
"How"  → 2437
" are" → 389
```

数字 `2437` 的大小不表示 `"How"` 的语义，也不能把相邻的 Token ID 理解为语义相近。Token ID 在模型中的作用更像数组下标：模型用它从 Token Embedding Table 中取出一个向量。

**Embedding Table 与查表**

Token Embedding Table 可以理解为包含 `V` 行、每行 `D` 个数的参数表：

```text
Token IDs [T]
→ 在 Token Embedding Table [V, D] 中查表
→ Token Embedding [T, D]
```

设 Token Embedding Table 为 `E_token`，第 `i` 个 Token ID 为 `id_i`，查表过程可以写成：

```text
X_token[i] = E_token[id_i]
```

对 `[2437, 389]` 来说：

```text
E_token[2437] → "How"  对应的 768 维向量
E_token[389]  → " are" 对应的 768 维向量
```

两个向量按照输入顺序排列，得到：

```text
Token IDs         [2]
→ Token Embedding [2, 768]
```

这个过程叫做 Embedding Lookup（Embedding 查表）。它不是把 `2437` 和 `389` 当作普通数字代入某个公式，而是根据它们选择参数表中的两个向量。

**两种 shape 表示**

shape（形状）表示 Tensor（张量）各个维度的大小。本文在原理部分使用更符合阅读直觉的 shape 顺序：

```text
[Token 数量, Hidden 维度] = [T, D]
```

在后文使用的 llama.cpp / GGML 中，同一个 Tensor 通常显示为：

```text
{Hidden 维度, Token 数量} = {D, T}
```

因此，下面两种写法描述的是同一个 Token Embedding：

```text
数学视角：[2, 768]
GGML 视角：{768, 2}
```

维度顺序不同，不代表模型结构不同。

## Position Embedding

Token Embedding 只由 Token ID 决定。同一个 Token 无论出现在第几个位置，都会查到同一个 Token Embedding 向量。

但文本顺序会影响含义。例如：

```text
dogs chase cats
cats chase dogs
```

两个句子包含相同的单词，但顺序不同，追逐者和被追逐者也随之交换。

为了让模型知道每个 Token 位于序列中的什么位置，GPT-2 还会查询 Position Embedding Table。对于同一个 Token ID `id`，它出现在位置 `0` 和位置 `2` 时，Token Embedding 相同，但加入的 Position Embedding 不同：

```text
E_token[id] + E_position[0]
E_token[id] + E_position[2]
```

因此，加入 Position Embedding 后，同一个 Token 出现在不同位置时会得到不同的 Initial Hidden State。Position Embedding 本身不直接表示具体语义，它只是把位置信息加入模型输入；后续 Transformer Block 再结合上下文计算每个位置的表示。

GPT-2 Small 的 Position Embedding Table 包含 1024 个位置，每个位置也是一个 768 维向量：

```text
Position IDs [T]
→ 在 Position Embedding Table [C, D] 中查表
→ Position Embedding [T, D]
```

`How are` 是一段没有历史上下文的新输入文本，因此两个 Token 的位置编号依次是 `0` 和 `1`：

| 输入位置 | Token ID | Token | Position ID |
|---:|---:|---|---:|
| 0 | 2437 | `How` | 0 |
| 1 | 389 | ` are` | 1 |

Position ID 和 Token ID 是两套不同的编号：

- Token ID 用来查询 Token Embedding Table，表示“当前是什么 Token”。
- Position ID 用来查询 Position Embedding Table，表示“当前位于哪里”。

GPT-2 的 Position Embedding 通过训练学习得到，并使用绝对位置编号。这里的“绝对”表示每个位置使用自己的编号，例如 `0、1、2`。

## Initial Hidden State

Token Embedding 和 Position Embedding 的 shape 相同，GPT-2 将它们逐元素相加：

```text
Token Embedding        [T, D]
+ Position Embedding   [T, D]
= Initial Hidden State [T, D]
```

对序列中的第 `i` 个位置：

```text
X_0[i] = E_token[id_i] + E_position[pos_i]
```

下面用 3 维向量演示相加过程。数值仅用于说明，不是 GPT-2 的真实参数：

```text
Token Embedding       [ 0.20, -0.10,  0.50]
Position Embedding    [ 0.01,  0.02, -0.03]
                      ---------------------
Initial Hidden State  [ 0.21, -0.08,  0.47]
```

GPT-2 Small 实际使用 768 维向量。对于 `How are`：

```text
Token Embedding        [2, 768]
+ Position Embedding   [2, 768]
= Initial Hidden State [2, 768]
```

> **为什么选择相加？**
>
> 这是 GPT-2 延续 Transformer 的架构选择。相加可以在不改变 Hidden size 的情况下，将位置信息加入 Token 表示，使结果直接进入后续 Transformer Block。它不是唯一方案，而是一种保持模型主干维度统一的简洁设计。

## Embedding 参数从哪里来

Token Embedding Table 和 Position Embedding Table 都是 GPT-2 在训练过程中学习得到的模型参数。推理时，推理框架不会重新训练或随机生成它们，而是从模型文件中加载训练好的参数。

从训练到查表的过程可以概括为：

```text
训练阶段：得到两张 Embedding Table
    ↓ 导出并保存
模型文件：保存训练得到的参数
    ↓ 推理框架加载
推理运行时：加载为两个参数 Tensor
    ↓ 分别根据 Token ID / Position ID 查表
查表结果：Token Embedding / Position Embedding
```

本文实战使用的模型文件格式是 GGUF。转换为 GGUF 后，GPT-2 中的两个 Embedding 参数对应为：

```text
transformer.wte → token_embd.weight
transformer.wpe → position_embd.weight
```

GGUF 使用元数据保存模型架构和相关配置，用 Tensor 保存 Embedding Table 等训练参数。加载模型时，llama.cpp 会读取这些 Tensor，供后续查表使用。

## llama.cpp 实战

下面使用 llama.cpp `b10435` 和 GPT-2 Q8_0 模型，查看 GGUF 中的 Embedding 参数、运行时操作与 shape，以及实际 Tensor 数值。基础环境准备见[《LLM 如何逐个生成 Token？》](/2026/08/how-llm-generates-next-token/#环境准备)，`gguf-dump` 的安装方式见[《文本如何变成 Token ID？》](/2026/08/how-text-becomes-token-ids/#查看-GGUF-中的-Tokenizer-数据)。

进入 llama.cpp 目录，设置模型路径，并构建本篇使用的工具：

```bash
cd llama.cpp

GPT2_MODEL=models/QuantFactory/gpt2-GGUF/gpt2.Q8_0.gguf

cmake --build build \
  --target llama-eval-callback \
  --config Release -j
```

### 查看 GGUF 中的 Embedding 参数

模型文件名中的 `Q8_0` 表示部分参数采用 Q8_0 量化格式保存，具体 Tensor 的类型仍需查看 GGUF。

使用 `gguf-dump` 读取模型元数据和两个 Embedding Tensor，再用 `jq` 只保留本篇需要的字段：

```bash
.venv/bin/gguf-dump "$GPT2_MODEL" --json |
  jq '{
    model: {
      architecture: .metadata["general.architecture"].value,
      blocks: .metadata["gpt2.block_count"].value,
      context: .metadata["gpt2.context_length"].value,
      embedding: .metadata["gpt2.embedding_length"].value
    },
    tensors: {
      token_embedding: (
        .tensors["token_embd.weight"] | {shape, type}
      ),
      position_embedding: (
        .tensors["position_embd.weight"] | {shape, type}
      )
    }
  }'
```

整理后的输出如下（只调整了 JSON 的换行）：

```json
{
  "model": {
    "architecture": "gpt2",
    "blocks": 12,
    "context": 1024,
    "embedding": 768
  },
  "tensors": {
    "token_embedding": {
      "shape": [768, 50257],
      "type": "Q8_0"
    },
    "position_embedding": {
      "shape": [768, 1024],
      "type": "F32"
    }
  }
}
```

这份静态 GGUF 数据验证了前面的模型配置：

- `token_embd.weight` 的 GGML shape 是 `{768,50257}`，数学语义是 `[50257,768]`。
- `position_embd.weight` 的 GGML shape 是 `{768,1024}`，数学语义是 `[1024,768]`。
- Token Embedding Table 使用 Q8_0，Position Embedding Table 使用 F32，说明同一 GGUF 文件中的 Tensor 可以使用不同类型。

### 查看 Embedding 的计算过程与 shape

`gguf-dump` 只能查看模型文件中的静态参数。要观察 `How are` 实际进入计算图后的 Tensor，可以使用 `llama-eval-callback`。

这个调试程序默认会打印大量中间 Tensor。下面只筛选 Embedding 阶段的三个节点：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' 2>&1 |
  rg 'common_debug_cb_eval: +(embd|pos_embd|inpL)'
```

整理后的关键输出如下：

```text
common_debug_cb_eval: embd = (f32) GET_ROWS(
  token_embd.weight{768, 50257, 1, 1},
  inp_tokens{2, 1, 1, 1}) = {768, 2, 1, 1}
common_debug_cb_eval: pos_embd = (f32) GET_ROWS(
  position_embd.weight{768, 1024, 1, 1},
  leaf_5{2, 1, 1, 1}) = {768, 2, 1, 1}
common_debug_cb_eval: inpL = (f32) ADD(
  embd{768, 2, 1, 1},
  pos_embd{768, 2, 1, 1}) = {768, 2, 1, 1}
```

其中 `leaf_5` 对应 Position ID 输入。

这三行分别对应：

1. `GET_ROWS(token_embd.weight, inp_tokens)` 根据 `[2437, 389]` 查询 Token Embedding。
2. `GET_ROWS(position_embd.weight, leaf_5)` 根据 `[0, 1]` 查询 Position Embedding。
3. `ADD(embd, pos_embd)` 把两个 `{768,2}` Tensor 相加，得到 `{768,2}` 的 `inpL`。

`inpL` 就是进入第一个 GPT-2 Block 的 Initial Hidden State。日志还显示，查表结果 `embd` 是参与后续计算的 F32 Tensor。

### 查看 Embedding 与 Initial Hidden State 的数值

`llama-eval-callback` 还会在节点信息后打印 Tensor 数值。下面使用 `-A 6` 保留每个目标节点后面的六行：

```bash
./build/bin/llama-eval-callback \
  -m "$GPT2_MODEL" \
  --prompt 'How are' 2>&1 |
  rg -A 6 --context-separator '' \
  'common_debug_cb_eval: +(embd|pos_embd|inpL) ='
```

整理后的数值部分如下：

```text
embd:
[
  [-0.0483,  0.0604,  0.0587, ...,  0.1476,  0.0712,  0.0738],
  [ 0.0760,  0.0564,  0.0491, ...,  0.0599, -0.0559,  0.0839]
]

pos_embd:
[
  [-0.0188, -0.1974,  0.0040, ..., -0.0430,  0.0283,  0.0545],
  [ 0.0240, -0.0538, -0.0948, ...,  0.0342,  0.0102, -0.0002]
]

inpL:
[
  [-0.0671, -0.1370,  0.0627, ...,  0.1045,  0.0995,  0.1283],
  [ 0.1000,  0.0026, -0.0458, ...,  0.0941, -0.0457,  0.0837]
]
```

每个 Tensor 都有两行，分别对应序列位置 `0` 的 `"How"` 和位置 `1` 的 `" are"`。每行实际包含 768 个值，调试输出只展示前 3 个和后 3 个。

不同计算后端的最后几位可能略有差异，但不影响这里的逐元素相加关系。

### 对照 Embedding 源码

GPT-2 在 [`load_arch_tensors()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/models/gpt2.cpp#L15-L29) 中声明两个参数 Tensor：

```cpp
tok_embd = create_tensor(
    tn(LLM_TENSOR_TOKEN_EMBD, "weight"),
    {n_embd, n_vocab}, 0);

pos_embd = create_tensor(
    tn(LLM_TENSOR_POS_EMBD, "weight"),
    {n_embd, n_ctx_train}, 0);
```

代入当前 GPT-2 Small 的配置：

```text
tok_embd → {768, 50257}
pos_embd → {768, 1024}
```

在 [`llama_model_gpt2::graph::graph()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/models/gpt2.cpp#L58-L78) 中，Embedding 主路径是：

```cpp
inpL = build_inp_embd(model.tok_embd);

ggml_tensor * inp_pos = build_inp_pos();

pos = ggml_get_rows(ctx0, model.pos_embd, inp_pos);

inpL = ggml_add(ctx0, inpL, pos);
```

其中，通用的 [`build_inp_embd()`](https://github.com/ggml-org/llama.cpp/blob/b10435/src/llama-graph.cpp#L2266-L2353) 为 Token ID 创建输入 Tensor，再构造查表节点：

```cpp
inp->tokens = ggml_new_tensor_1d(
    ctx0, GGML_TYPE_I32, ubatch.n_tokens);

cur = ggml_get_rows(ctx0, tok_embd, inp->tokens);
```

因此，从源码到运行结果可以连成同一条路径：

```text
inp_tokens {2}
→ ggml_get_rows(token_embd.weight)
→ embd {768,2}

positions {2}
→ ggml_get_rows(position_embd.weight)
→ pos_embd {768,2}

embd {768,2} + pos_embd {768,2}
→ inpL {768,2}
```

这里的 `ggml_get_rows()` 和 `ggml_add()` 首先构造计算图节点；真正的数值计算在实际执行阶段完成。`llama-eval-callback` 展示的是这些节点执行后的 Tensor 类型、shape 和部分数值，计算图与实际执行的完整边界将在后续文章中单独介绍。

## 小结

本文以 `[2437, 389]` 为例，说明了 Token ID 如何变成 GPT-2 的输入向量：

- Token ID 只是词表中的整数编号；GPT-2 将它作为下标，查询训练得到的 Token Embedding Table。
- GPT-2 同时根据 Position ID 查询 Position Embedding，为每个 Token 加入位置信息。
- Token Embedding 与 Position Embedding 逐元素相加，得到 Initial Hidden State。

得到的 `inpL` 会进入第一个 GPT-2 Block，成为后续 12 层计算的起点。
