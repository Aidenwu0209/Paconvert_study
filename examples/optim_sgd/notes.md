# optim_sgd 说明

## 这个例子来自哪里

它对应 upstream 的 `tests/test_optim_SGD.py:64-68`，也就是位置参数形态的 `torch.optim.SGD(conv.parameters(), 0.5)`。

## 为什么比 simple_add 更适合看参数改写

因为这里不是单纯改前缀，而是会连续发生 3 件事：

1. 位置参数 `conv.parameters()`、`0.5` 先按 `args_list` 归一化成 `params`、`lr`
2. `kwargs_change` 再把它们改成 `parameters`、`learning_rate`
3. `paddle_default_kwargs` 再补出 `weight_decay=0.0`

`torch.add` 那种例子看不到这三步。

## 我实际怎么跑的

我本地实际执行过：

```bash
cd <UPSTREAM_REPO_ROOT>
python3 paconvert/main.py \
  -i <GUIDE_REPO_ROOT>/examples/optim_sgd/input_torch.py \
  -o /tmp/optim_sgd_out.py \
  --log_dir disable
```

`expected_paddle.py` 是这次实际执行得到的输出。

## 它在主流程里经历了什么

1. `ImportTransformer` 把 `import torch` 改成文件头部的 `import paddle`
2. `BasicTransformer` 先处理 `torch.nn.Conv2d(...)`
3. 再处理 `torch.optim.SGD(...)`
4. `get_api_matcher()` 命中 `GenericMatcher`
5. `parse_args_and_kwargs()` 把两个位置参数变成 `params`、`lr`
6. `change_kwargs()` 把它们改成 `parameters`、`learning_rate`
7. `set_paddle_default_kwargs()` 补 `weight_decay=0.0`
8. 最后拼成 `paddle.optimizer.SGD(...)`

## 这个例子没展示什么

它没有展示 unsupported 边界。  
如果你想看 `momentum`、`dampening`、`nesterov` 这些参数为什么会直接落到 `>>>>>>`，请对照：

1. `tests/test_optim_SGD.py:80-116`
2. `paconvert/api_mapping.json:10092-10099`

当前这条规则不是“完全支持 SGD”，而是“支持一个明确子集”。
