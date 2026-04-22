# 04. 两个真实 API 的完整链路

这一篇只追两个例子：

1. `torch.add`
2. `torch.optim.SGD`

它们都能在当前 upstream 里同时找到：

1. mapping 依据
2. matcher 依据
3. 测试依据
4. 实际转换输出

## 例子一：`torch.add`

### 为什么选它

它足够简单，能把注意力放在主链路，不容易被专用 matcher 细节带偏。

但它也有一个很适合拿来提醒新人的点：  
这里追的是包级函数 `torch.add(...)`，不是方法调用 `x.add(...)`。两者在当前仓库里不是一套 matcher。

### 依据在哪里

1. mapping：`paconvert/api_mapping.json:3058-3060`
2. matcher：`paconvert/api_matcher.py:423-455` 的 `ChangePrefixMatcher`
3. 测试：`tests/test_add.py:55-64` 的 `test_case_3`

### 1. 源码里的原始调用长什么样

我在 guide 里放的最小例子对应的是下面这段：

```python
import torch

a = torch.tensor([1, 2, 3])
b = torch.tensor([20])
result = torch.add(a, b)
```

这个形态和 `tests/test_add.py:55-64` 里真实测试用例一致，只是单独抽成了一个更短的文件。

### 2. import / 别名如何被识别

`ImportTransformer.visit_Import()` 会看到 `import torch`：

1. 发现 `torch` 命中 `GlobalManager.TORCH_PACKAGE_MAPPING`
2. 把 `torch` 记录到 `imports_map[file]["torch_packages"]`
3. 删除原始 `import torch`
4. 在模块遍历结束时补回 `import paddle`

所以最后输出文件顶部看到的是：

```python
import paddle
```

不是“保留 `import torch` 再补一个 `import paddle`”。

### 3. 完整 torch API 名如何确定

走到 `BasicTransformer.visit_Call()` 时，`node.func` 已经能被恢复成完整属性串。

这里的调用点本来就是 `torch.add`，所以：

1. `get_full_attr_for_apiname(node.func)` 得到 `torch.add`
2. 它本身不需要再走 alias mapping
3. 于是直接按 `torch.add` 去查 `api_mapping.json`

### 4. 去哪里查映射

命中的 mapping 很短：

1. key：`torch.add`
2. value：`Matcher = ChangePrefixMatcher`

这个配置本身没有 `paddle_api`、`kwargs_change`、`unsupport_args`。  
意思很明确：这里不需要专门写一条复杂规则，只要让 matcher 用“包前缀映射”推导目标 API 即可。

### 5. 哪个 matcher 接手

`BasicTransformer.get_api_matcher()` 根据 mapping 里的 `Matcher` 字段，实例化 `ChangePrefixMatcher`。

这个 matcher 做的事很少：

1. 用 `GlobalManager.TORCH_PACKAGE_MAPPING` 把最左边的 `torch` 换成 `paddle`
2. 把参数原样保留
3. 顺手删掉少量 Paddle 当前不支持的兼容参数，比如 `layout`、`generator`、`memory_format`

对 `torch.add(a, b)` 这种调用来说，参数并没有被重写。

### 6. 参数如何变化

这个例子里，`torch.add` 本身没有参数名改写。

真正发生变化的是同文件里的另外两个调用：

1. `torch.tensor([1, 2, 3]) -> paddle.tensor([1, 2, 3])`
2. `torch.tensor([20]) -> paddle.tensor([20])`

也就是说，这个文件实际有 3 个 API 被转换。  
这也是我本地实际运行时 summary 显示 `There are 3 Pytorch APIs in this Project` 的原因。

### 7. 最终输出代码长什么样

这是当前 upstream 实际执行得到的输出，不是手写推演：

```python
import paddle

a = paddle.tensor([1, 2, 3])
b = paddle.tensor([20])
result = paddle.add(a, b)
```

对应文件见：

1. [examples/simple_add/input_torch.py](../examples/simple_add/input_torch.py)
2. [examples/simple_add/expected_paddle.py](../examples/simple_add/expected_paddle.py)

### 8. 相关测试在哪里

最直接的是 `tests/test_add.py`。

这个文件不只测最简单的两参调用，还覆盖了：

1. 关键字参数写法
2. `alpha`
3. `out`
4. 关键字乱序
5. 一些当前能力边界，比如 skip 的稀疏张量 case

所以它不是只在验证“能不能从 `torch.add` 变成 `paddle.add`”，还在验证这条 mapping 在不同参数形态下有没有跑偏。

### 这个例子最容易讲错的点

不要把 `torch.add` 和 `torch.Tensor.add` 混成一条规则。

当前仓库里：

1. `torch.add` 走 `ChangePrefixMatcher`
2. `x.add(...)` 对应的是类方法，会走 `BasicTransformer` 的类方法分支，最后命中别的 matcher

只看名字像“都是 add”，但源码链路不是一回事。

---

## 例子二：`torch.optim.SGD`

