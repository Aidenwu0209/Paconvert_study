# 术语表

## AST

`Converter.transfer_file()` 用 `ast.parse()` 读 `.py` 文件，再由 `astor.to_source()` 写回。

## Transformer

继承 `BaseTransformer` 的 AST 访问器。`ImportTransformer` 做 import 恢复，`BasicTransformer` 做主分发。

## Matcher

继承 `BaseMatcher` 的 API 规则类。`ChangePrefixMatcher` 改前缀，`GenericMatcher` 处理参数归一化、改名、默认值。

## Mapping

`paconvert/api_mapping.json` 里的 API 规则。新增普通 API 通常先改这里。

## Alias Mapping

`paconvert/api_alias_mapping.json` 里的别名归一，比如 `torch.absolute -> torch.abs`。

## Wildcard Mapping

`paconvert/api_wildcard_mapping.json` 里的通配规则，比如 `einops.layers.torch.*`。

## Canonical Torch API

import 别名补全、alias 归一后的 API 全名。`F.relu` 会先还原成 `torch.nn.functional.relu`。

## Unsupported API

当前 mapping 无法安全处理时，PaConvert 保留原调用，并在输出里打 `>>>>>>`。

## Summary / Convert Rate

`Converter.run()` 的项目级统计，按识别到的 torch API 次数算，不按文件数算。
