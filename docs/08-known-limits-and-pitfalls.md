# 08. 已知限制和容易误判的点

这页只收读源码和看输出时最容易误判成 bug 的现象。每一条都尽量落到“你会看到什么，为什么会这样”。

## 看到你自己封装的函数没改，不一定是漏转

常见现象是：当前文件里只写了 `my_add(x, y)`，而 `my_add()` 的实现藏在别的模块里，里面再去调 `torch.add()`。这种情况下，PaConvert 往往不会自动把 `my_add()` 也识别成待转换 API。

原因不在 matcher，而在识别边界。当前主流程主要看“当前文件 AST 里能不能恢复出 torch 生态前缀”，不会跨包做更深的静态分析。所以 `torch.xxx`、`nn.xxx`、`F.xxx` 这类直接写在当前文件里的调用比较稳；项目自己再封一层，自动识别的把握就会明显下降。

## 看到 import 顺序、空行、拆行都变了，不是 formatter 失控

常见现象是：转换后逻辑没什么变化，但 import 顺序重排了，长调用被拆行了，空行位置也和原文件不同。

这来自固定输出链：`astor.to_source()` 先把 AST 回写成源码，后面默认还会接 `black` 和 `isort`。所以代码风格变化不是额外插件“多管闲事”，而是 `Converter.transfer_file()` 的默认行为。

## 看到注释没了，先别怀疑 matcher

最典型的现象是：业务调用都改对了，但行注释不见了，原来手工排版的细节也保不住。

原因很直接：Python AST 不保留普通注释，回写又走的是 `astor.to_source()`。文档字符串还能留下，是因为它本来就是字符串字面量节点；普通注释则没有这层待遇。

## 看到输出多了几行，或者多了 `paddle_utils.py`，先看是不是设计使然

这类现象通常有三种来源。第一种是 matcher 本来就需要多句代码才能表达一个 API；第二种是 matcher 引入了临时变量；第三种是 matcher 通过 `BaseMatcher.enable_utils_code()` 登记了 helper，于是任务结束后由 `UtilsFileHelper.write_code()` 统一落成 `paddle_utils.py` 或插回当前文件。

所以“多出几行”不自动等于规则错了。很多时候只是目标 API 没法一对一替换，当前设计选择了更显式的展开方式。

## 看到 `>>>>>>`，它表示这段调用被保守地留了下来

`>>>>>>` 不是 matcher 当场拼进去的文本，而是 `Converter.mark_unsupport()` 在源码输出最后一层统一加上的。通常是前面某个 transformer 或 matcher 已经判断这段调用不该自动改，先插入一条 `'Not Support auto convert ...'` 提示语句，最后再由 `mark_unsupport()` 给真实业务代码那一行打标。

所以看到 `>>>>>>` 时，更接近的理解是“这段调用被显式保留，等人手工接管”，而不是“系统半改半没改，状态不明”。

## summary 数字比你预想的大，通常只是统计口径不同

最常见的误会是拿文件数去对照 `convert_rate`。实际上 summary 统计的是识别到的 torch API 次数，不是文件数。

比如 `examples/simple_add/input_torch.py` 里除了 `torch.add(...)`，还有两个 `torch.tensor(...)`。所以同一个小文件，summary 看到的是 3 个 API，而不是 1 个文件。

## 名字很像的 API，不一定走同一条规则

`torch.add(...)` 和 `x.add(...)` 很容易被看成一回事，但在当前仓库里它们不是同一条链路。前者是包级函数，当前走 `ChangePrefixMatcher`；后者是类方法，会走 `BasicTransformer` 的类方法分支，再命中别的 matcher。

所以如果你只凭 API 名字搜一圈就下结论，很容易把“规则不一致”误判成 bug。先确认它到底是包级调用、类方法还是属性访问。

## 文件存在，不等于默认一定会参与主流程

`paconvert/transformer/tensor_requires_grad_transformer.py` 就是最典型的例子。它的职责很明确，专门处理 `tensor.requires_grad = ...` 左值赋值；但当前 `Converter.transfer_node()` 默认并没有把它接进 transformer 链。

这件事源码能直接确认，所以读代码时别把“仓库里有这个文件”自动理解成“这次转换一定会跑到它”。

## 只有 `requirements.txt` 被特殊处理，别的配置文件不会顺手跟着改

你可能会看到这样的现象：Python 源码里的 `torch` 调用已经改了，但 `pyproject.toml`、`setup.cfg`、YAML、shell 脚本里的依赖声明原封不动。

这不是漏掉了某个 formatter。当前代码只对文件名以 `requirements.txt` 结尾的文件做简单替换，其他非 Python 文件基本就是原样复制。

## 可见的 GitHub workflow，比实际维护检查少

如果你只看 `.github/workflows_origin/`，当前能直接看到的是 `tests.yml`、`lint.yml`、`coverage.yml`。但 `scripts/` 和 `docs/CONTRIBUTING.md` 里还能找到 `modeltest`、`consistency`、`install`、`PRTemplate` 这些检查项。

所以“仓库里只挂了三条 workflow”不等于维护流程里真的只做这三类检查。读 CI 相关代码时，最好把 `.github/` 和 `scripts/` 放在一起看。

## 这两个点我选择继续明确标 `不确定`

当前工作区同时存在 `./PaConvert` 和 `./paconvert`，而且内容一致；但打包入口写的是 `paconvert.main:main`，所以正文统一用小写路径。这个结论能确认，至于历史上为什么会同时保留两套目录名，现有文件给不出答案。

`TensorRequiresGradTransformer` 为什么没接进默认链路也一样。源码能确认“现在没接”，不能只靠现有仓库文件确认“后来为什么不用它”。
