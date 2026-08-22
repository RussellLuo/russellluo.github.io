categories:
- AI

tags:
- 从零学大模型
- LLM
- GPT-2
- llama.cpp

title: 从零学大模型：文本如何变成 Token ID？
---

在上一篇[《LLM 如何逐个生成 Token？》](/2026/08/how-llm-generates-next-token)中，`How are` 经过分词后得到 Token ID 序列 `[2437, 389]`。那么，Tokenizer（分词器）是如何完成这一步的？

本文先介绍 Token、Token ID 和词表，再说明文本与 Token ID 如何相互转换，最后用 llama.cpp 查看真实的 Token、预切分规则、词表和合并规则。

## Token、Token ID 与词表

GPT-2 模型本身不直接处理字符串。文本进入模型计算之前，Tokenizer 会依据固定规则完成下面的转换：

![How are 转换为 Token ID 2437 和 389](tokenization.svg)

这里的 `" are"` 包含一个前导空格。这个空格不会被丢弃，而是输入文本的一部分。

### Token 不等于单词

Token 是模型处理文本时使用的基本单位。在 GPT-2 的词表中，它可能是完整单词，也可能只是单词的一部分：

```text
unbelievable!
↓
"un" + "bel" + "iev" + "able" + "!"

"你好"
↓
[19526, 254, 25001, 121]
```

它还可能包含前导空格、标点或换行。`你好` 只有两个 Unicode 字符，在这个 GPT-2 Tokenizer 中却对应四个 Token ID。对于中文等非 ASCII 文本，一个 Token 甚至可能只对应某个 UTF-8 字节序列的一部分，单独显示时不一定是完整字符。

因此，Token 不能简单等同于“单词”或“字符”，而是 Tokenizer 根据固定规则得到的文本片段。

### 词表保存 Token 与 ID 的对应关系

词表（Vocabulary）可以看作一张固定的映射表，其中每个 Token 都有一个整数编号，也就是 Token ID。

按照文本中的先后顺序，`How are you doing?` 对应下面的 Token ID 序列：

```text
"How are you doing?"
→ [2437, 389, 345, 1804, 30]
```

但在词表中，这些 Token 按照 Token ID 排列在不同位置：

| Token ID | Token |
|---:|---|
| 0 | `!` |
| … | … |
| 30 | `?` |
| … | … |
| 345 | `Ġyou` |
| 389 | `Ġare` |
| … | … |
| 1804 | `Ġdoing` |
| … | … |
| 2437 | `How` |
| … | … |
| 50256 | `<\|endoftext\|>` |

省略号表示未展示的词表项；Token 在句子中的顺序与它在词表中的位置无关。表中的 `Ġ` 对应前导空格，这种表示方式将在后面的“字节级映射”中说明。

## GPT-2 的 Byte-level BPE

BPE 是 Byte Pair Encoding（字节对编码）的缩写。GPT-2 使用 Byte-level BPE（字节级 BPE）将文本转换成 Token ID。一次编码可以概括为：

![How are 的 Byte-level BPE 编码过程](byte-level-bpe.svg)

### 预切分

Tokenizer 先用一条固定的文本匹配规则（正则表达式）扫描输入，将内容大致划分为：

- 连续的字母，包括汉字等 Unicode 字母
- 连续的数字
- 连续的标点或其他符号
- 连续的空白
- 常见的英文缩写后缀，如 `'s`、`'t`、`'re`

其中，字母、数字或符号片段可以带上紧邻其前的一个普通空格。例如：

```text
How are
↓
"How" + " are"
```

这也是 `"are"` 和 `" are"` 可能得到不同 Token ID 的原因。在当前词表中，不带空格的 `"are"` 是 Token ID `533`，带空格的 `" are"` 则是 Token ID `389`。

预切分只负责划分片段，并不直接决定最终 Token。

### 字节级映射

GPT-2 先把每个片段表示为 UTF-8 字节，再通过一张可逆映射将每个字节变成便于处理的字符。常见例子包括：

```text
空格 0x20 → Ġ
换行 0x0A → Ċ
```

所以 `" are"` 在 BPE 内部会从下面四个初始符号开始：

```text
Ġ a r e
```

这种设计让 GPT-2 可以从字节层面表示不同语言和符号，而不必为每个 Unicode 字符准备一个基础 Token。代价是一个非 ASCII 字符可能被拆到多个 Token 中，单个 Token 文本片段不一定能独立解码成完整的 Unicode 字符。

> **为什么还需要预切分？**
>
> 预切分先确定哪些内容属于同一个 BPE 处理片段；字节级映射则只负责把片段转换成可逆的字符表示，不会重新划分片段。对于 `How are`，BPE 会分别在 `"How"` 和 `" are"` 内部尝试合并，不能跨越两个片段的边界。

