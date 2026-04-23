# 07. 核心文件速查表

这页不是正文，主要给“读到一半忘了该回哪个文件”时查。表格按角色分成三组：主链路、配置/辅助、测试/校验。

## 主链路核心文件

| 文件路径 | 阶段 | 关键类 / 函数 | 上游 | 下游 | 优先级 | 一句话提醒 |
| --- | --- | --- | --- | --- | --- | --- |
| `setup.py` | CLI 注册 | `setup()` | shell / pip | `paconvert.main:main` | A | console script 在这里，不在 README。 |
| `paconvert/main.py` | 参数解析 | `main()` | `setup.py` | `Converter.run()` | A | 这里只解释参数和任务颗粒度，不做 AST。 |
| `paconvert/converter.py` | 任务调度 | `Converter.run()`、`transfer_dir()`、`transfer_file()`、`transfer_node()` | `main.py` | transformer 链、输出 | A | 想先走通主流程，先看它。 |
| `paconvert/transformer/import_transformer.py` | import 恢复 | `ImportTransformer` | `transfer_node()` | `imports_map`、补全后的 API 名 | A | 不先跑它，后面的 matcher 看不到完整 API。 |
| `paconvert/transformer/basic_transformer.py` | 主 AST 改写 | `BasicTransformer` | `ImportTransformer` | `api_matcher.py` | A | 大多数 API 都是在这里被识别并分发的。 |
| `paconvert/api_matcher.py` | 代码生成 | `ChangePrefixMatcher`、`GenericMatcher` 等 | `BasicTransformer` | 新 AST 片段 / helper 登记 | A | 带着具体 API 去搜，不要从头硬啃。 |

## 配置与辅助文件

| 文件路径 | 阶段 | 关键类 / 函数 | 上游 | 下游 | 优先级 | 一句话提醒 |
| --- | --- | --- | --- | --- | --- | --- |
| `paconvert/global_var.py` | 全局配置加载 | `GlobalManager` | JSON 配置 | import / matcher | A | 哪些包会被认成 torch 生态，先看这里。 |
| `paconvert/base.py` | 公共底座 | `BaseTransformer`、`BaseMatcher` | `Converter` | 所有 transformer / matcher | A | 参数归一化、作用域插桩、helper 注入都在这里。 |
| `paconvert/api_mapping.json` | API 声明 | 每条 mapping 项 | `GlobalManager.API_MAPPING` | `get_api_matcher()` | A | 新增普通 API，通常先改这里。 |
| `paconvert/api_alias_mapping.json` | alias 归一 | alias key/value | `GlobalManager.ALIAS_MAPPING` | canonical API 恢复 | B | `torch.absolute -> torch.abs` 这种归一在这里。 |
| `paconvert/api_wildcard_mapping.json` | 通配规则 | wildcard mapping | `GlobalManager.API_WILDCARD_MAPPING` | `get_api_matcher()` | B | 文件不大，但能解释 wildcard 是怎么接进来的。 |
| `paconvert/utils.py` | helper 落盘 | `UtilsFileHelper` | matcher / converter | `paddle_utils.py` 或目标文件 | B | 为什么 helper 最后统一写文件，答案在这里。 |
| `paconvert/transformer/custom_op_transformer.py` | custom op 支线 | `PreCustomOpTransformer`、`CustomOpTransformer` | `BasicTransformer` 之后 | 壳子改写、不支持提示 | B | 普通 API 不必先看，但 custom op 会绕到这里。 |
| `paconvert/transformer/tensor_requires_grad_transformer.py` | 专用改写 | `TensorRequiresGradTransformer` | 理论上属于 transformer 链 | 当前默认链路未接入 | B | 文件存在，不等于默认一定会跑。 |

## 测试与校验文件

| 文件路径 | 阶段 | 关键类 / 函数 | 上游 | 下游 | 优先级 | 一句话提醒 |
| --- | --- | --- | --- | --- | --- | --- |
| `tests/apibase.py` | 单测基座 | `APIBase.run()`、`convert()` | `tests/test_*.py` | `Converter`、结果比较 | A | 想知道测试到底怎么调 PaConvert，就看这个。 |
| `tests/test_add.py` | 简单 API 样板 | `test_case_*` | `APIBase` | `torch.add` 回归 | A | 读简单 trace 的最好入口。 |
| `tests/test_optim_SGD.py` | 参数改写样板 | `test_case_*` | `APIBase`、helper 文件 | `torch.optim.SGD` 支持 / 不支持边界 | A | 看 `GenericMatcher` 很合适。 |
| `tests/code_library/code_case/__init__.py` | 源码级样例注册 | `CODE_CONSISTENCY_MAPPING` | `tools/consistency` | `torch_code` / `paddle_code` 配对样例 | B | 输出代码形态变了，通常要回这里。 |
| `tests/code_library/model_case/__init__.py` | 模型级样例注册 | `MODEL_LIST` | `tools/modeltest` | 模型脚本转换与运行 | B | 影响更大样例时再碰。 |
| `tools/validate_unittest/validate_unittest.py` | 测试规范检查 | `RecordAPIRunPlugin`、`check_call_variety()` | `tests/test_*.py` | `validation_report.md` | A | pytest 能过，不等于它不会报。 |
| `tools/validate_docs/validate_docs.py` | 文档对齐 | `check_mapping_args()` 等 | docs 侧映射、PaConvert JSON | 错误日志 | A | 改参数名映射时，这里很容易先炸。 |
| `tools/consistency/consistency_check.py` | 源码文本回归 | `convert_pytorch_code_to_paddle()` | `tests/code_library/code_case/` | diff 输出 | B | 它保护的是生成代码文本，不是数值结果。 |
| `tools/modeltest/modeltest_check.py` | 大样例 smoke test | `run_model()` | `tests/code_library/model_case/` | 运行成功 / 失败 | B | 更像真实项目脚本的回归在这里。 |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR 约束 | 模板本身 | PR 页面 | `prTemplate_check.py` | C | 不是代码逻辑，但提交时会用到。 |
| `.github/workflows_origin/tests.yml` | 可见 CI 入口 | `make test` | push / pull request | pytest | C | 公开 workflow 只覆盖维护流程的一部分。 |

## 最短回看路径

如果你只是想把主线重新捡起来，回看这四个文件就够了：`paconvert/main.py`、`paconvert/converter.py`、`paconvert/transformer/import_transformer.py`、`paconvert/transformer/basic_transformer.py`。

如果你已经准备直接改一个 API，就从 `paconvert/api_mapping.json`、`paconvert/api_matcher.py` 和 `tests/test_<api>.py` 开始，不用先把整张表再读一遍。
