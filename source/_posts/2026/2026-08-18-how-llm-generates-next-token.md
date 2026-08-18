categories:
- AI

tags:
- 从零学大模型
- LLM
- GPT-2
- llama.cpp

title: 从零学大模型：LLM 如何逐个生成 Token？
---

当我们与 ChatGPT 对话，或让 Agent 完成任务时，背后发挥核心作用的都是 LLM（大语言模型）。文本生成是 LLM 最基础的能力，也是理解其工作原理的起点。

本文以 [GPT-2（Small）](https://huggingface.co/openai-community/gpt2) 为例，先从文本续写的整体过程入手，再解释自回归生成（Autoregressive generation）和单次预测，最后用 [llama.cpp](https://github.com/ggml-org/llama.cpp) 进行验证。

## 文本续写

![How are 续写为 you doing?](text-completion.svg)

就功能而言，可以把 LLM 看作一个文本续写系统：输入 `How are`，输出 `you doing?`。从外部看，整个续写过程像是一次完成的。

## 自回归生成

实际上，`you doing?` 由多个 Token 依次生成。Token 是模型处理文本的基本单位，通常对应一个文本片段。每轮根据已有的 Token 序列预测下一个 Token，再将它追加到序列中，进入下一轮，直到满足停止条件。

![you doing? 的三轮自回归生成过程](autoregressive-generation.svg)

需要注意，`" you"` 和 `" doing"` 的前导空格也是 Token 的一部分，因此 Token 并不等同于单词。

## 一次 Token 预测

以 GPT-2 第一次预测 `" you"` 为例，一次 Token 预测可以分为分词（Tokenize）、GPT-2 计算、采样（Sampling）和反分词（Detokenize）四个步骤：

![从 How are 预测下一个 Token " you"](single-token-prediction.svg)

### 分词

分词将 `How are` 划分为两个 Token，并将它们映射为词表（Vocabulary）中的整数编号，也就是 Token ID：

```text
"How"  → 2437
" are" → 389
```

因此，模型接收的 Token ID 序列是 `[2437, 389]`。这些整数后续还要转换为向量才能参与计算。

### GPT-2

GPT-2 接收 Token ID 序列，输出 50257 个 logits（原始预测分数）。每个 logit 对应词表中的一个 Token，表示它作为下一个 Token 的原始评分。

得到 logits 后，GPT-2 的前向计算（Forward Pass）就结束了。接下来由推理框架根据这些评分进行采样，选出下一个 Token ID。

### 采样

采样根据 logits 选择下一个 Token ID，可以通过 Temperature（温度）、Top-k 和 Top-p 等参数控制选择结果。本例将 Temperature 设为 0，以确定性方式选中 Token ID `345`。

即使 logits 相同，不同的采样参数也可能选出不同的 Token。因此，模型计算和 Token 选择是两个不同阶段。

### 反分词

反分词是分词的逆向转换：Token ID `345` 根据同一份词表还原为文本片段 `" you"`。

> **说明：**
> 生成的文本片段用于显示，Token ID 则直接追加到已有序列：`[2437, 389] + 345 → [2437, 389, 345]`。GPT-2 基于新序列继续预测，无须重新分词；不断重复这一过程，就形成了自回归生成。

## llama.cpp 实战

下面用 llama.cpp 实际观察分词结果、候选分数与采样结果，以及最终的续写结果。

GPT-2 与 llama.cpp 在这一过程中承担不同职责：

- **GPT-2**：包含模型结构和训练得到的参数，将 Token ID 序列转换为 logits。
- **llama.cpp**：加载 GGUF 中的模型与 Tokenizer（分词器）的相关信息，构建并执行计算图（Computation Graph），完成采样和文本输出。

### 环境准备

下面的实验基于 llama.cpp（版本标签：[`b10435`](https://github.com/ggml-org/llama.cpp/releases/tag/b10435)），需要预先安装 Git、CMake、cURL 和 C/C++ 编译器。

克隆代码并构建 `llama-completion` 和 `llama-server`：

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp
git checkout b10435

cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build \
  --target llama-completion llama-server \
  --config Release -j
```

接着从 [QuantFactory/gpt2-GGUF](https://huggingface.co/QuantFactory/gpt2-GGUF) 下载 GPT-2 Q8_0 GGUF 模型：

```bash
GPT2_MODEL=models/QuantFactory/gpt2-GGUF/gpt2.Q8_0.gguf
mkdir -p models/QuantFactory/gpt2-GGUF

curl -L --fail \
  -o "$GPT2_MODEL" \
  https://huggingface.co/QuantFactory/gpt2-GGUF/resolve/main/gpt2.Q8_0.gguf
```

### 查看分词结果

借助 `llama-completion`，可以查看输入文本的分词结果，包括 Token 及其对应的 ID：

```bash
./build/bin/llama-completion \
  -m "$GPT2_MODEL" \
  --prompt 'How are' \
  --predict 0 \
  --verbose-prompt \
  2>&1 |
  grep -E "llama_completion: (prompt:|number of tokens in prompt)| I +[0-9]+ -> '"
```

输出：

```text
0.00.366.307 I llama_completion: prompt: 'How are'
0.00.366.307 I llama_completion: number of tokens in prompt = 2
0.00.366.309 I   2437 -> 'How'
0.00.366.310 I    389 -> ' are'
```

### 查看候选分数与采样结果

先在一个终端启动 `llama-server`：

```bash
./build/bin/llama-server \
  -m "$GPT2_MODEL"
```

模型加载完成后，另开一个终端，请求生成一个 Token：

```bash
curl -sS http://127.0.0.1:8080/completion \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "How are",
    "n_predict": 1,
    "temperature": 0,
    "return_tokens": true,
    "n_probs": 3,
    "response_fields": ["content", "tokens", "completion_probabilities"]
  }'
```

省略响应中的 `bytes` 后，关键结果如下：

```json
{
  "content": " you",
  "tokens": [345],
  "completion_probabilities": [
    {
      "id": 345,
      "token": " you",
      "logprob": -1.0721638,
      "top_logprobs": [
        {"id": 345, "token": " you",  "logprob": -1.0721638},
        {"id": 356, "token": " we",   "logprob": -2.1492436},
        {"id": 262, "token": " the",  "logprob": -2.3353780}
      ]
    }
  ]
}
```

`tokens[0]` 表示最终选中的 Token ID，即 `345`；对应的文本片段是 `" you"`。`top_logprobs` 列出了本轮预测中排名靠前的候选 Token，其中的 `logprob`（对数概率）由 logits 转换而来，并非 GPT-2 直接输出的原始 logits。Temperature 为 0 时，llama.cpp 会确定性地选择排名第一的 Token。

### 查看续写结果

最后运行 `llama-completion`，从 `How are` 开始连续生成三个 Token：

```bash
./build/bin/llama-completion \
  -m "$GPT2_MODEL" \
  --prompt 'How are' \
  --predict 3 \
  --temp 0 \
  --log-verbosity 1
```

续写结果：

```text
How are you doing?
```

## 小结

本文以 `How are → you doing?` 为例，串起了 LLM 逐个生成 Token 的基本流程：

- `How are` 被分词为 `[2437, 389]`，第一次预测选中 Token ID `345`（`" you"`），连续预测后得到 `you doing?`。
- 一次 Token 预测依次经过分词、GPT-2 计算、采样和反分词；新 Token ID 会追加到已有序列，形成自回归生成。
- GPT-2 负责根据 Token ID 计算 logits，llama.cpp 负责模型执行、Token 选择和文本输出。