### BPE 合并

BPE 合并规则（merges）规定哪些相邻符号可以合并。每条规则在数组中的位置就是 rank（优先级）。BPE 只比较同一片段中当前相邻的候选；rank 越小的规则越先执行。

`How` 从三个初始符号开始：

```text
H o w
↓  o + w → ow        rank 66
H ow
↓  H + ow → How      rank 2181
How
```

`" are"` 的合并过程则是：

```text
Ġ a r e
↓  Ġ + a → Ġa        rank 1
Ġa r e
↓  r + e → re        rank 4
Ġa re
↓  Ġa + re → Ġare    rank 133
Ġare
```

如果一个片段不能继续合并，它就会保留为多个较小 Token。前面的 `unbelievable` 被拆成 `un`、`bel`、`iev` 和 `able`，正是这个过程的结果。

### 查询词表

BPE 合并结束后，Tokenizer 用每个 Token 查询前面介绍的词表：`How` 对应 Token ID `2437`，`Ġare` 对应 Token ID `389`。查询结果按照原有顺序组成 Token ID 序列 `[2437, 389]`。

GPT-2 的词表与合并规则是配套生成的，因此 BPE 合并结果能够在词表中找到。

> **词表和合并规则从哪里来？**
>
> 词表和合并规则在 Tokenizer 训练阶段根据训练语料确定，后续编码文本时保持不变。它们是 Tokenizer 的数据，不是 GPT-2 用于模型计算的神经网络权重。

## 反分词

在 `How are → you doing?` 的续写过程中，GPT-2 在 `How are` 后依次生成了 Token ID `345`、`1804` 和 `30`。这些 ID 不需要再次分词；要把它们显示为可读文本，需要执行相反的转换：反分词（Detokenize）。

![Token ID 345、1804 和 30 还原为 you doing?](detokenization.svg)

`Ġyou` 和 `Ġdoing` 中的 `Ġ` 都会还原成前导空格，而 `?` 不带前导空格。因此，这三个 Token 依次拼接后的反分词结果是 `" you doing?"`。它与原输入拼接后，得到完整文本 `"How are you doing?"`。

这个过程不会倒着执行 BPE 合并规则，只需根据 ID 查回 Token 文本片段，再逆转字节级映射并拼接结果。

对于英文 ASCII 文本，单个 Token 通常可以直接显示；而对于中文等非 ASCII 文本，单个 Token 可能只包含一个 UTF-8 字符的部分字节。流式输出时，推理框架需要先积累这些字节，才能显示完整字符，不能假设每个 Token 都能独立解码为完整的 Unicode 文本。

## llama.cpp 实战

