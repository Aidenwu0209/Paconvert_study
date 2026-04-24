# 05. 新增或修改一个 API

先判断问题落在识别层还是规则表达层。调用已经能被 `BasicTransformer` 识别，只是要换 API 名、改参数名、补默认值，就先看 `paconvert/api_mapping.json`；完整 API 名都恢复不出来，才去 `paconvert/transformer/`。

## 1. 看调用有没有被识别

先找 `tests/test_<api>.py` 或同类测试，看输入长什么样。包级函数、类方法、属性访问走的分支不一样，`torch.add(...)` 和 `x.add(...)` 就不能混成一条规则。

`BasicTransformer` 能拿到 canonical API 时，下一步看 mapping。`import torch as th`、`from torch.nn import functional as F` 这种 alias 没恢复成功时，回到 `paconvert/transformer/import_transformer.py` 和 `paconvert/base.py` 查 `imports_map[file]`。

属性访问也要先分清。`x.device`、`tensor.T` 不走普通 `Call`，类方法还会受 `self.paddleClass` 影响。入口判断错了，后面改 JSON 会一直没命中。

## 2. mapping 能表达就别写 matcher

`paconvert/api_mapping.json` 能覆盖很多普通改动：`Matcher`、`paddle_api`、`args_list`、`min_input_args`、`kwargs_change`、`unsupport_args`、`paddle_default_kwargs`。

只改前缀，用 `ChangePrefixMatcher`，`torch.add` 是例子。只改 API 名，看 `ChangeAPIMatcher`。位置参数要按 `args_list` 归一化、再改参数名或补默认值，看 `GenericMatcher`，`torch.optim.SGD` 是例子。

`unsupport_args` 也属于 mapping 能表达的范围。某些参数不能安全转换时，优先在 JSON 里写清边界，再用 `tests/test_<api>.py` 的 `unsupport=True` 固定输出行为。

`args_list` 要和测试调用形态一起看。位置参数顺序、`*` 后 keyword-only 参数、`min_input_args` 都会影响 `BaseMatcher.parse_args_and_kwargs()` 的判断；测试只覆盖一种写法时，mapping 很容易看起来“能跑”，但边界不稳。

## 3. mapping 不够时复用 matcher

`paconvert/api_matcher.py` 适合带着需求搜，不适合从头翻。多个 torch 参数共同决定一个 paddle 参数、输出要变多行、要临时变量、要 `paddle.assign(...)`、要 helper 函数、要处理 `*args` / `**kwargs`，这些都超过了纯 JSON 字段。

能用已有 matcher 就复用。开始在脑子里拼输出模板时，再考虑新 matcher。

新 matcher 需要 helper 时走 `BaseMatcher.enable_utils_code()`，不要在单个转换点直接写文件；落盘由 `UtilsFileHelper.write_code()` 统一处理。

## 4. transformer 是最后手段

`paconvert/transformer/basic_transformer.py` 和 `paconvert/transformer/import_transformer.py` 处理的是识别框架，不是单条 API 的常规入口。

import 被误判、本地模块被当成 torch 生态、alias 没进 `imports_map`、类方法和属性访问边界错了，才考虑动 transformer。`paconvert/transformer/tensor_requires_grad_transformer.py` 当前不在默认链路里，修相关行为时不能假设改它就生效。

## 5. 测试和校验

`tests/test_<api>.py` 至少补最小支持 case、全 kwargs、kwargs 乱序、默认参数省略；有明确不支持边界时补 `unsupport=True`。`tools/validate_unittest/validate_unittest.py` 会卡这些调用形态。

参数名、签名、`kwargs_change` 变了，要看 `tools/validate_docs/validate_docs.py`。输出源码形态变了，补 `tests/code_library/code_case/` 并看 `tools/consistency/consistency_check.py`。影响更像模型脚本，再看 `tests/code_library/model_case/`。

`.github/PULL_REQUEST_TEMPLATE.md` 里的 `PR Docs`、`PR APIs` 也要填。维护者会用它快速定位这次改动影响了哪些 API 和文档。

单测失败先看转换后的临时文件，再看运行结果。很多 API 的问题出在 PaConvert 生成的源码形态，Paddle 结果不一致只是后面的表现。

## 最小行动清单

1. 在 `paconvert/api_mapping.json` 找同类 API。
2. mapping 能表达就只改 JSON；不够再碰 `paconvert/api_matcher.py`。
3. 补 `tests/test_<api>.py`。
4. 跑目标单测和 `tools/validate_unittest/validate_unittest.py -r tests/test_<api>.py`。
5. 参数文档受影响时处理 `validate_docs`；源码文本受影响时补 `tests/code_library/code_case/`。
6. 准备改 `basic_transformer.py`、`import_transformer.py`、`base.py` 前，重新确认问题确实是识别层问题。
