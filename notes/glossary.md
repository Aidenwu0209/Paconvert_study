# 术语表

## AST

抽象语法树。PaConvert 先把 `.py` 文件 `ast.parse()` 成 AST，再在树上改写节点，最后用 `astor.to_source()` 写回代码。它不是基于文本正则做替换。

## Transformer

这里主要指继承 `BaseTransformer` 的 AST 访问器，比如 `ImportTransformer`、`BasicTransformer`。它们负责“在哪些节点上识别转换机会”。

## Matcher

继承 `BaseMatcher` 的 API 级规则类。它负责“这个 API 被识别出来以后，具体怎么改写成 Paddle 代码”。

## Mapping

主要是 `paconvert/api_mapping.json`。每个 `torch API` 对应一条规则，至少会告诉系统要用哪个 `Matcher`。

## Wildcard Mapping

`paconvert/api_wildcard_mapping.json` 里的通配规则。当前文件很小，能看到的例子只有 `einops.layers.torch.*`，还有一个被 `disable` 的 `transformers.*`。

## Alias Mapping

`paconvert/api_alias_mapping.json` 里的“别名归一化”规则。比如 `torch.absolute` 会先归一成 `torch.abs`，后面再查真正的 mapping。

## Canonical Torch API

这里我用它指“补全 import 别名并做 alias 归一化之后的 API 全名”。例如 `F.relu` 会先还原成 `torch.nn.functional.relu`；如果命中 alias，再继续归到真正做 mapping 的那一项。

## Import 分析

`ImportTransformer` 在第一轮遍历里做的事。它会记住当前文件里 `torch` 相关 import 的别名、本地模块、非 torch 包名，并把这些信息存到 `imports_map[file]`。

## Summary / Convert Rate

`Converter.run()` 最后打印的项目级统计。它按识别到的 `torch API` 次数算，不按文件数算。

## Unsupported API

当前有 mapping 但带了不支持参数，或者根本没找到 matcher 处理时，PaConvert 会保留原调用，并在源码里打 `>>>>>>` 标记，提醒人工处理。
