# 04. 两个真实 API 的完整链路

这里固定只追两个例子：`torch.add` 和 `torch.optim.SGD`。前者够短，适合先把主链路踩一遍；后者会经过 `GenericMatcher`，能把参数归一化、参数改名和默认值补齐都带出来。

两段 trace 都按同一套顺序写：原始代码 -> import 识别 -> canonical API -> mapping -> matcher -> 参数变化 -> 输出 -> 测试。这样看下来，共性和差异都比较直。

## 例子一：`torch.add`

### 为什么选它

它够简单，注意力可以放在主链路本身，不会先被专用 matcher 的细节带偏。这个例子还有个常见误区很适合顺手澄清：这里追的是包级函数 `torch.add(...)`，不是方法调用 `x.add(...)`。

### 依据在哪里

1. mapping：`paconvert/api_mapping.json:3058-3060`
2. matcher：`paconvert/api_matcher.py:423-455` 的 `ChangePrefixMatcher`
3. 测试：`tests/test_add.py:55-64` 的 `test_case_3`

### 原始代码

guide 里的最小例子对应的是：

```python
import torch

a = torch.tensor([1, 2, 3])
b = torch.tensor([20])
result = torch.add(a, b)
```

这个形态和 `tests/test_add.py:55-64` 里的真实测试一致，只是单独抽成了更短的文件。

### import 识别

`ImportTransformer.visit_Import()` 会看到 `import torch`，确认它命中 `GlobalManager.TORCH_PACKAGE_MAPPING`，然后把 `torch` 记录到 `imports_map[file]["torch_packages"]`，删掉原始 import，最后在模块头部补回 `import paddle`。

所以这个文件输出时顶部看到的是：

```python
import paddle
```

这里没有“保留 `import torch` 再补一个 `import paddle`”这一步。

### canonical API

走到 `BasicTransformer.visit_Call()` 时，`node.func` 已经能被恢复成完整属性串。这里的调用点本来就是 `torch.add`，所以 `get_full_attr_for_apiname(node.func)` 直接得到 `torch.add`，不需要再走 alias mapping。

### mapping

`paconvert/api_mapping.json` 里这条配置很短：

1. key：`torch.add`
2. value：`Matcher = ChangePrefixMatcher`

它没有 `paddle_api`、`kwargs_change`、`unsupport_args` 这些字段，意思也很直接：这里不需要复杂规则，只要把包前缀改掉就够了。

### matcher

`BasicTransformer.get_api_matcher()` 会按 `Matcher` 字段实例化 `ChangePrefixMatcher`。这个 matcher 做的事情不多：把最左边的 `torch` 按 `GlobalManager.TORCH_PACKAGE_MAPPING` 改成 `paddle`，保留原参数，同时顺手丢掉少量 Paddle 当前不支持的兼容参数，比如 `layout`、`generator`、`memory_format`。

对 `torch.add(a, b)` 这种调用来说，参数本身没有被重写。

### 参数变化

这个例子里，`torch.add` 本身没有参数名改写。真正一起被改掉的是同文件里的另外两个调用：

1. `torch.tensor([1, 2, 3]) -> paddle.tensor([1, 2, 3])`
2. `torch.tensor([20]) -> paddle.tensor([20])`

也就是说，这个文件实际一共转换了 3 个 API。这也是本地跑示例时 summary 显示 `There are 3 Pytorch APIs in this Project` 的原因。

### 输出代码

这是当前 upstream 实际执行得到的输出：

```python
import paddle

a = paddle.tensor([1, 2, 3])
b = paddle.tensor([20])
result = paddle.add(a, b)
```

对应文件见：

1. [examples/simple_add/input_torch.py](../examples/simple_add/input_torch.py)
2. [examples/simple_add/expected_paddle.py](../examples/simple_add/expected_paddle.py)

### 相关测试

最直接的是 `tests/test_add.py`。这个文件不只测最简单的两参调用，还覆盖了关键字参数写法、`alpha`、`out`、关键字乱序，以及一些当前能力边界，比如 skip 的稀疏张量 case。

所以它验证的不只是“能不能从 `torch.add` 变成 `paddle.add`”，也在看这条 mapping 在不同参数形态下有没有跑偏。

### 这个例子最容易讲错的点

不要把 `torch.add` 和 `torch.Tensor.add` 混成一条规则。当前仓库里，`torch.add` 走 `ChangePrefixMatcher`；`x.add(...)` 属于类方法，会走 `BasicTransformer` 的另一条分支，最后命中别的 matcher。名字看起来都叫 add，源码链路不是一回事。

## 例子二：`torch.optim.SGD`

### 为什么选它

这个例子把 `torch.add` 没带出来的那部分补上了：位置参数先归一化成命名参数，参数名再重写，最后还会补 Paddle 端默认值。以后你真要加一个普通难度的 optimizer 映射，读这个例子比只看 `torch.add` 更接近实际。

### 依据在哪里

