# 05. 新增或修改一个 API 映射，最小闭环是什么

加一个 API 时，先别想着“我要写哪段代码”，先判断这条规则落在哪一层。大多数需求只会停在 `paconvert/api_mapping.json`；少数会继续落到 matcher；再少数才需要动 transformer。

## 先判断：这是 mapping 问题，还是识别问题

第一眼先看调用长什么样。它是包级函数、类方法，还是属性访问？它是单纯换名字，还是参数语义也要变？它有没有明确的不支持边界？这三个判断会直接决定你下一步打开哪个文件。

如果调用已经能被 `BasicTransformer` 识别出来，只是要换目标 API、改参数名、补默认值，那就先去 `paconvert/api_mapping.json`。如果你已经发现“这个 API 连完整名都恢复不出来”或者“import 阶段就认错包了”，那才是 transformer 层的问题。

## 动手时先开哪几个文件

推荐顺序不是从 `api_matcher.py` 顶部往下翻，而是先找同类样板。

1. 先看 `tests/test_<api>.py`，确认仓库里有没有现成测试，顺便看这个 API 平时怎么写。
2. 再看 `paconvert/api_mapping.json`，找同类 API 现在怎么配。
3. 如果 mapping 看起来不够表达，再去 `paconvert/api_matcher.py` 找能不能复用已有 matcher。
4. 只有你开始怀疑参数归一化、helper 注入或者 AST 识别边界时，才继续往 `paconvert/base.py`、`paconvert/transformer/basic_transformer.py`、`paconvert/transformer/import_transformer.py` 里钻。

这个顺序的好处是，你会先知道“现有体系打算怎么表达这类规则”，而不是一上来就被大文件淹没。

## 什么时候只改 `api_mapping.json`

如果需求能完全落在现有字段里，先别新写 matcher。典型情况有三种。

第一种是单纯改前缀，比如 `torch.add` 这种 `ChangePrefixMatcher` 场景。第二种是 API 名直接换掉，比如 `ChangeAPIMatcher`。第三种是 API 结构不变，但参数名要改、Paddle 端要补默认值，或者需要声明一组不支持参数，这类通常落在 `GenericMatcher`，`torch.optim.SGD` 就是典型例子。

这时你主要会改这些字段：`Matcher`、`paddle_api`、`args_list`、`min_input_args`、`kwargs_change`、`unsupport_args`、`paddle_default_kwargs`。如果你的需求已经能完整写进这几个字段，基本没必要再下探一层。

## 什么时候该写或改 matcher

当 JSON 已经表达不完需求时，再去 `paconvert/api_matcher.py`。最常见的信号不是“这条 API 很复杂”，而是你已经没法只靠字段描述输出形态了。

比如多个 torch 参数要一起决定一个 paddle 参数，或者输出不再是一句函数调用，而是多句代码、临时变量、`paddle.assign(...)`、helper 函数、`*args` / `**kwargs` 特判，这些都更像 matcher 该做的事。类方法如果还依赖 `self.paddleClass` 来决定接收者，也通常会落到 matcher。

一个很实用的判断是：如果你脑子里想的还是“把某几个 kwargs rename 一下”，先别写 matcher；如果你已经开始想输出模板字符串，说明这条规则大概率超出 mapping 能力了。

## 什么时候才需要碰 transformer

这属于少数情况。只有当问题已经不是“怎么改写”，而是“系统压根没认出来”时，才值得去 `transformer/` 目录找答案。

常见场景包括：import 被误判，本地模块被当成 torch 生态删掉；某种 alias 没进 `imports_map`，导致 canonical API 恢复失败；类方法或属性访问的边界判断错了；或者你需要跨节点、跨作用域插语句，matcher 这一层已经不够表达。

这里顺手再提醒一次：`paconvert/transformer/tensor_requires_grad_transformer.py` 虽然存在，但当前默认链路没有接它。所以如果你是为了修 `requires_grad` 相关行为，不能先假设改这个文件就会生效。

## 测试怎么补，才算闭环

加一个普通 API，最低限度至少要补 `tests/test_<api>.py`。实际写的时候，更建议按调用形态补，而不是只写一个 happy path。

通常先有一个最小支持 case，再补一个全关键字 case、一个关键字乱序 case、一个依赖默认参数的 case。如果这条规则明确只支持一个子集，还要再补一个 `unsupport=True` 的 case。`tools/validate_unittest/validate_unittest.py` 盯的就是这类覆盖面：它会把测试里的调用形态反推回 `args_list` 和 `min_input_args`，缺一种常见写法都可能被卡住。

如果你的改动影响的不只是“能不能跑通”，还影响输出代码长什么样，就继续补 `tests/code_library/code_case/`。这类样例比的是转换后的源码文本，不是运行结果。更大范围的模型级回归才会落到 `tests/code_library/model_case/`。

## `validate_docs`、`validate_unittest` 和 CI 会在哪拦你

`validate_unittest` 最常见的报错不是代码错，而是测试覆盖不完整。只写一个最小用例、没有全 kwargs、没有乱序 kwargs，或者 `args_list` 已经改了但测试形态没跟上，都会在这里暴露。

`validate_docs` 看的是配置和文档是否对齐，不看代码能不能跑。`paddle_api`、`kwargs_change`、`args_list` 这些字段一旦改了，文档侧如果没同步，往往这里会先报。

CI 里能直接看到的是 `.github/workflows_origin/tests.yml`、`lint.yml`、`coverage.yml`。另外 `scripts/` 和 `docs/CONTRIBUTING.md` 还提到 `modeltest`、`consistency`、`install`、`PRTemplate`。对一个新增 API 来说，PR 前最常挂的通常是三类问题：行为测试没过、覆盖率不够、代码样例文本和预期不一致。

## 一个稳一点的动手顺序

1. 在 `paconvert/api_mapping.json` 里找同类 API，先判断能不能复用现有 matcher。
2. 只要 mapping 能表达，就先改 mapping；不够再去 `paconvert/api_matcher.py`。
3. 立刻补 `tests/test_<api>.py`。
4. 先跑这个单测文件，再跑 `tools/validate_unittest/validate_unittest.py -r tests/test_<api>.py`。
5. 如果参数名、签名或 docs 映射受影响，再看 `tools/validate_docs/validate_docs.py`。
6. 如果输出源码形态也变了，补 `tests/code_library/code_case/`。

## 最小改动清单

支持一个普通难度的 API，常见闭环就是下面这几项：

1. `paconvert/api_mapping.json`
2. `tests/test_<api>.py`
3. 必要时改 `paconvert/api_matcher.py`
4. 必要时补 `tests/code_library/code_case/`
5. 参数文档或 docs 映射受影响时，再补对应文档改动

如果你发现自己已经准备去改 `paconvert/transformer/basic_transformer.py`、`paconvert/transformer/import_transformer.py` 或 `paconvert/base.py`，先停一下再确认一遍。那通常已经不是“补一条 mapping”，而是在改识别框架本身。
