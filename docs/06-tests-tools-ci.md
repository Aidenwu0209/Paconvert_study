# 06. tests、tools、CI 分别在保护什么

如果你刚改完一条 mapping，最容易低估的就是这一层：代码能转出来，不等于这次改动已经站住。`tests/`、`tools/` 和 CI 关心的是三个不同的问题，最好分开看。

## `tests/test_*.py`：先卡 API 行为回归

根目录的 `tests/test_*.py` 是最贴近日常开发的一层。大多数情况就是一文件一个 API，直接围绕某条 mapping 写输入、跑转换、比较结果。

这些测试不是手工拼转换流程，而是走 `tests/apibase.py` 的 `APIBase.run()`。它会把内嵌的 PyTorch 代码先写到临时文件，再调 `Converter` 做真实转换。支持 case 会执行转换前后的代码并比较结果；不支持 case 则会检查输出里是不是出现了 `>>>>>>`。

所以你改一个 API，第一道回归线通常就落在这里：这条规则在常见调用形态下还能不能转，对明确 unsupported 的输入有没有老老实实打标，而不是静默改坏语义。

## `tests/code_library/`：再卡源码文本和大样例

有些改动不是数值结果先出问题，而是输出代码的形态先漂了。这时就不是 `tests/test_*.py` 一层能完全兜住的。

`tests/code_library/code_case/` 维护的是一组 `torch_code/...` 和 `paddle_code/...` 的成对文件，配合 `tools/consistency/consistency_check.py` 做逐文件对比。它保护的是“生成出来的源码文本还像不像预期”，而不是运行结果。

`tests/code_library/model_case/` 则更像大脚本 smoke test，配合 `tools/modeltest/modeltest_check.py` 跑。你可以把它理解成更接近真实项目脚本的一层回归。

所以一个新增 API 不一定每次都要碰 `code_case` 或 `model_case`，但只要你的改动已经影响输出源码结构，或者可能波及更大脚本，就该想到这两层。

## `validate_unittest`：它查的是测试覆盖面，不是代码对错

`tools/validate_unittest/validate_unittest.py` 最容易让人误判。pytest 能过，不代表它也会过。

它会记录每个 `APIBase.run(...)` 里真实执行过的调用形态，再回头检查这些测试有没有把一条 mapping 最容易出错的写法覆盖到，比如 `all args`、`all kwargs`、`kwargs out of order`、省略默认参数这些情况。

所以你如果只写一个最小 happy path，行为测试也许是绿的，`validate_unittest` 还是会拦你。它保护的是“这条规则以后改动时还有没有足够样本可回归”。

## `validate_docs`：它查的是配置和文档有没有漂

`tools/validate_docs/validate_docs.py` 不看代码能不能跑，它看 docs 侧的映射信息和 PaConvert 代码里的 JSON 配置是不是还对得上。

这里会交叉比对 `paconvert/api_mapping.json`、`paconvert/attribute_mapping.json`、`paconvert/api_alias_mapping.json` 和 docs 侧导出的 `docs_mappings.json`。`paddle_api`、`kwargs_change`、`args_list` 这些字段一旦改了，文档没同步，往往就是这里先报。

这也是为什么“我只改了一条 mapping”不一定等于工程闭环已经完成。对维护者来说，配置和文档是两份要一起保的资产。

## `tools/consistency`、`modeltest`、`coverage`：它们会在不同位置拦你

`tools/consistency/consistency_check.py` 会在你碰输出代码形态时拦你，防止源码级样例和预期文本漂移。  
`tools/modeltest/modeltest_check.py` 会在更大的模型样例上拦你，防止局部修复引出整段脚本跑不通。  
`tools/coverage/coverage_diff.py` 则关注覆盖率，防止新增改动没有足够测试兜底。

这些脚本的意义不一样，但合在一起看，都是在补“单个 API 测试过了也未必够”的那部分空白。

## CI 和 PR 模板：最后一道公开门面

`.github/workflows_origin/` 里当前能直接看到的是 `tests.yml`、`lint.yml`、`coverage.yml`。它们比较薄，主要还是安装依赖，再去调 `make test`、`make lint`、`make coverage`。

但只看这三个 workflow 不够。`scripts/` 和 `docs/CONTRIBUTING.md` 里还能看到 `consistency`、`modeltest`、`install`、`PRTemplate` 这些检查项。这说明仓库里公开能看到的 GitHub workflow，比维护流程里实际考虑的检查面要窄。

`.github/PULL_REQUEST_TEMPLATE.md` 和 `tools/prTemplate/prTemplate_check.py` 则是另一条线：它们不关心 API 语义，关心的是 PR 描述有没有按仓库要求把 `PR Docs`、`PR APIs` 这些信息写完整。

## 一个新增 API 的 PR，通常会在哪些地方挂

最常见的几类问题其实很稳定。

1. `tests/test_<api>.py` 只写了最小用例，`validate_unittest` 认为覆盖不够。
2. `args_list`、`kwargs_change` 改了，但 docs 侧没同步，`validate_docs` 先报。
3. 改动影响了输出代码文本，却没补 `tests/code_library/code_case/`，`consistency` 对不上。
4. 测试本身补得少，`coverage` 过不去。
5. PR 描述没按模板写，`prTemplate` 这一层会拦。

所以从开发动作上看，`tests`、`tools`、CI 不是三块并列目录，而是一条逐步收紧的防线：先查 API 行为，再查覆盖面和文档对齐，最后查更大样例和提交流程。
