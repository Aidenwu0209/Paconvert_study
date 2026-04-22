# 05. 新增或修改一个 API 映射，最小闭环是什么

这篇按“你下一步该去哪改”来写，不按概念分类。

## 先别急着改，先做 3 个判断

看到一个待支持 API 时，先回答这 3 个问题：

1. 它是包级函数、类方法，还是属性访问。
2. 它是“只改名字/参数名”就够，还是要改参数语义，甚至插多行代码。
3. 它对应的边界是“支持一个子集”还是“全量支持”。

这 3 个问题决定你到底应该只改 JSON、改 matcher，还是要碰 transformer。

## 新增一个 API 映射时，通常先看哪些文件

建议顺序：

1. `tests/test_<api>.py`
   - 先看仓库里是否已经有相关测试
2. `paconvert/api_mapping.json`
   - 看同类 API 现在怎么配
3. `paconvert/api_matcher.py`
   - 先找能不能复用已有 matcher
4. `paconvert/base.py`
   - 看参数归一化和 helper 注入机制
5. `paconvert/transformer/basic_transformer.py`
   - 只有怀疑“识别阶段就有问题”时再往这里看
6. `tools/validate_unittest/validate_unittest.py`
   - 看测试覆盖规范
7. `tools/validate_docs/validate_docs.py`
   - 看文档对齐会检查什么

如果你一开始就打开 `api_matcher.py` 从头往下翻，通常效率不高。

## 什么情况下只改 mapping 就够

最常见的是下面三类：

1. 只改包名前缀
   - 典型是 `ChangePrefixMatcher`
   - 例子：`torch.add`
2. 只改 API 名
   - 典型是 `ChangeAPIMatcher`
3. 参数结构没变，只是参数名改了、Paddle 端要补默认值，或者要声明少量不支持参数
   - 典型是 `GenericMatcher`
   - 例子：`torch.optim.SGD`

这时通常只需要动 `paconvert/api_mapping.json`：

1. `Matcher`
2. `paddle_api`
3. `args_list`
4. `min_input_args`
5. `kwargs_change`
6. `unsupport_args`
7. `paddle_default_kwargs`

如果你碰到的需求能完全落在这几个字段里，先别新写 matcher。

## 什么情况下要改 matcher

当你发现 JSON 字段已经表达不完需求时，就该去 `paconvert/api_matcher.py`。

典型信号有这些：

1. 多个 torch 参数一起决定一个 paddle 参数
2. 输出不能是一句函数调用，要变成多句
3. 需要引入临时变量
4. 需要 `paddle.assign(...)`
5. 需要额外 helper 函数
6. 需要处理 `*args` / `**kwargs`
7. 需要根据 `self.paddleClass` 改写类方法接收者

一个经验判断：

1. 如果你能说出“这条规则只是在 `kwargs_change` 上做 rename”，先别写 matcher
2. 如果你已经开始在脑子里写模板字符串了，多半就该写 matcher 了

## 什么情况下要补 transformer 逻辑

这是少数情况，不是默认路径。

只有当问题已经不在“这个 API 怎么改写”，而在“系统根本没把它识别出来”时，才应该去碰 transformer。

常见场景：

1. import 识别有问题
   - 比如本地模块被误删、第三方包被误认成 torch 包
2. API 全名恢复有问题
   - 比如某种别名场景没有进 `imports_map`
3. 类方法 / 属性识别边界有问题
   - 比如同名 Python 原生方法和 Tensor 方法撞车
4. 需要跨节点或跨作用域插入语句
   - matcher 本身已经不够表达
5. 自定义 C++ OP 这种特殊链路

再强调一次一个容易踩坑的点：

1. `paconvert/transformer/tensor_requires_grad_transformer.py` 存在
2. 但当前默认链路没有跑它
3. 所以如果你是为了修 `requires_grad` 左值赋值，不能先预设“改这个文件就会生效”

## 要补哪些测试

默认最少要补的是单 API 测试，也就是 `tests/test_<api>.py` 这一层。

通常我会按下面这个顺序补：

1. 一个最小支持 case
2. 一个全关键字 case
3. 一个关键字乱序 case
4. 一个省略默认参数的 case
5. 如果这条规则有明确边界，再补一个 `unsupport=True` 的 case

这是因为 `tools/validate_unittest/validate_unittest.py` 就在盯这些调用形态。

如果你的改动会影响“源码长什么样”，不只是数值行为，还要考虑加 `tests/code_library/code_case/` 样例。  
这类样例不是比较运行结果，而是比较转换后的源码文本。

如果你的改动更像模型级回归风险，再看要不要补 `tests/code_library/model_case/`。

## docs / validate_docs / validate_unittest / CI 会卡哪些问题

### docs

当前仓库的 `docs/CONTRIBUTING.md` 明确把“映射文档”和“PaConvert 规则”当成两条并行资产。  
这意味着你改了 `api_mapping.json`，不一定等于整个工程闭环完成。

### `validate_unittest`

它主要检查两件事：

1. 这个 API 的测试有没有覆盖关键调用形态
2. 当前测试代码里提取出来的参数用法，和 `args_list` / `min_input_args` 是否对得上

会卡住你的常见原因：

1. 只写了一个 happy path
2. 没有“全 kwargs”
3. 没有“kwargs out of order”
4. `args_list` 改了，但测试调用形态没跟着变

### `validate_docs`

它不是看代码能不能跑，而是看 PaConvert 配置和文档描述是否一致。

会比对：

1. `paddle_api`
2. `kwargs_change`
3. `args_list`
4. 哪些 API 有 matcher，但 docs 侧没有对应文档

所以你如果改了参数名映射，`validate_docs` 很可能先报，而不是单测先报。

### CI / 脚本

当前仓库里能看到两层：

1. `.github/workflows_origin/` 里有 `tests.yml`、`lint.yml`、`coverage.yml`
2. `scripts/` 和 `docs/CONTRIBUTING.md` 还提到 `modeltest`、`consistency`、`install`、`PRTemplate`

对一个新增 API 来说，最常见的影响是：

1. `tests`：行为回归没过
2. `coverage`：增量覆盖率不够
3. `consistency`：代码样例文本对不上
4. `PRTemplate`：PR 描述没按模板写

## 一个比较稳的修改顺序

1. 先在 `api_mapping.json` 旁边找同类 API，看有没有现成 matcher 可复用
2. 改 mapping 或新增 matcher
3. 立刻补 `tests/test_<api>.py`
4. 本地先跑这个单测文件
5. 再跑 `tools/validate_unittest/validate_unittest.py -r tests/test_<api>.py`
6. 如果改动触及参数名 / 签名，再看 `validate_docs` 会不会受影响
7. 如果你改的是源码级输出形态，再补 `tests/code_library/code_case/`

## 最小改动清单

如果你要支持一个“普通难度”的 API，通常最小闭环会落在这些地方：

1. `paconvert/api_mapping.json`
2. `paconvert/api_matcher.py`
   - 只有现成 matcher 不够用时才改
3. `tests/test_<api>.py`
4. 必要时补 `tests/code_library/code_case/` 样例
5. 如果文档侧也要对齐，再准备 `docs_mappings.json` 对应的文档改动

如果你已经开始动下面这些文件，先停一下想想是不是必要：

1. `paconvert/transformer/basic_transformer.py`
2. `paconvert/transformer/import_transformer.py`
3. `paconvert/base.py`

因为一旦动到这里，通常说明你不是在“加一条 mapping”，而是在改识别框架本身。
