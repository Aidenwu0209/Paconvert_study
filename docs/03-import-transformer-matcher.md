# 03. import、transformer、matcher 是怎么分工的

`docs/02` 已经把主流程走完了。这里不再重讲目录扫描和输出，只盯 AST 链中间最容易混掉的三层：import 恢复、`BasicTransformer` 分发、matcher 生成代码。

## import 这一步到底在解决什么

`ImportTransformer` 先解决的是“这个名字到底是谁”。不把这件事做完，后面根本谈不上 stable mapping。

问题的根源很直接：源码里真实出现的往往不是完整 API 名，而是各种局部写法。`import torch as th`、`import torch.nn as nn`、`from torch.nn import functional as F`、`from torch.nn import Linear` 都只把一部分信息留在调用点。你看到的可能是 `th.add(...)`、`nn.Linear(...)`、`F.relu(...)`、`Linear(...)`，甚至再混进本地相对导入和普通第三方包。

`ImportTransformer` 做的事不是“马上把 API 改成 Paddle”，而是先把这些名字放回正确语境里。对照 `tests/code_library/code_case/torch_code/import_analysis.py` 和 `tests/code_library/code_case/paddle_code/import_analysis.py` 看，会更容易理解它为什么要先区分 `torch_packages`、`may_torch_packages` 和 `other_packages`。

## canonical API 是怎么恢复出来的

这件事分两步。

第一步是 import 层的补全。`BaseTransformer.get_full_api_from_node()` 会先看当前节点最左边的名字，比如 `F.relu` 里的 `F`、`nn.Linear` 里的 `nn`、`Linear(...)` 里的 `Linear`。如果这个名字能在 `imports_map[file]` 里找到，就替换成完整前缀。

第二步是 alias 层的归一。补全后的完整名字还可能再过一次 `GlobalManager.ALIAS_MAPPING`，也就是 `paconvert/api_alias_mapping.json`。比如 `torch.absolute` 会归到 `torch.abs`，`torch.arccos` 会归到 `torch.acos`。所以文档里说的 canonical API，实际指的是“import 已补全、alias 也已归一”之后那个最终名字。

后面的 mapping 查询，都是拿这个名字去查。

## `BasicTransformer` 是什么时候介入的

`ImportTransformer` 跑完之后，`Converter.transfer_node()` 才会继续进 `BasicTransformer`。这就是为什么它必须排在 import 之后：`BasicTransformer` 接到的输入，应该已经是能稳定还原出 canonical API 的 AST 节点，而不是一堆模糊别名。

`BasicTransformer` 关心三类东西：包级调用、类方法调用、属性访问。它会在遍历 AST 时判断当前节点属于哪一类，再按 canonical API 去查 `paconvert/api_mapping.json`、`paconvert/attribute_mapping.json` 或 wildcard mapping。

它本身不负责写具体转换代码，真正的工作更像调度：识别节点类型、恢复 API 名、挑 matcher、把 matcher 产出的结果插回当前作用域。

## matcher 接到的是什么，吐出的又是什么

matcher 接到的核心输入有三样：

1. 当前节点对应的 canonical API
2. 这条 API 在 mapping 里的配置
3. 当前 AST 作用域和辅助上下文，比如 `self.paddleClass`

拿到这些之后，matcher 才开始做自己擅长的那一层：参数归一化、参数改名、删参、补默认值、判断 unsupported、必要时登记 helper 代码。

matcher 产出的本质不是“一个字符串”这么简单，而是一段要插回 AST 的结果。有时是一句函数调用；有时是多句辅助语句加最后一个表达式；再复杂一点，还会顺带登记 `paddle_utils.py` 里要落的 helper。

所以 transformer 和 matcher 的交界线可以记成这样：transformer 决定“谁来改”，matcher 决定“改成什么样”。

## 什么时候只是改前缀，什么时候要改参数

`torch.add` 这种场景就是最典型的“只改前缀”。`paconvert/api_mapping.json` 里只写 `Matcher = ChangePrefixMatcher`，然后由 `ChangePrefixMatcher` 把最左边的 `torch` 改成 `paddle`。参数结构基本原样保留。

`torch.optim.SGD` 就不是这样了。它会进 `GenericMatcher`：先用 `BaseMatcher.parse_args_and_kwargs()` 把位置参数归一化成命名参数，再按 `kwargs_change` 改名，最后按 `paddle_default_kwargs` 补默认值。这一层已经不是“换个前缀”能说清的了。

真正再往上一层的复杂度，是需要 helper 或多行代码的时候。比如某些专用 matcher 不会只返回一句调用，而是要引入临时变量、拼多句代码，再由 `BaseTransformer.insert_multi_node()` 把辅助语句插回当前作用域。看到这种需求时，就别再试图只靠 JSON 把问题描述完。

## `BaseMatcher.parse_args_and_kwargs()` 为什么这么关键

很多人第一次看 `api_mapping.json` 时，会把注意力都放在 `paddle_api` 上，反而漏掉 `args_list`。但对 `GenericMatcher` 这类规则来说，`args_list` 才是把位置参数解释对的前提。

`BaseMatcher.parse_args_and_kwargs()` 会按 `args_list` 给位置参数命名，再把源码里本来就是关键字参数的部分并进同一个 `kwargs`。如果遇到 `unsupport_args` 且用户真的传了，就直接走 unsupported；如果传入形态和 mapping 声明对不上，还可能落到 `misidentify`。

`args_list` 里出现 `"*"` 也不是装饰，它表示后面的参数必须按 keyword 形式出现。`torch.optim.SGD` 就靠这个把 `maximize`、`foreach`、`differentiable`、`fused` 划到了 keyword-only 区间。

## 这三层的真实顺序，不要记反

当前默认顺序就是：

1. `ImportTransformer`
2. `BasicTransformer`
3. 具体 matcher

不是所有 `transformer/` 目录里的文件都会自动执行，也不是 matcher 先跑、再回头看 import。`mark_unsupport()` 更不在这一层，它是在 AST 回写成源码之后才统一打 `>>>>>>`。

如果你只打算改一个普通 API，读代码时最值得盯住的还是这几处：`paconvert/base.py`、`paconvert/transformer/import_transformer.py`、`paconvert/transformer/basic_transformer.py`、`paconvert/api_mapping.json`、`paconvert/api_alias_mapping.json`、`paconvert/api_matcher.py`。多数情况下，真正要动的还是 mapping、matcher 和对应测试。
