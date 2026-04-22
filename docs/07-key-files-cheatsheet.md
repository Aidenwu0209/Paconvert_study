# 07. 核心文件速查表

下面这张表是给“过两周回来又忘了从哪看”的时候用的。

| 文件路径 | 负责的阶段 | 关键类 / 函数 | 上游是谁 | 下游是谁 | 推荐阅读优先级 | 一句话提醒 |
| --- | --- | --- | --- | --- | --- | --- |
| `setup.py` | 打包与 CLI 入口注册 | `setup()` | shell / pip 安装 | `paconvert.main:main` | A | 真正的 console script 在这里，不在 README。 |
| `paconvert/main.py` | CLI 参数解释 | `main()` | `setup.py` 的 `console_scripts` | `Converter.run()` | A | 这里只做参数解释和任务分发，不做 AST。 |
| `paconvert/converter.py` | 任务级调度 | `Converter.run()`、`transfer_dir()`、`transfer_file()`、`transfer_node()` | `paconvert/main.py` | transformer 链、输出文件 | A | 先看它，能最快把整条主链路串起来。 |
| `paconvert/global_var.py` | 全局静态配置 | `GlobalManager` | `paconvert/*.json` | `ImportTransformer`、`BasicTransformer` | A | 想知道“哪些包会被认成 torch 生态”，先看这里。 |
| `paconvert/base.py` | 公共底座 | `BaseTransformer`、`BaseMatcher` | `Converter.transfer_node()` | 所有 transformer / matcher | A | 参数归一化、作用域插桩、helper 注入都在这里。 |
| `paconvert/transformer/import_transformer.py` | import 预处理 | `ImportTransformer` | `Converter.transfer_node()` | `imports_map`、补全后的 API 名 | A | 不先看它，后面很多 API 名恢复逻辑都像黑盒。 |
| `paconvert/transformer/basic_transformer.py` | 主 AST 改写 | `BasicTransformer` | `ImportTransformer` | `api_matcher.py` | A | 绝大多数 API 都是在这里被识别并分发的。 |
| `paconvert/transformer/custom_op_transformer.py` | 自定义 C++ OP 特殊链路 | `PreCustomOpTransformer`、`CustomOpTransformer` | `BasicTransformer` 之后 | 不支持提示、壳子改写 | B | 它不是主流程核心，但解释了 custom op 为什么会被特殊对待。 |
| `paconvert/transformer/tensor_requires_grad_transformer.py` | 专用左值赋值改写 | `TensorRequiresGradTransformer` | 理论上属于 transformer 链 | 当前默认链路未接入 | B | 文件存在，但 `Converter.transfer_node()` 现在没用它。 |
| `paconvert/api_mapping.json` | API 规则声明 | 每个 API 的 mapping 项 | `GlobalManager.API_MAPPING` | `BasicTransformer.get_api_matcher()` | A | 大多数新增 API 支持都先从这里开始。 |
| `paconvert/api_alias_mapping.json` | API 别名归一 | alias key/value | `GlobalManager.ALIAS_MAPPING` | import 恢复后的 canonical API 名 | B | `torch.absolute -> torch.abs` 这种归一在这里。 |
| `paconvert/api_wildcard_mapping.json` | 通配规则 | `einops.layers.torch.*` 等 | `GlobalManager.API_WILDCARD_MAPPING` | `get_api_matcher()` | B | 当前文件很小，但能解释 wildcard mapping 是怎么接进来的。 |
| `paconvert/api_matcher.py` | 具体代码生成 | `ChangePrefixMatcher`、`GenericMatcher` 等 | `BasicTransformer` | 新 AST 节点 / helper 代码 | A | 不要从头硬啃，先找你关心的 matcher。 |
| `paconvert/utils.py` | helper 与通用工具 | `UtilsFileHelper`、`get_unique_name()` | matcher / converter | `paddle_utils.py` 或目标文件 | B | 多行 helper 为什么会统一落到 `paddle_utils.py`，答案在这里。 |
| `tests/apibase.py` | 单测基座 | `APIBase.run()`、`convert()` | `tests/test_*.py` | `Converter`、结果比较 | A | 想知道单测到底怎么调用 PaConvert，就看这个。 |
| `tests/test_add.py` | 真实 API 测例 | `test_case_*` | `APIBase` | `torch.add` 行为回归 | A | 读简单 API trace 的最好入口。 |
| `tests/test_optim_SGD.py` | 真实 API 测例 | `test_case_*` | `APIBase`、`optimizer_helper.py` | `torch.optim.SGD` 支持 / 不支持边界 | A | 读 `GenericMatcher` 的最好入口之一。 |
| `tests/code_library/code_case/__init__.py` | 源码级样例注册 | `CODE_CONSISTENCY_MAPPING` | `tools/consistency` | `torch_code` / `paddle_code` 配对样例 | B | 想补源码级一致性样例，要先改这里。 |
| `tests/code_library/model_case/__init__.py` | 模型级样例注册 | `MODEL_LIST` | `tools/modeltest` | 模型脚本转换与运行 | B | 只有影响更大样例时才需要碰。 |
| `tools/validate_unittest/validate_unittest.py` | 测试规范检查 | `RecordAPIRunPlugin`、`check_call_variety()` | `tests/test_*.py` | `validation_report.md` | A | pytest 能过，不等于它不会报。 |
| `tools/validate_docs/validate_docs.py` | 文档与配置对齐 | `check_mapping_args()` 等 | docs 侧 `docs_mappings.json`、PaConvert JSON | 错误日志 | A | 改参数名映射时，这里很容易先炸。 |
| `tools/consistency/consistency_check.py` | 源码文本回归 | `convert_pytorch_code_to_paddle()` | `tests/code_library/code_case/` | diff 输出 | B | 它保护的是“生成代码像不像预期”，不是数值结果。 |
| `tools/modeltest/modeltest_check.py` | 模型级 smoke test | `run_model()` | `tests/code_library/model_case/` | 运行成功 / 失败 | B | 真正像项目脚本的回归，在这里看。 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 提交流程约束 | 模板本身 | PR 页面 | `prTemplate_check.py` | C | 不是代码逻辑，但 CI 可能卡在这里。 |
| `.github/workflows_origin/tests.yml` | GitHub workflow | `make test` | push / pull request | pytest | C | 可见 workflow 比 `scripts/` 提到的检查项少。 |

## 读不动时的最短路径

如果你只有 15 分钟：

1. 先看 `paconvert/main.py`
2. 再看 `paconvert/converter.py`
3. 再看 `paconvert/transformer/import_transformer.py`
4. 最后拿 `tests/test_add.py` 对照 `paconvert/api_mapping.json`

如果你要直接改一个 API：

1. 先看 `paconvert/api_mapping.json`
2. 再搜 `paconvert/api_matcher.py` 里有没有现成 matcher
3. 最后补 `tests/test_<api>.py`
