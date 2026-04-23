# optim_sgd 说明

这个例子对应 [docs/04-one-api-full-trace.md](../../docs/04-one-api-full-trace.md) 里 `torch.optim.SGD` 那一节。

## 为什么选它

它比 `simple_add` 更接近日常会改到的 mapping。这里不是单纯改前缀，而是会先把位置参数按 `args_list` 归一化，再按 `kwargs_change` 改名，最后补上 `paddle_default_kwargs`。

## 看输出时注意什么

1. `conv.parameters()` 和 `0.5` 不会原样保留位置参数，而是先变成 `parameters=`、`learning_rate=`。
2. 输入里没写 `weight_decay`，输出里仍然会显式补出 `weight_decay=0.0`。
3. 这个例子本身没展示 unsupported 边界；要看 `momentum`、`dampening`、`nesterov` 为什么会落到 `>>>>>>`，回头对照 `tests/test_optim_SGD.py` 更直接。

## 对应文档

- [docs/03-import-transformer-matcher.md](../../docs/03-import-transformer-matcher.md)
- [docs/04-one-api-full-trace.md](../../docs/04-one-api-full-trace.md)
- [docs/05-how-to-add-or-modify-an-api.md](../../docs/05-how-to-add-or-modify-an-api.md)
