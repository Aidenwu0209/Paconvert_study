# simple_add 说明

`torch.add(...)` 走 `ChangePrefixMatcher`，适合看包级 API 的最短链路。

这个文件还包含两个 `torch.tensor(...)`，summary 会统计 3 个 API。

输入输出见 `input_torch.py` 和 `expected_paddle.py`。

回看：[docs/04-one-api-full-trace.md](../../docs/04-one-api-full-trace.md)。
