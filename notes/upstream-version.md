# 上游版本记录

## 这次实际读取的是哪套源码

1. 用户没有替换占位符时，默认上游路径是 `SOURCE_PACONVERT_PATH=./PaConvert`。
2. 这次本地实际确认到的仓库根目录是 `./`，包目录同时存在 `./PaConvert` 和 `./paconvert`。
3. 我额外执行了 `diff -qr ./PaConvert ./paconvert`，结果为空，说明这两个目录当前内容一致。
4. 由于 `setup.py` 的 console script 入口写的是 `paconvert.main:main`，正文统一使用 `paconvert/...` 这套路径表达运行链路。
5. `tests/`、`tools/`、`.github/` 不在 `./PaConvert` 目录里，而是在它所在的仓库根目录，所以第 5 部分内容是基于仓库根目录一起核对的。

## 分支与提交

- 上游目录：`/Users/wu/Desktop/wu/AAaabaidu/Paconvert`
- 默认源码包镜像：`/Users/wu/Desktop/wu/AAaabaidu/Paconvert/PaConvert`
- 当前分支：`master`
- 当前 commit：`85c9d0b76ec1a14ab839aaf54e3aecdff5468eb1`
- 阅读日期：`2026-04-22`

## 我确认过的关键文件

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
- `tools/README.md`
- `tools/validate_unittest/validate_unittest.py`
- `tools/validate_unittest/complete_mapping.py`
- `tools/validate_docs/validate_docs.py`
- `tools/validate_docs/auto_build_docs.py`
- `tools/consistency/consistency_check.py`
- `tools/modeltest/modeltest_check.py`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows_origin/tests.yml`
- `.github/workflows_origin/lint.yml`
- `.github/workflows_origin/coverage.yml`
- `docs/CONTRIBUTING.md`

## 已执行的最小验证

我在本地安装了 `requirements.txt` 里的最小依赖后，实际执行了以下转换：

- `examples/simple_add` 对应的 `torch.add`
- `examples/optim_sgd` 对应的 `torch.optim.SGD`
- 一个带 `momentum` / `dampening` / `nesterov` 的 `torch.optim.SGD` 不支持样例

这些执行都基于：

```bash
python3 paconvert/main.py -i <input.py> -o <output.py> --log_dir disable
```

## 仍然保留的几个不确定点

1. `paconvert/transformer/tensor_requires_grad_transformer.py` 明显是一个专用 transformer，但当前 `Converter.transfer_node()` 没把它加入默认链路。源码能确认“现在没用”，但不能确认“为什么后来不用了”。
2. `.github/workflows_origin/` 里只看到 `tests.yml`、`lint.yml`、`coverage.yml` 三个工作流；`docs/CONTRIBUTING.md` 和 `scripts/` 提到的 `ModelTest`、`CodeConsistency`、`PRTemplate` 更像另一套内部流水线命名。当前仓库能确认“脚本存在”，但不能只靠现有文件确认它们在外部 CI 平台上的真实绑定关系。
