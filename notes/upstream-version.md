# 上游版本说明

## 源码范围

- 上游仓库：`/Users/wu/Desktop/wu/AAaabaidu/Paconvert`
- 默认源码路径占位符：`./PaConvert`
- 正文统一使用的路径前缀：`paconvert/...`

当前工作区同时存在 `./PaConvert` 和 `./paconvert` 两个目录，而且内容一致。由于 `setup.py` 注册的 console script 入口是 `paconvert.main:main`，正文统一使用小写路径。

## 分支与提交

- 分支：`master`
- commit：`85c9d0b76ec1a14ab839aaf54e3aecdff5468eb1`
- 阅读日期：`2026-04-22`

## 关键核对文件

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
- `tests/code_library/code_case/__init__.py`
- `tests/code_library/model_case/__init__.py`
- `tools/validate_unittest/validate_unittest.py`
- `tools/validate_docs/validate_docs.py`
- `tools/consistency/consistency_check.py`
- `tools/modeltest/modeltest_check.py`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows_origin/tests.yml`
- `.github/workflows_origin/lint.yml`
- `.github/workflows_origin/coverage.yml`
- `docs/CONTRIBUTING.md`

## 示例输出说明

`examples/simple_add/expected_paddle.py` 和 `examples/optim_sgd/expected_paddle.py` 都基于当前 commit 的实际转换结果整理。

## 仍保留的 `不确定`

1. `paconvert/transformer/tensor_requires_grad_transformer.py` 当前不在默认 transformer 链里；源码能确认“没有接入”，不能只靠现有文件确认“为什么后来不用它”。
2. `.github/workflows_origin/` 里只看到 `tests`、`lint`、`coverage` 三个 workflow；`scripts/` 和 `docs/CONTRIBUTING.md` 还提到 `modeltest`、`consistency`、`install`、`PRTemplate`。脚本存在可以确认，但它们在外部 CI 平台上的真实绑定方式，现有文件不足以下结论。
