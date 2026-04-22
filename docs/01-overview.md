# 01. 总览

下面提到的路径，默认都相对 upstream 仓库根目录来写，也就是 `paconvert/...`、`tests/...`、`tools/...` 这一层。

## PaConvert 在迁移流程里扮演什么角色

它不是训练框架，也不是模型权重转换器。它做的是“把一份 PyTorch Python 源码尽量自动改写成 Paddle Python 源码”。

从仓库实现看，这件事被拆成两层：

1. 识别：当前文件里哪些名字真的是 `torch` 生态 API，不是本地模块、不是普通第三方库、也不是同名变量。
2. 改写：如果识别出来了，这个调用应该改成哪一段 Paddle 代码。

入口在 `paconvert/main.py`，总控在 `paconvert/converter.py`，识别和改写主干在 `paconvert/transformer/` 与 `paconvert/api_matcher.py`。

## 它和“字符串替换工具”的本质区别

PaConvert 不直接对源码做 `torch.` -> `paddle.` 的全局替换。

源码里至少有这些情况，纯文本替换会直接出错：

1. `from torch.nn import functional as F`，真正调用时看到的是 `F.relu(...)`。
2. `nn.Linear`、`Linear`、`x.add(...)` 这种写法，名字本身不带完整前缀。
3. `torch.optim.SGD(conv.parameters(), 0.5)` 这种位置参数调用，要先知道第一个位置参数是 `params`，第二个是 `lr`，才能改成 `parameters=`、`learning_rate=`。
4. 有些 API 不是一行换一行，而是要先插入辅助语句，再把最后一个表达式替回原位置。
5. 注释、字符串、相对导入、本地模块这些东西都可能让“看到一个 `torch` 字样”并不等于“这是待改写 API”。

所以它先走 AST，再决定哪里能改、怎么改。

## 为什么要基于 AST 做转换

直接看实现，`paconvert/converter.py` 在 `transfer_file()` 里先 `ast.parse(code)`，然后把 AST 交给固定顺序的 transformer 链。

这样做至少有三个直接好处：

1. 可以区分 `Call`、`Attribute`、`Name`、`ImportFrom` 这些不同语法节点，不会把文档字符串里的 `torch.xxx` 误当成真实调用。
2. 可以在“当前作用域”里插回多行代码。`BaseTransformer.record_scope()` 和 `insert_scope()` 就是干这个的。
3. 可以先做 import/别名恢复，再做 API 映射。`ImportTransformer` 和 `BasicTransformer` 是前后两段，不是一个函数里混着写。

代价也很明显：回写时要经过 `astor.to_source()`，注释和一部分原始排版会丢，这也是 PaConvert 输出代码看起来和原文件风格不完全一样的根源。

## 最值得优先读的目录

### `paconvert/`

核心包。先看这里，不然看测试会一直猜“它内部到底怎么认 API”。

重点文件：

1. `paconvert/main.py`
2. `paconvert/converter.py`
3. `paconvert/global_var.py`
4. `paconvert/base.py`
5. `paconvert/api_matcher.py`

### `paconvert/transformer/`

主转换链真正落地的地方。

优先顺序建议：

1. `paconvert/transformer/import_transformer.py`
2. `paconvert/transformer/basic_transformer.py`
3. `paconvert/transformer/custom_op_transformer.py`
4. `paconvert/transformer/tensor_requires_grad_transformer.py`

最后这个文件要特别留意：它存在，但默认链路当前没有启用，后面会单独说。

### `tests/`

这里不是只有“跑不跑得过”。

不同子区保护的是不同层面：

1. `tests/test_*.py`：单个 API 的行为回归，绝大多数是一文件一个 API。
2. `tests/apibase.py`：测试基座，负责“临时落盘 -> 调用 Converter -> 执行两边代码 -> 比较结果”。
3. `tests/code_library/code_case/`：源码级一致性样例，不看数值，看转换出来的代码文本像不像维护者预期。
4. `tests/code_library/model_case/`：更大的模型脚本样例。
5. `tests/distributed/`、`tests/flash_attn_tests/`：特殊子领域。

### `tools/`

如果你后面要自己提 PR，这里很重要。

我会优先看：

1. `tools/validate_unittest/validate_unittest.py`
2. `tools/validate_docs/validate_docs.py`
3. `tools/consistency/consistency_check.py`
4. `tools/modeltest/modeltest_check.py`
5. `tools/prTemplate/prTemplate_check.py`

### `scripts/` 和 `.github/`

这两块决定“本地怎么跑检查”和“仓库里可见的 GitHub workflow 是哪些”。

当前仓库有个值得注意的现象：

1. `.github/workflows_origin/` 只看到 `tests.yml`、`lint.yml`、`coverage.yml` 三个工作流文件。
2. 但 `scripts/` 和 `docs/CONTRIBUTING.md` 里提到的检查项更多，包括 `modeltest`、`consistency`、`install`、`PRTemplate`。

这说明“仓库可见 workflow”和“维护流程里真实存在的检查脚本”不是一回事。

## 给新人的 2 小时阅读路线

### 第 0-20 分钟

先看：

1. `setup.py`
2. `paconvert/main.py`
3. `paconvert/converter.py`

目标不是记参数，而是先回答一个问题：`paconvert -i xxx` 之后，到底是谁开始扫目录、读文件、跑 AST。

### 第 20-50 分钟

接着看：

1. `paconvert/global_var.py`
2. `paconvert/base.py`
3. `paconvert/transformer/import_transformer.py`

这一步要搞清两个核心概念：

1. `imports_map[file]` 里到底记了什么。
2. “局部名字 -> 完整 torch API 名”的恢复是在什么地方做的。

### 第 50-90 分钟

再看：

1. `paconvert/transformer/basic_transformer.py`
2. `paconvert/api_matcher.py`
3. `paconvert/api_mapping.json`

不要试图一次读完整个 `api_matcher.py`。先只盯住 `ChangePrefixMatcher`、`GenericMatcher` 和你关心的那一个 API。

### 第 90-120 分钟

最后配着测试看两个真实例子：

1. `tests/test_add.py`
2. `tests/test_optim_SGD.py`

然后再回头看本指南的：

1. [02-how-paconvert-runs.md](./02-how-paconvert-runs.md)
2. [04-one-api-full-trace.md](./04-one-api-full-trace.md)
3. [05-how-to-add-or-modify-an-api.md](./05-how-to-add-or-modify-an-api.md)

这两个小时的目标不是“把所有 matcher 看完”，而是先形成一个稳定的心智模型：入口在哪、分层在哪、你下次应该先改哪里。
