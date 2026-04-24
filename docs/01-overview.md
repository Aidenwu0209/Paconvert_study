# 01. 第一次接手先开哪些文件

`setup.py`、`paconvert/main.py`、`paconvert/converter.py` 放在第一轮读。目标很小：确认 CLI 怎么进 `main()`，`Converter.run()` 什么时候接手，目录和单文件分别在哪分流。

`paconvert/transformer/import_transformer.py` 和 `paconvert/transformer/basic_transformer.py` 放在第二轮读。前者准备 `imports_map[file]`，后者识别包级调用、类方法、属性访问并分发 matcher。

先别急着看 `paconvert/api_matcher.py`。matcher 文件能回答“某条规则怎么生成代码”，回答不了“这个调用为什么会走到这里”。入口和 transformer 顺序没立住时，读 matcher 很容易只看到一堆局部规则。

`paconvert/api_mapping.json`、`paconvert/api_matcher.py`、对应的 `tests/test_<api>.py` 放在第三轮读。带着具体 API 搜，比从 `api_matcher.py` 顶部硬翻有效。`torch.add` 看 `tests/test_add.py`，`torch.optim.SGD` 看 `tests/test_optim_SGD.py`。

`tools/` 和 `.github/` 放到准备改代码时再看。`tools/validate_unittest/validate_unittest.py` 会检查测试形态，`tools/validate_docs/validate_docs.py` 会检查文档映射，`tools/consistency/consistency_check.py` 看源码文本回归。

AST 背景记一条就够：`Converter.transfer_file()` 先 `ast.parse(code)`，再由 transformer 改树，最后 `astor.to_source()` 写回。注释和排版问题放到输出阶段理解，不要在 matcher 里找原因。

## 1 到 2 小时路线

前 20 分钟：`setup.py`、`paconvert/main.py`、`paconvert/converter.py`。分清 `main()`、`Converter.run()`、`transfer_dir()`、`transfer_file()`。

接着 30 分钟：`paconvert/global_var.py`、`paconvert/base.py`、`paconvert/transformer/import_transformer.py`。看 `GlobalManager.TORCH_PACKAGE_MAPPING`、`imports_map[file]`、`BaseTransformer.get_full_api_from_node()`。

再用 30 到 40 分钟：`paconvert/transformer/basic_transformer.py`、`paconvert/api_mapping.json`、`paconvert/api_matcher.py`。只盯 `ChangePrefixMatcher`、`GenericMatcher` 和当前 API。

最后对照 `tests/test_add.py`、`tests/test_optim_SGD.py`、[04-one-api-full-trace.md](./04-one-api-full-trace.md)。主线能讲清后，再回到 [05-how-to-add-or-modify-an-api.md](./05-how-to-add-or-modify-an-api.md) 开始判断改哪层。