### 为什么选它

这个例子比 `torch.add` 更像“你以后真的会改的 API”。

它能把三件事一次讲清楚：

1. 位置参数先被归一化
2. 参数名再被改写
3. Paddle 端默认参数还能被自动补出来

### 依据在哪里

1. mapping：`paconvert/api_mapping.json:10075-10107`
2. matcher：`paconvert/api_matcher.py:121-214` 的 `GenericMatcher`
3. 参数归一化：`paconvert/base.py:398-479`
4. 测试：`tests/test_optim_SGD.py:64-68` 的 `test_case_6`

### 1. 源码里的原始调用长什么样

我这里选的是 `tests/test_optim_SGD.py:64-68` 这一类：

```python
import torch

conv = torch.nn.Conv2d(1, 1, 3)
optimizer = torch.optim.SGD(conv.parameters(), 0.5)
```

为什么选这个，而不是带 `weight_decay=0.1` 的例子？  
因为这个更能看出 `GenericMatcher` 还会主动补 `weight_decay=0.0`。

### 2. import / 别名如何被识别

这里还是 `import torch`，所以 import 识别逻辑和前一个例子一样：

1. 删掉 `import torch`
2. 记录 `torch` 是待转换包前缀
3. 最后补 `import paddle`

### 3. 完整 torch API 名如何确定

`BasicTransformer.visit_Call()` 对 `torch.optim.SGD(...)` 做后序遍历时：

1. 先处理里面的 `torch.nn.Conv2d(...)`
2. 再回到外层 `torch.optim.SGD(...)`
3. `get_full_attr_for_apiname(node.func)` 得到完整名 `torch.optim.SGD`

这个调用不需要 import 补全，也不需要 alias 归一，名字本身已经是 canonical form。

### 4. 去哪里查映射

`paconvert/api_mapping.json` 里，这条配置比 `torch.add` 明显长得多：

1. `Matcher = GenericMatcher`
2. `paddle_api = paddle.optimizer.SGD`
3. `args_list = ["params", "lr", "momentum", "dampening", "weight_decay", "nesterov", "*", "maximize", "foreach", "differentiable", "fused"]`
4. `unsupport_args` 里列了 `momentum`、`dampening`、`nesterov`、`maximize`、`foreach`、`differentiable`、`fused`
5. `kwargs_change` 把 `params -> parameters`、`lr -> learning_rate`
6. `paddle_default_kwargs` 补 `weight_decay = 0.0`

看到这种配置时，基本就可以预判：这不是简单改前缀，而是标准 `GenericMatcher` 场景。

### 5. 哪个 matcher 接手

`BasicTransformer.get_api_matcher()` 会实例化 `GenericMatcher`。

它的处理顺序大致是：

1. 先让 `BaseMatcher.parse_args_and_kwargs()` 把位置参数变成命名参数
2. 再用 `change_kwargs()` 做参数改名
3. 再用 `set_paddle_default_kwargs()` 补 Paddle 端默认值
4. 最后拼成 `paddle.optimizer.SGD(...)`

### 6. 参数如何变化

对这条输入：

```python
torch.optim.SGD(conv.parameters(), 0.5)
```

实际变化顺序是：

1. 位置参数第 1 个 `conv.parameters()` 先被识别成 `params`
2. 位置参数第 2 个 `0.5` 先被识别成 `lr`
3. `kwargs_change` 再把 `params -> parameters`
4. `kwargs_change` 再把 `lr -> learning_rate`
5. 因为输入里没给 `weight_decay`，`paddle_default_kwargs` 再补出 `weight_decay=0.0`

所以输出不是：

```python
paddle.optimizer.SGD(conv.parameters(), 0.5)
```

而是显式展开成关键字参数。

### 7. 最终输出代码长什么样

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

### 8. 相关测试在哪里

`tests/test_optim_SGD.py` 这个文件很适合当“怎么读一个 API 的测试覆盖面”样板。

它至少包含三类信息：

1. 支持的常见调用形态
   - 纯位置参数
   - 显式 `lr`
   - 显式 `weight_decay`
   - 关键字乱序
2. 预期不支持的形态
   - `momentum`
   - `dampening`
   - `nesterov`
   - `maximize`
   - `foreach`
   - `differentiable`
3. 这条 mapping 的“工程边界”到底画在哪

我额外本地跑过一个不支持样例：

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

输出结果不是偷偷删参，而是保留原调用并打 `>>>>>>` 标记。

### 这个例子最容易讲错的点

不要把“mapping 里写了 `paddle.optimizer.SGD`”理解成“只要是 `torch.optim.SGD` 就都支持”。

当前这条规则是支持一个子集，不支持一个子集。

从 `api_mapping.json` 和 `tests/test_optim_SGD.py` 一起看，边界非常清楚：

1. `lr`、`weight_decay` 这类能走通
2. `momentum`、`dampening`、`nesterov` 等参数一旦真的出现，就会转成 unsupported，而不是弱化成部分兼容