下面使用 llama.cpp `b10435` 和 GPT-2 Q8_0 模型，验证 `How are → [2437, 389]`，查看 GPT-2 的预切分规则，以及 GGUF 中真实的词表与 BPE 合并规则。基础环境准备见[《LLM 如何逐个生成 Token？》](/2026/08/how-llm-generates-next-token/#环境准备)。

进入 llama.cpp 目录，设置模型路径，并构建本篇使用的工具：

```bash
cd llama.cpp

GPT2_MODEL=models/QuantFactory/gpt2-GGUF/gpt2.Q8_0.gguf

cmake --build build \
  --target llama-tokenize \
  --config Release -j
```

### 查看 Token ID 与文本片段

运行 `llama-tokenize`：

```bash
./build/bin/llama-tokenize \
  -m "$GPT2_MODEL" \
  --no-bos \
  --log-verbosity 0 \
  --prompt 'How are'
```

输出：

```text
  2437 -> 'How'
   389 -> ' are'
```

`--no-bos` 表示不添加 BOS Token。输出共有两个 Token：`" are"` 的前导空格属于第二个 Token，两个 Token ID 分别是 `2437` 和 `389`。

再观察一个不能按完整单词切分的例子：

```bash
./build/bin/llama-tokenize \
  -m "$GPT2_MODEL" \
  --no-bos \
  --log-verbosity 0 \
  --prompt 'unbelievable!'
```

输出：

```text
   403 -> 'un'
  6667 -> 'bel'
 11203 -> 'iev'
   540 -> 'able'
     0 -> '!'
```

这说明 Token 既可以是单词片段，也可以是标点。

`llama-tokenize` 默认启用 `--escape`，会解析 `\n` 等转义序列。把输入文本改成 `'How\nare'`，可以观察到换行对应 Token ID `198`，换行后的 `"are"` 对应 ID `533`，而不是带前导空格的 `389`。

### 查看 GPT-2 的预切分规则

`llama-tokenize` 展示的是经过全部分词步骤得到的最终 Token，不会直接输出预切分产生的中间片段。要查看 GPT-2 使用的具体预切分规则，可以检查 llama.cpp 源码：

```bash
rg -n -A 1 'GPT2 system regex' src/unicode.cpp
```

输出：

```text
214:// GPT2 system regex:  's|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+
215-static std::vector<size_t> unicode_regex_split_custom_gpt2(const std::string & text, const std::vector<size_t> & offsets) {
```

其中，`\p{L}`、`\p{N}` 和 `[^\s\p{L}\p{N}]` 分别匹配字母、数字和其他符号；前面的 ` ?` 表示可以带上一个普通空格，其他分支用于匹配英文缩写后缀和空白。这与前面“预切分”小节概括的规则一致。

### 查看 GGUF 中的 Tokenizer 数据

`gguf-dump` 位于 llama.cpp 的 `gguf-py` 包中。如果当前环境里还没有这个工具，可以安装到仓库内的 Python 虚拟环境：

```bash
python3 -m venv .venv
.venv/bin/pip install --editable ./gguf-py
```

查看 GPT-2 的主要 Tokenizer 元数据：

```bash
.venv/bin/gguf-dump "$GPT2_MODEL" --no-tensors |
  grep -E 'tokenizer\.ggml\.(model|pre|tokens|merges|bos_token_id|eos_token_id)'
```

筛选后的标准输出如下：

```text
     13: STRING     |        1 | tokenizer.ggml.model = 'gpt2'
     14: STRING     |        1 | tokenizer.ggml.pre = 'gpt-2'
     15: [STRING]   |    50257 | tokenizer.ggml.tokens = ['!', '"', '#', '$', '%', '&', ...]
     17: [STRING]   |    50000 | tokenizer.ggml.merges = ['Ġ t', 'Ġ a', 'h e', 'i n', 'r e', 'o n', ...]
     18: UINT32     |        1 | tokenizer.ggml.bos_token_id = 50256
     19: UINT32     |        1 | tokenizer.ggml.eos_token_id = 50256
```

`tokenizer.ggml.pre = 'gpt-2'` 表示当前模型选择了上一节查看的 GPT-2 预切分方式。

`tokenizer.ggml.tokens` 就是词表。它有 50257 个元素，数组下标范围是 `0～50256`；`tokenizer.ggml.merges` 则按 rank 顺序保存 50000 条 BPE 合并规则。

普通输出会截断大数组。要查看指定 Token ID，可以输出完整 JSON，再使用 `jq` 提取目标元素：

```bash
.venv/bin/gguf-dump "$GPT2_MODEL" \
  --no-tensors --json --json-array |
  jq -r '
    .metadata["tokenizer.ggml.tokens"].value as $tokens
    | [0, 30, 345, 389, 1804, 2437, 50256][]
    | "\(.)\t\($tokens[.])"
  '
```

输出：

```text
0	!
30	?
345	Ġyou
389	Ġare
1804	Ġdoing
2437	How
50256	<|endoftext|>
```

这些条目按照 Token ID 从小到大排列，与前面的词表示例一致。它们在 `How are you doing?` 中的出现顺序则是 `2437、389、345、1804、30`。

GGUF 内部的 `Ġare`、`Ġyou` 和 `Ġdoing` 都包含表示前导空格的 `Ġ`；`llama-tokenize` 显示这些 Token 时，会把它还原成真实空格。

### 查看 BPE 合并规则

从 GGUF 中提取 `How` 和 `" are"` 用到的合并规则及其 rank：

```bash
.venv/bin/gguf-dump "$GPT2_MODEL" \
  --no-tensors --json --json-array |
  jq -r '
    .metadata["tokenizer.ggml.merges"].value
    | to_entries[]
    | select(
        .value == "Ġ a" or .value == "r e" or
        .value == "Ġa re" or .value == "o w" or
        .value == "H ow"
      )
    | "rank=\(.key)\t\(.value)"
  '
```

输出：

```text
rank=1	Ġ a
rank=4	r e
rank=66	o w
rank=133	Ġa re
rank=2181	H ow
```

这些真实规则与前面手工展开的 BPE 合并过程一一对应。

## 小结

本文以 `How are → [2437, 389]` 为例，说明了 GPT-2 如何将文本转换为 Token ID：

- Token 是词表中的文本片段，不等同于单词或字符；Token ID 是它在词表中的整数编号。
- GPT-2 依次经过预切分、字节级映射、BPE 合并和词表查询，得到按照原文顺序排列的 Token ID。
- 反分词完成相反方向的转换：根据 Token ID 查询词表、还原字节并依次拼接，不需要逆向执行 BPE。
