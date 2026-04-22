# 03. import、transformer、matcher 是怎么分工的

如果把 PaConvert 的主流程只压成一句话，大概是：

先把“这个名字到底是谁”搞清楚，再决定“该交给哪个规则改写”。

前半句主要是 `ImportTransformer` 和 `BaseTransformer`。后半句主要是 `BasicTransformer`、`BaseMatcher` 和具体 matcher。

## import 分析为什么重要

不先做 import 分析，后面很多调用根本无从判断。

最常见的几种情况：

1. `import torch as th`
2. `import torch.nn as nn`
3. `from torch.nn import functional as F`
4. `from torch.nn import Linear`
5. `from .datasets import x`
6. `import datasets`

对新人最有帮助的例子是 `tests/code_library/code_case/torch_code/import_analysis.py`。  
它把“本地相对导入”和“应该被认成 torch 生态的包”混着放在同一个文件里。对应的期望输出在 `tests/code_library/code_case/paddle_code/import_analysis.py`。

`ImportTransformer` 在这里做的不是“立刻改成 Paddle API 调用”，而是先把三类东西分开：

1. `torch_packages`
2. `may_torch_packages`
3. `other_packages`

后面 `BasicTransformer` 会用这些信息避免误判。

## canonical torch API 名是怎么恢复出来的

这件事实际分两层。

### 第一层：import 别名恢复

`BaseTransformer.get_full_api_from_node()` 会先看当前节点的最左侧名字，比如：

1. `F.relu` 里的 `F`
2. `nn.Linear` 里的 `nn`
3. `Linear(...)` 里的 `Linear`

如果这个名字能在 `imports_map[file]` 里找到，就替换成完整前缀。

结果会变成类似：

1. `F.relu` -> `torch.nn.functional.relu`
2. `nn.Linear` -> `torch.nn.Linear`
3. `Linear` -> `torch.nn.Linear`

### 第二层：alias mapping 归一

补全成完整名字之后，还可能再查一次 `GlobalManager.ALIAS_MAPPING`，也就是 `paconvert/api_alias_mapping.json`。

这里处理的是“同一类 API 的别名入口”，比如当前仓库里可以直接查到：

1. `torch.absolute -> torch.abs`
2. `torch.arccos -> torch.acos`
3. `torch.Tensor.absolute -> torch.Tensor.abs`

所以文中说的 canonical torch API，实际指的是：

1. import 别名已经补全
2. alias mapping 也已经归一

之后再去查 `api_mapping.json` / `attribute_mapping.json`。

## transformer 各自负责什么

### `ImportTransformer`

文件：`paconvert/transformer/import_transformer.py`

职责：

1. 扫 import / from-import
2. 记录别名到完整前缀的映射
3. 记录非 torch 包名，供黑名单使用
4. 把局部写法补成完整 API 名
5. 在模块头部补回 `import paddle`

它做的是“识别前置处理”，不是最终 API 语义改写。

### `BasicTransformer`

文件：`paconvert/transformer/basic_transformer.py`

职责：

1. 识别包级调用
2. 识别类方法调用
3. 识别属性访问
4. 查 mapping
5. 实例化 matcher
6. 把 matcher 生成的 AST 节点插回当前作用域

它才是“主转换器”。

### `PreCustomOpTransformer`

文件：`paconvert/transformer/custom_op_transformer.py`

职责：

1. 预扫描 C++ extension import
2. 记录哪些 `autograd.Function` 类和自定义扩展关联

### `CustomOpTransformer`

同文件后半段。

职责：

1. 把 `AutogradFunc.apply` 这类壳子调用改成扩展模块调用
2. 同时插入“不支持自动转换 C++ 部分”的提示

### `TensorRequiresGradTransformer`

文件：`paconvert/transformer/tensor_requires_grad_transformer.py`

它的职责很明确：专门改 `tensor.requires_grad = ...` 左值赋值。  
但当前 `Converter.transfer_node()` 没有把它加入默认链路。