1. mapping：`paconvert/api_mapping.json:10075-10107`
2. matcher：`paconvert/api_matcher.py:121-214` 的 `GenericMatcher`
3. 参数归一化：`paconvert/base.py:398-479`
4. 测试：`tests/test_optim_SGD.py:64-68` 的 `test_case_6`

### 原始代码

这里选的是 `tests/test_optim_SGD.py:64-68` 这一类：

```python
import torch

conv = torch.nn.Conv2d(1, 1, 3)
optimizer = torch.optim.SGD(conv.parameters(), 0.5)
```

不选带 `weight_decay=0.1` 的例子，是因为这个输入更容易看出 `GenericMatcher` 还会主动补 `weight_decay=0.0`。

### import 识别

这里还是 `import torch`，所以 import 识别逻辑和前一个例子一样：删掉 `import torch`，记录 `torch` 是待转换包前缀，最后补回 `import paddle`。

### canonical API

`BasicTransformer.visit_Call()` 对 `torch.optim.SGD(...)` 做后序遍历时，会先处理里面的 `torch.nn.Conv2d(...)`，再回到外层 `torch.optim.SGD(...)`。`get_full_attr_for_apiname(node.func)` 最后拿到的是完整名 `torch.optim.SGD`。

这个调用不需要 import 补全，也不需要 alias 归一，名字本身已经是 canonical form。

### mapping

`paconvert/api_mapping.json` 里，这条配置比 `torch.add` 长得多：

1. `Matcher = GenericMatcher`
2. `paddle_api = paddle.optimizer.SGD`
3. `args_list = ["params", "lr", "momentum", "dampening", "weight_decay", "nesterov", "*", "maximize", "foreach", "differentiable", "fused"]`
4. `unsupport_args` 里列了 `momentum`、`dampening`、`nesterov`、`maximize`、`foreach`、`differentiable`、`fused`
5. `kwargs_change` 把 `params -> parameters`、`lr -> learning_rate`
6. `paddle_default_kwargs` 补 `weight_decay = 0.0`

看到这种配置，基本就能判断这不是简单改前缀，而是标准 `GenericMatcher` 场景。

### matcher

`BasicTransformer.get_api_matcher()` 会实例化 `GenericMatcher`。它的处理顺序大致是：先让 `BaseMatcher.parse_args_and_kwargs()` 把位置参数变成命名参数，再用 `change_kwargs()` 改参数名，再用 `set_paddle_default_kwargs()` 补 Paddle 端默认值，最后拼成 `paddle.optimizer.SGD(...)`。

### 参数变化

对这条输入：

```python
torch.optim.SGD(conv.parameters(), 0.5)
```

实际变化顺序是：

1. 位置参数第 1 个 `conv.parameters()` 先被识别成 `params`
2. 位置参数第 2 个 `0.5` 先被识别成 `lr`
3. `kwargs_change` 把 `params -> parameters`
4. `kwargs_change` 把 `lr -> learning_rate`
5. 因为输入里没给 `weight_decay`，`paddle_default_kwargs` 再补出 `weight_decay=0.0`

所以输出不是 `paddle.optimizer.SGD(conv.parameters(), 0.5)`，而是显式展开成关键字参数。

### 输出代码

这是当前 upstream 实际执行得到的输出：

```python
import paddle

conv = paddle.nn.Conv2d(1, 1, 3)
optimizer = paddle.optimizer.SGD(
    parameters=conv.parameters(), learning_rate=0.5, weight_decay=0.0
)
```

对应文件见：

1. [examples/optim_sgd/input_torch.py](../examples/optim_sgd/input_torch.py)
2. [examples/optim_sgd/expected_paddle.py](../examples/optim_sgd/expected_paddle.py)

### 相关测试

`tests/test_optim_SGD.py` 很适合拿来当“怎么读一个 API 的测试覆盖面”样板。它既有支持的调用形态，也有明确标成 unsupported 的参数组合，用来划定这条 mapping 的工程边界。

为了对照 unsupported 分支，这里再放一个本地实际转换过的不支持样例：

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

输出不是偷偷删参，而是保留原调用并打 `>>>>>>` 标记。

### 这个例子最容易讲错的点

不要把“mapping 里写了 `paddle.optimizer.SGD`”理解成“只要是 `torch.optim.SGD` 就都支持”。从 `api_mapping.json` 和 `tests/test_optim_SGD.py` 一起看，边界很清楚：`lr`、`weight_decay` 这类能走通，`momentum`、`dampening`、`nesterov` 等参数一旦真的出现，就会转成 unsupported，而不是弱化成部分兼容。

## 把这两个例子放在一起看

它们共用同一条入口：都先经过 `ImportTransformer`，再由 `BasicTransformer` 取得 canonical API，最后交给 matcher。差别从 mapping 开始才真正拉开。

`torch.add` 这条规则几乎只是在改前缀，所以重点是看主流程本身。`torch.optim.SGD` 则把 `GenericMatcher` 那套常见工程动作都带出来了：位置参数归一化、参数名改写、默认值补齐，以及 unsupported 边界怎么落回 `>>>>>>`。后面你要新增或修改一个 API，通常会先判断自己更像前者还是后者。
