# simple_add 说明

这个例子对应 [docs/04-one-api-full-trace.md](../../docs/04-one-api-full-trace.md) 里 `torch.add` 那一节。

## 为什么选它

它足够短，适合先看清一条最基本的包级 API 调用会经过哪些节点。`torch.add(...)` 本身走的是 `ChangePrefixMatcher`，不会先把注意力带到复杂参数改写上。

## 看输出时注意什么

1. 文件头会从 `import torch` 变成 `import paddle`。
2. 这个文件实际会一起改掉两个 `torch.tensor(...)`，所以 summary 统计到的是 3 个 API，不是 1 个。
3. 如果你想看位置参数归一化、参数改名和默认值补齐，这个例子不够，直接去看 `optim_sgd`。

## 对应文档

- [docs/02-how-paconvert-runs.md](../../docs/02-how-paconvert-runs.md)
- [docs/04-one-api-full-trace.md](../../docs/04-one-api-full-trace.md)
