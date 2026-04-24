# 上游版本说明

- 上游源码：`PaConvert`
- 默认源码路径：`./PaConvert`
- 文档路径写法：`paconvert/...`
- 分支：`master`
- commit：`85c9d0b76ec1a14ab839aaf54e3aecdff5468eb1`
- 阅读日期：`2026-04-22`

正文使用 `paconvert/...` 路径，是因为 `setup.py` 的 console script 入口注册到 `paconvert.main:main`。

## 核对文件

- `setup.py`
- `paconvert/main.py`
- `paconvert/converter.py`
- `paconvert/global_var.py`
- `paconvert/base.py`
- `paconvert/utils.py`
- `paconvert/api_mapping.json`
- `paconvert/api_alias_mapping.json`
- `paconvert/api_wildcard_mapping.json`
- `paconvert/api_matcher.py`
- `paconvert/transformer/import_transformer.py`
- `paconvert/transformer/basic_transformer.py`
- `paconvert/transformer/custom_op_transformer.py`
- `paconvert/transformer/tensor_requires_grad_transformer.py`
- `tests/apibase.py`
- `tests/test_add.py`
- `tests/test_optim_SGD.py`
- `tools/validate_unittest/validate_unittest.py`
- `tools/validate_docs/validate_docs.py`
- `tools/consistency/consistency_check.py`
- `tools/modeltest/modeltest_check.py`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows_origin/tests.yml`
- `.github/workflows_origin/lint.yml`
- `.github/workflows_origin/coverage.yml`
- `docs/CONTRIBUTING.md`

## 保留的不确定点

`paconvert/transformer/tensor_requires_grad_transformer.py` 当前不在默认 transformer 链里；源码能确认“没有接入”，不能只靠现有文件确认原因。

`.github/workflows_origin/` 只看到 `tests`、`lint`、`coverage` 三个 workflow；`scripts/` 和 `docs/CONTRIBUTING.md` 还提到 `modeltest`、`consistency`、`install`、`PRTemplate`。脚本存在可以确认，外部 CI 绑定方式不在当前文件里下结论。
