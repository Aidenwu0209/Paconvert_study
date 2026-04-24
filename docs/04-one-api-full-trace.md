# 04. 两个 API 的 trace

## `torch.add`

`torch.add` 的锚点是 `paconvert/api_mapping.json:3058-3060`、`paconvert/api_matcher.py` 里的 `ChangePrefixMatcher`、`tests/test_add.py:55-64`。

原始代码：

```python
import torch

a = torch.tensor([1, 2, 3])
b = torch.tensor([20])
result = torch.add(a, b)
```

`ImportTransformer.visit_Import()` 看到 `import torch` 后，把 `torch` 记进 `imports_map[file]["torch_packages"]`，删掉原 import，模块头部补 `import paddle`。

`BasicTransformer.visit_Call()` 处理 `torch.add(a, b)` 时，`get_full_attr_for_apiname(node.func)` 得到 `torch.add`。这个调用本身不需要 alias 归一，直接查 `paconvert/api_mapping.json`。

mapping 里只写 `Matcher = ChangePrefixMatcher`，没有 `paddle_api`、`kwargs_change`、`unsupport_args`。`ChangePrefixMatcher` 用 `GlobalManager.TORCH_PACKAGE_MAPPING` 把最左边的 `torch` 改成 `paddle`，参数保持原样。

`ChangePrefixMatcher` 还会处理少量 Paddle 当前不接的兼容参数，比如 `layout`、`generator`、`memory_format`。这个最小例子没带这些参数，所以输出里看不到删参动作。

同一个文件里的两个 `torch.tensor(...)` 也会被 `BasicTransformer` 转成 `paddle.tensor(...)`。所以这个例子的 summary 统计到 3 个 API，不是只统计 `torch.add`。

输出代码：

```python
import paddle

a = paddle.tensor([1, 2, 3])
b = paddle.tensor([20])
result = paddle.add(a, b)
```

对应文件是 [examples/simple_add/input_torch.py](../examples/simple_add/input_torch.py) 和 [examples/simple_add/expected_paddle.py](../examples/simple_add/expected_paddle.py)。`tests/test_add.py` 还覆盖关键字参数、`alpha`、`out`、关键字乱序和 skip 的稀疏张量 case。

读测试时先看 `tests/test_add.py:55-64` 的最短支持 case，再扫同文件里带 `alpha`、`out` 的 case。guide 里的 4 行代码只负责把主链路缩小到可追。

最容易讲错的点：`torch.add(...)` 是包级函数，走 `ChangePrefixMatcher`；`x.add(...)` 是类方法，会走 `BasicTransformer` 的类方法分支，再命中别的 matcher。

## `torch.optim.SGD`

`torch.optim.SGD` 的锚点是 `paconvert/api_mapping.json:10075-10107`、`GenericMatcher`、`paconvert/base.py:398-479` 的参数归一化、`tests/test_optim_SGD.py:64-68`。

原始代码：

```python
import torch

conv = torch.nn.Conv2d(1, 1, 3)
optimizer = torch.optim.SGD(conv.parameters(), 0.5)
```

`ImportTransformer` 对 `import torch` 的处理和前一个例子一样。`BasicTransformer.visit_Call()` 会先处理内层 `torch.nn.Conv2d(...)`，再回到外层 `torch.optim.SGD(...)`；`get_full_attr_for_apiname(node.func)` 得到 `torch.optim.SGD`。

mapping 写了 `Matcher = GenericMatcher`、`paddle_api = paddle.optimizer.SGD`、`args_list = ["params", "lr", "momentum", "dampening", "weight_decay", "nesterov", "*", "maximize", "foreach", "differentiable", "fused"]`。`kwargs_change` 把 `params -> parameters`、`lr -> learning_rate`，`paddle_default_kwargs` 补 `weight_decay = 0.0`。`unsupport_args` 里列了 `momentum`、`dampening`、`nesterov`、`maximize`、`foreach`、`differentiable`、`fused`。

`GenericMatcher` 先让 `BaseMatcher.parse_args_and_kwargs()` 把位置参数归一化：`conv.parameters()` 变成 `params`，`0.5` 变成 `lr`。随后 `change_kwargs()` 改名，`set_paddle_default_kwargs()` 补默认值。

`args_list` 里的 `"*"` 把后面的 `maximize`、`foreach`、`differentiable`、`fused` 划到 keyword-only 区间。参数位置写错时，问题通常会在 `parse_args_and_kwargs()` 暴露。

输出代码：

```python
import paddle

conv = paddle.nn.Conv2d(1, 1, 3)
optimizer = paddle.optimizer.SGD(
    parameters=conv.parameters(), learning_rate=0.5, weight_decay=0.0
)
```

对应文件是 [examples/optim_sgd/input_torch.py](../examples/optim_sgd/input_torch.py) 和 [examples/optim_sgd/expected_paddle.py](../examples/optim_sgd/expected_paddle.py)。`tests/test_optim_SGD.py` 同时写了 supported 和 unsupported 形态；带 `momentum`、`dampening`、`nesterov` 的调用会保留原代码并打 `>>>>>>`。

输出里的 `weight_decay=0.0` 来自 `paddle_default_kwargs`。排查默认参数时，先看 mapping，再看 `GenericMatcher` 的默认值补齐。

unsupported 分支可以用这类输入对照：

```python
optimizer = torch.optim.SGD(
    conv.parameters(),
    lr=0.8,
    momentum=0,
    dampening=0,
    weight_decay=0,
    nesterov=False,
    maximize=False,
    foreach=None,
    differentiable=False,
)
```

输出会保留原调用并打 `>>>>>>`，不是把这些参数静默丢掉。

最容易讲错的点：mapping 里有 `paddle.optimizer.SGD`，不代表所有 `torch.optim.SGD` 参数组合都支持。当前规则支持一个子集，不支持参数由 `unsupport_args` 和测试一起划边界。

## 差异

`torch.add` 基本是前缀替换；`torch.optim.SGD` 会走 `GenericMatcher` 的位置参数归一化、参数改名和默认值补齐。新增 API 时，先判断自己更像哪一种。
