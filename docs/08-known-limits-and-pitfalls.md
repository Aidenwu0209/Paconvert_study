# 08. 易误判现象

## 自己封装的函数没改

现象：当前文件只有 `my_add(x, y)`，真正的 `torch.add()` 藏在另一个模块里。  
原因：PaConvert 主要看当前文件 AST 里能否恢复出 torch 生态前缀，不跨包做静态分析。  
先看：`paconvert/transformer/import_transformer.py`、`paconvert/base.py` 的 API 名恢复逻辑。

## import 顺序、空行、拆行变了

现象：逻辑改对了，输出代码的 import 顺序和原文件排版都变了。  
原因：`Converter.transfer_file()` 后段会走 `astor.to_source()`、`black.format_str()`、`isort.code()`。  
先看：`paconvert/converter.py` 的 `.py` 文件输出分支。

## 注释丢了

现象：行注释消失，docstring 还在。  
原因：普通注释不在 Python AST 里，`astor.to_source()` 回写时保不住；docstring 是字符串节点。  
先看：`paconvert/converter.py` 里 `ast.parse()` 到 `astor.to_source()` 的链路。

## 输出多了几行或多了 `paddle_utils.py`

现象：一行 PyTorch 调用变成多行 Paddle 代码，目录输出里出现 `paddle_utils.py`。  
原因：matcher 可能插入临时变量、多节点结果，或通过 `BaseMatcher.enable_utils_code()` 登记 helper。  
先看：`paconvert/api_matcher.py`、`paconvert/utils.py::UtilsFileHelper`。

## 出现 `>>>>>>`

现象：原调用被保留，行前出现 `>>>>>>`。  
原因：转换链判断该调用不能自动处理，`Converter.mark_unsupport()` 在源码字符串阶段打标。  
先看：`paconvert/converter.py::mark_unsupport()`，再回查对应 matcher 的 `unsupport_args`。

`torch.optim.SGD` 带 `momentum`、`dampening`、`nesterov` 时就是这种情况。当前规则没有静默删参，风险留给人工处理。

## summary 数字比预想大

现象：一个很小的文件显示 3 个 API。  
原因：summary 按识别到的 torch API 次数统计；`simple_add` 里有两个 `torch.tensor(...)` 和一个 `torch.add(...)`。  
先看：`Converter.run()` 的 summary 统计字段。

## `torch.add` 和 `x.add` 对不上

现象：改了 `torch.add` 的 mapping，`x.add(...)` 的输出没按预期变化。  
原因：前者是包级函数，后者是类方法，`BasicTransformer` 分发路径不同。  
先看：`paconvert/transformer/basic_transformer.py` 的类方法分支，再查对应 matcher。

## `tensor_requires_grad_transformer.py` 没生效

现象：看到 `paconvert/transformer/tensor_requires_grad_transformer.py`，但默认转换链没有跑它。  
原因：当前 `Converter.transfer_node()` 没把 `TensorRequiresGradTransformer` 接进默认顺序。原因不能靠现有文件推断。  
先看：`paconvert/converter.py::transfer_node()`。

## 配置文件里的依赖没改

现象：Python 源码改成 Paddle 了，`pyproject.toml`、`setup.cfg`、YAML、shell 脚本里的 `torch` 还在。  
原因：`Converter.transfer_file()` 只对 `requirements.txt` 做简单 `torch -> paddlepaddle-gpu` 替换，其他非 Python 文件按原样复制。  
先看：`paconvert/converter.py` 的 `requirements.txt` 分支。

## visible workflow 看起来很少

现象：`.github/workflows_origin/` 只有 `tests.yml`、`lint.yml`、`coverage.yml`，但 PR 讨论里提到更多检查。  
原因：`scripts/` 和 `docs/CONTRIBUTING.md` 还保留 `modeltest`、`consistency`、`install`、`PRTemplate` 等脚本入口。  
先看：`.github/workflows_origin/`、`scripts/`、`docs/CONTRIBUTING.md`。