这里不能写成“它现在也会参与主流程”。实际源码里不是这样。

## matcher 负责什么

transformer 的工作到“识别出一个 API，并确定它应该交给哪个 matcher”就差不多结束了。  
真正决定输出代码长什么样的是 matcher。

matcher 主要做四件事：

1. 参数归一化
2. 参数改名 / 删参 / 补默认值
3. 生成目标 Paddle 代码字符串
4. 必要时生成额外的辅助语句或 helper 函数

举几个最常见的 matcher：

1. `ChangePrefixMatcher`
   - 只改包名前缀
   - 典型例子：`torch.add -> paddle.add`
2. `ChangeAPIMatcher`
   - 只改 API 名，不动参数结构
3. `GenericMatcher`
   - 最常见
   - 能做参数归一化、改名、补默认值、处理 `out` / `requires_grad`
4. 一些专用 matcher
   - 比如 `SliceScatterMatcher`、`TransposeMatcher`
   - 会直接生成多行代码

## 位置参数 / 关键字参数如何被归一化

核心逻辑在 `BaseMatcher.parse_args_and_kwargs()`。

它依赖 mapping 里的几个字段：

1. `args_list`
2. `min_input_args`
3. `unsupport_args`
4. 可选的 `overload_args_list`

它的工作方式可以简单理解成：

1. 先用 `args_list` 给位置参数按顺序命名。
2. 再把源码里本来就是关键字参数的部分并到同一个 `kwargs` 字典里。
3. 如果遇到 `unsupport_args` 且用户真的传了，就直接返回不支持。
4. 如果传入形态和 mapping 声明不一致，比如关键字名根本不在 `args_list` 里，就返回 `misidentify`。

`args_list` 里还有个容易忽略的约定：  
如果出现 `"*"`，表示它后面的参数必须用 keyword 形式出现。

`torch.optim.SGD` 就是很典型的例子：

1. `args_list` 先列 `params, lr, momentum, dampening, weight_decay, nesterov`
2. 再用 `*` 把后面的 `maximize, foreach, differentiable, fused` 划成只能 keyword 的参数

## 为什么有些 API 能一对一替换，有些要生成多行代码

### 一对一替换

这类最省心。

典型情况：

1. API 名和参数结构几乎一样
2. 不需要引入辅助变量
3. 不需要根据上下文插额外语句

`torch.add -> paddle.add` 就是这种。

### 多行代码

多行通常来自三种需求：

1. Paddle 侧没有完全对等的单 API，要用多句组合出来。
2. 需要引入临时变量，避免重复求值。
3. 需要保留 `out=`、`requires_grad=` 这类 PyTorch 语义。

`GenericMatcher.generate_code()` 本身就可能把一行变多行。  
比如同时出现 `out` 和 `requires_grad` 时，它会生成 `paddle.assign(...)` 加属性赋值，不再是一句简单函数调用。

更复杂的专用 matcher 会直接拼多句模板，然后靠 `BaseTransformer.insert_multi_node()` 把前面的辅助语句插回当前作用域，把最后一个表达式替回原调用点。

## 实际顺序到底是不是“我以为的那样”

当前源码里，默认顺序是：

1. `ImportTransformer`
2. `BasicTransformer`
3. `PreCustomOpTransformer`
4. `CustomOpTransformer`

不是：

1. 所有 `transformer/` 目录里的文件都会执行
2. `matcher` 先跑，再决定 import
3. `mark_unsupport()` 在 transformer 里面直接打 `>>>>>>`

这三个都是常见误读。

## 这一层读代码时最值得盯住的文件

1. `paconvert/base.py`
2. `paconvert/transformer/import_transformer.py`
3. `paconvert/transformer/basic_transformer.py`
4. `paconvert/api_mapping.json`
5. `paconvert/api_alias_mapping.json`
6. `paconvert/api_matcher.py`

如果你只打算改一个普通 API 映射，通常不会先改 transformer。  
大多数时候真正要动的是 `api_mapping.json`、`api_matcher.py` 和对应测试。
