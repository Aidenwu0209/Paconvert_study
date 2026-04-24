# optim_sgd 说明

`torch.optim.SGD(conv.parameters(), 0.5)` 走 `GenericMatcher`。

它主要体现 `args_list` 位置参数归一化、`kwargs_change` 参数改名、`paddle_default_kwargs` 默认值补齐。

输入输出见 `input_torch.py` 和 `expected_paddle.py`。

回看：[docs/04-one-api-full-trace.md](../../docs/04-one-api-full-trace.md)、[docs/05-how-to-add-or-modify-an-api.md](../../docs/05-how-to-add-or-modify-an-api.md)。
