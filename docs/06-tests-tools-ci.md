# 06. tests、tools、CI 分别在保护什么

如果你只把 `tests/` 看成“跑 pytest 的地方”，会漏掉很多信息。  
这个仓库实际上有三层保护：

1. API 行为回归
2. 源码输出形态回归
3. 文档、测试规范和提交流程约束

## `tests/` 目录怎么组织

### 根目录 `tests/test_*.py`

这是最密的一层。

当前本地工作树里，根目录 `tests/test_*.py` 文件数是 `1760` 个，这是我在 `2026-04-22` 本地统计到的数字。  
它的组织方式很朴素：大多数情况就是“一文件一个 API”。

典型特点：

1. 文件名直接对应 API
2. 通过 `APIBase` 跑转换和结果比对
3. 支持 `unsupport=True` 去验证 `>>>>>>` 标记

### `tests/apibase.py`

这是单测基座。

它把一个 API 测试拆成固定动作：

1. 把内嵌的 PyTorch 代码临时写到 `test_project/pytorch_temp.py`
2. 调 `Converter` 做一次真实转换
3. 如果是支持 case，就执行转换前后的代码并比较结果
4. 如果是不支持 case，就检查输出里是否出现 `>>>>>>`

所以你写 `tests/test_xxx.py` 时，很多“怎么调 converter、怎么对比结果”的细活都不用重复写。

### helper 文件

比如：

1. `tests/optimizer_helper.py`
2. `tests/lr_scheduler_helper.py`

它们的作用不是测试框架，而是把某些 API 需要的固定样板代码抽出来，减少单测文件里的重复。

### `tests/code_library/code_case/`

这块是源码级一致性样例。

它维护一组：

1. `torch_code/...`
2. `paddle_code/...`

的成对文件，再由 `tools/consistency/consistency_check.py` 批量转换和逐文件比对。

它保护的不是运行结果，而是“生成的源码文本是不是还长这样”。

### `tests/code_library/model_case/`

这块更像模型级 smoke test。

`tools/modeltest/modeltest_check.py` 会把这些模型脚本转成 Paddle，再尝试直接运行。

它保护的是“在更像真实项目的脚本里，改动有没有带来大面积失效”。

### 其他子目录

像：

1. `tests/distributed/`
2. `tests/flash_attn_tests/`

说明仓库里还保留了一些专题子集，不全都走“根目录一文件一个 API”的模式。

## `tools/` 目录里几类工具分别干什么

当前 `tools/` 下面我实际看到这些子目录：

1. `codestyle`
2. `consistency`
3. `coverage`
4. `docker`
5. `modeltest`
6. `prTemplate`
7. `validate_docs`
8. `validate_unittest`

可以粗分成 4 类。

### 1. 规则正确性

1. `tools/validate_unittest/validate_unittest.py`
2. `tools/validate_docs/validate_docs.py`

前者管测试规范，后者管文档和配置一致性。

### 2. 结果形态回归

1. `tools/consistency/consistency_check.py`
2. `tools/modeltest/modeltest_check.py`

前者看源码级 diff，后者看模型脚本能不能跑。

### 3. 流程质量门

1. `tools/coverage/coverage_diff.py`
2. `tools/prTemplate/prTemplate_check.py`

一个看增量覆盖率，一个看 PR 描述模板。

### 4. 环境与辅助

1. `tools/docker/`
2. `tools/codestyle/`

这些更多是给脚本和 CI 用。

## `validate_unittest` 在看什么

它最关键的逻辑在 `tools/validate_unittest/validate_unittest.py`。

不是简单“跑不跑得过”，而是收集每个 `APIBase.run(...)` 里真实执行过的调用代码，再回头检查：

1. 有没有 `all args`
2. 有没有 `all kwargs`
3. 有没有 `kwargs out of order`
4. 有没有“省略默认参数”的 case

也就是说，它管的是“这个 API 的测试有没有把 mapping 里最容易出错的参数形态覆盖到”。

所以你写一个只有单 happy path 的测试文件，很可能 pytest 能过，但 `validate_unittest` 仍然会报。

## `validate_docs` 在对齐什么

`tools/validate_docs/validate_docs.py` 会拿 docs 侧导出的 `docs_mappings.json`，和 PaConvert 代码里的：

1. `paconvert/api_mapping.json`
2. `paconvert/attribute_mapping.json`
3. `paconvert/api_alias_mapping.json`

做交叉检查。

它关注的是：

1. `paddle_api` 是否一致
2. `kwargs_change` 是否一致
3. `args_list` 是否一致
4. 有没有 matcher 已存在，但文档缺失

注意一个现实问题：  
如果你只在本仓库改代码，没有同步准备 docs 侧的映射数据，`validate_docs` 这条线不一定能自动“绿掉”。

## CI / PR 模板相关目录是干什么的

### `.github/PULL_REQUEST_TEMPLATE.md`

这里约束的是 PR 描述结构，不是代码逻辑。  
模板要求至少写：

1. `PR Docs`
2. `PR APIs`

`tools/prTemplate/prTemplate_check.py` 和 `scripts/PRTemplate_check.sh` 都在围绕这个模板做检查。

### `.github/workflows_origin/`

当前仓库里能直接看到 3 个 workflow 文件：

1. `tests.yml`
2. `lint.yml`
3. `coverage.yml`

它们很轻：

1. 安装依赖
2. 调 `make test` / `make lint` / `make coverage`

### `scripts/`

这里是另一层更完整的检查脚本集合。  
我实际确认到的文件包括：

1. `scripts/unittest_check.sh`
2. `scripts/code_style_check.sh`
3. `scripts/code_coverage_check.sh`
4. `scripts/consistency_check.sh`
5. `scripts/modeltest_check.sh`
6. `scripts/install_check.sh`
7. `scripts/PRTemplate_check.sh`
8. `scripts/run_ci.sh`

跟 `.github/workflows_origin/` 对比着看，能发现一个事实：

1. visible GitHub workflow 只覆盖了其中一部分
2. 仓库维护流程里实际考虑的检查项比公开 workflow 文件更多

## 一个新增 API 的 PR 通常要自查什么

我会按这个顺序自查：

1. `api_mapping.json` 的 `args_list`、`kwargs_change`、`unsupport_args`、`paddle_default_kwargs` 有没有和我想表达的语义一致
2. `tests/test_<api>.py` 里有没有最小支持 case、全 kwargs、乱序 kwargs、默认参数省略 case
3. 如果有不支持边界，是否显式写了 `unsupport=True`
4. 如果改动会影响源码形态，是否补了 `tests/code_library/code_case/`
5. 如果改动更像大样例回归风险，是否看过 `model_case`
6. `validate_unittest` 会不会因为测试样态单一而报
7. `validate_docs` 会不会因为参数名或签名漂移而报
8. PR 描述里有没有把 `PR Docs` 和 `PR APIs` 写完整

把这 8 项过一遍，基本已经不是“只改了一条 JSON”这种局部视角，而是完整工程闭环视角了。
