# simple_add 说明

## 这个例子来自哪里

它对应 upstream 的 `tests/test_add.py:55-64`，也就是最简单的一组 `torch.add(a, b)` 用例。

## 为什么用它

因为它够短，但链路很完整：

1. `import torch` 会被 `ImportTransformer` 删掉并补成 `import paddle`
2. 两个 `torch.tensor(...)` 会一起转换
3. `torch.add(...)` 本身会命中 `ChangePrefixMatcher`

所以虽然文件只有 4 行业务代码，summary 里会看到 3 个 API 被统计。

## 我实际怎么跑的

我本地实际执行过：

```bash
cd <UPSTREAM_REPO_ROOT>
python3 paconvert/main.py \
  -i <GUIDE_REPO_ROOT>/examples/simple_add/input_torch.py \
  -o /tmp/simple_add_out.py \
  --log_dir disable
```

`expected_paddle.py` 是这次实际执行得到的输出。

## 它在主流程里经历了什么

1. `paconvert/main.py` 解析 CLI 参数
2. `Converter.run()` 进入文件模式
3. `transfer_file()` 对 `input_torch.py` 做 `ast.parse()`
4. `ImportTransformer` 删除 `import torch`，最后补 `import paddle`
5. `BasicTransformer` 先把两个 `torch.tensor(...)` 转成 `paddle.tensor(...)`
6. 同一个 `BasicTransformer` 再把 `torch.add(...)` 交给 `ChangePrefixMatcher`
7. `astor + black + isort` 回写输出

## 这个例子最适合看什么

看“主链路怎么串起来”，不要拿它去理解复杂参数语义。  
如果你想看参数归一化、参数改名、默认值补齐，直接跳到 `examples/optim_sgd`。
