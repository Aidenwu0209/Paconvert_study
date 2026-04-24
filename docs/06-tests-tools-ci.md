# 06. 改完 API 后哪里会挂

`tests/test_<api>.py` 先拦行为回归。测试通过 `tests/apibase.py::APIBase.run()` 临时写 PyTorch 代码、调用 `Converter` 转换、执行两边代码并比较结果；`unsupport=True` 会检查输出里的 `>>>>>>`。新增 mapping 只写 happy path，通常不够。

`torch.optim.SGD` 这类 API 至少要覆盖位置参数、关键字参数、默认参数省略和 unsupported 参数。最小支持 case 只能证明规则跑得动，不能证明参数边界稳定。

`tools/validate_unittest/validate_unittest.py` 拦测试形态。它会记录 `APIBase.run(...)` 里的真实调用，检查有没有 all args、all kwargs、kwargs out of order、默认参数省略。pytest 绿了，这里仍可能因为覆盖形态太少报错。

失败时先看报告指出的调用形态，再回 `tests/test_<api>.py` 补 case。很多时候 matcher 没错，只是测试样本太单一。

`tools/validate_docs/validate_docs.py` 拦配置和文档漂移。`paconvert/api_mapping.json`、`attribute_mapping.json`、`api_alias_mapping.json` 里的 `paddle_api`、`kwargs_change`、`args_list` 变了，docs 侧映射没同步，这里会先报。

参数名改动最容易触发这条线。`kwargs_change` 里把 `lr` 改成 `learning_rate`，docs 侧还写旧字段时，单测可能没问题，`validate_docs` 仍会报。

`tools/consistency/consistency_check.py` 拦源码文本变化。改动影响输出代码形态时，需要看 `tests/code_library/code_case/` 的 `torch_code` / `paddle_code` 配对样例。更像真实脚本的回归放到 `tests/code_library/model_case/` 和 `tools/modeltest/modeltest_check.py`。

这类失败不要只看数值结果。formatter、helper 插入、多行代码模板都会影响源码文本，`code_case` 保护的是维护者认可的输出形态。

`.github/workflows_origin/tests.yml`、`lint.yml`、`coverage.yml` 是可见 CI 入口；`scripts/` 和 `docs/CONTRIBUTING.md` 还提到 `consistency`、`modeltest`、`install`、`PRTemplate`。PR 前常见挂点是测试形态不足、docs 映射没对齐、源码文本样例没更新、覆盖率不够、`.github/PULL_REQUEST_TEMPLATE.md` 信息缺失。

`tools/coverage/coverage_diff.py` 拦的是增量覆盖率。新增 matcher 或 transformer 分支时，只补一个支持 case 很容易过不了覆盖率；补 unsupported、乱序 kwargs、默认参数省略，通常比扩大无关测试更有用。

`tools/prTemplate/prTemplate_check.py` 和 `scripts/PRTemplate_check.sh` 关注 PR 描述。`PR Docs`、`PR APIs` 缺失时，代码本身没问题也可能被流程挡住。

CI 失败时先按层拆：pytest 失败看 `tests/test_<api>.py` 和转换临时文件；`validate_unittest` 失败补调用形态；`validate_docs` 失败同步 docs 映射；`consistency` 失败更新 `tests/code_library/code_case/` 的预期源码。不要把所有失败都当成 matcher 逻辑错。
