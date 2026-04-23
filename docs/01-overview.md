# 01. 总览

下面提到的路径，默认都相对 upstream 仓库根目录来写，也就是 `paconvert/...`、`tests/...`、`tools/...` 这一层。

## 第一次接手，先看哪些目录

先开 `setup.py`、`paconvert/main.py`、`paconvert/converter.py`。这三处能最快回答一个最基本的问题：`paconvert -i xxx` 之后，谁负责解析参数，谁开始扫目录，谁把单个 `.py` 文件送进 AST 链。

看完这三处，再去 `paconvert/transformer/import_transformer.py` 和 `paconvert/transformer/basic_transformer.py`。这时你已经知道主流程在哪，继续往下追才会明白 import 恢复和 matcher 分发各自接的是哪一棒。

第三层再看 `paconvert/api_mapping.json`、`paconvert/api_matcher.py` 和对应测试。到这里才值得开始问“某个 API 为什么这样改”，不然很容易只看到规则，不知道规则是在什么节点被触发的。

## 别一上来就先看哪些文件

先别从 `paconvert/api_matcher.py` 顶部一路往下翻。这个文件适合带着问题查，不适合当入口。你如果还没走通 `Converter.run()` 和 `transfer_node()`，看到一堆 matcher 只会知道“有很多规则”，不知道这些规则什么时候会被调到。

也别先在 `tests/test_*.py` 里挑一个 API 埋头看。测试能告诉你输入和预期输出，但如果前面那条主链没立住，你会一直反过来猜源码到底在哪层做了这件事。

`tools/` 和 `.github/` 也不适合放在第一轮。它们更像你准备改代码、补测试、提 PR 时再回来看的一层约束。

## 为什么这里一定要先接受 AST 这件事

PaConvert 不是做文本替换。`Converter.transfer_file()` 先 `ast.parse(code)`，再把 AST 交给固定顺序的 transformer 链，这个设计决定了它能区分真实调用、属性访问、import、局部别名和普通字符串。

这件事如果一开始没接受，后面很多现象都会看起来像“怎么这么绕”。比如 `from torch.nn import functional as F` 这种写法，只有先把 `F` 还原回完整前缀，后面的 matcher 才知道它其实是在处理 `torch.nn.functional.relu`。

代价也一起带来了：AST 回写要经过 `astor.to_source()`，后面还会接 `black` 和 `isort`。所以输出代码的排版、import 顺序、注释保留情况，天然就不会和原文件完全一样。

## 真正值得优先读的目录

### `paconvert/`

这是主链路所在的地方。入口、调度、基础类、mapping、matcher 都在这里。不先读这层，后面的测试和工具看起来都会像黑盒。

### `paconvert/transformer/`

这里是 AST 改写真正落地的地方。优先顺序建议还是先 `import_transformer.py`，再 `basic_transformer.py`。`custom_op_transformer.py` 放后面看就行；`tensor_requires_grad_transformer.py` 要带着一个前提去看：文件存在，但当前默认链路没有接它。

### `tests/`

这一层不是只拿来跑 pytest。`tests/test_*.py` 负责 API 级行为回归，`tests/apibase.py` 是单测基座，`tests/code_library/code_case/` 看的是源码文本回归，`tests/code_library/model_case/` 则更接近大脚本 smoke test。

### `tools/`

真正开始改 API 时再回来看最值。`validate_unittest`、`validate_docs`、`consistency`、`modeltest` 这几类脚本会告诉你：这次改动除了“能不能转”，还会在哪些地方被卡住。

## 一条 1 到 2 小时能执行完的阅读路线

前 20 分钟，先看 `setup.py`、`paconvert/main.py`、`paconvert/converter.py`。这一步的目标不是记参数，而是先把入口、目录扫描和单文件处理分清楚。

接下来的 30 分钟，看 `paconvert/global_var.py`、`paconvert/base.py`、`paconvert/transformer/import_transformer.py`。重点是搞清 `imports_map[file]` 里到底存了什么，以及局部名字是怎么恢复成完整 API 名的。

再往后 30 到 40 分钟，看 `paconvert/transformer/basic_transformer.py`、`paconvert/api_mapping.json` 和 `paconvert/api_matcher.py`。这里不要试图一次把 matcher 看完，先盯 `ChangePrefixMatcher`、`GenericMatcher` 以及你眼下关心的那个 API。

最后拿两个真实例子收尾：`tests/test_add.py` 和 `tests/test_optim_SGD.py`。这时候再对照 [02-how-paconvert-runs.md](./02-how-paconvert-runs.md)、[04-one-api-full-trace.md](./04-one-api-full-trace.md)、[05-how-to-add-or-modify-an-api.md](./05-how-to-add-or-modify-an-api.md)，主线通常就已经立住了。
