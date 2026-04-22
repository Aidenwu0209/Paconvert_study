# 08. 已知限制和容易误判的点

这一篇不讲“应该怎么设计”，只讲“你读源码或看输出时，哪些现象别先下结论”。

## 为什么第三方库封装的 torch API 不一定能自动转

PaConvert 识别的是当前文件 AST 里能还原成 torch 生态前缀的调用。

它比较擅长的情况是：

1. `torch.xxx`
2. `nn.xxx`
3. `F.xxx`
4. `torchvision.xxx`
5. `mmcv.xxx`
6. 其他在 `GlobalManager.TORCH_PACKAGE_MAPPING` 里显式列出来的包前缀

它不擅长的情况是：

1. 你项目自己封了一层 `my_add()`，里面再调用 `torch.add()`
2. 第三方库内部帮你调了 torch，但当前文件里只看到一个普通函数名
3. import 名字根本不在 `TORCH_PACKAGE_MAPPING` / `MAY_TORCH_PACKAGE_LIST` 里

这不是简单的 bug，更像能力边界。  
它看的是 AST 节点和 import 前缀，不会跨包做静态分析。

## 为什么转换后代码风格可能变化

因为当前输出链路就是：

1. `astor.to_source()`
2. `black`
3. `isort`

这会直接带来这些结果：

1. import 顺序变了
2. 空行变了
3. 长调用被拆行了
4. 一些括号风格变了

这不是额外 formatter 插件“多管闲事”，而是 `Converter.transfer_file()` 的默认行为。

## 为什么注释可能消失

因为 Python AST 本身不保留普通注释，回写又走的是 `astor.to_source()`。

所以：

1. 行注释基本会丢
2. 原始排版里的很多细节也不会保留
3. 文档字符串能保留，是因为它们本身是字符串字面量节点

如果你在 diff 里看到“逻辑没怎么变，但注释没了”，先别怀疑 matcher。

## 为什么有些代码会多出几行

常见来源有 4 种：

1. matcher 需要多句组合实现一个 API
2. matcher 需要插入临时变量
3. matcher 需要 helper 函数，于是触发 `paddle_utils.py`
4. 不支持自动转换时，transformer 会先插入提示节点，后面再由 `mark_unsupport()` 把业务代码那一行打上 `>>>>>>`

所以“多出几行”不一定代表规则错了，有时只是实现方式本来就不是一对一替换。

## `>>>>>>` 标记代表什么

它不是 matcher 直接拼进去的文本，而是 `Converter.mark_unsupport()` 在源码输出最后一层加上的。

它主要有两种触发来源：

1. `BasicTransformer` / `CustomOpTransformer` 先插入一条 `'Not Support auto convert ...'` 提示语句
2. `mark_unsupport()` 再把后面的真实业务代码行前面加上 `>>>>>>`

还有一个细节值得知道：  
`mark_unsupport()` 会先尽量把字符串字面量剔掉，再判断有没有残留 `torch.` 前缀，所以不会把普通文案字符串里的 `torch` 全都误标红。

## 哪些地方最容易误以为“这是 bug”，但其实更像设计取舍

### 1. Convert Rate 不是按文件算

它按识别到的 API 次数算。

所以一个文件里有两个 `torch.tensor` 和一个 `torch.add`，summary 看到的就是 3 个 API，不是 1 个文件。

### 2. `torch.add` 和 `x.add` 不是同一条规则

名字很像，但一个是包级函数，一个是类方法。  
前者当前走 `ChangePrefixMatcher`，后者会走类方法分支和别的 matcher。

### 3. `tensor_requires_grad_transformer.py` 存在，不等于默认一定会跑

当前默认 transformer 链里没有它。  
这是源码能直接确认的事实，不该写成“应该会走但可能失效”。

### 4. 只有 `requirements.txt` 被特殊处理

当前代码只对文件名以 `requirements.txt` 结尾的文件做简单替换。  
别的配置文件、YAML、shell、TOML 都是按原样复制。

### 5. visible GitHub workflow 不等于全部维护检查

`.github/workflows_origin/` 里现在只看得到 `tests`、`lint`、`coverage` 三个 workflow。  
但 `scripts/` 和 `docs/CONTRIBUTING.md` 还提到 `modeltest`、`consistency`、`install`、`PRTemplate` 等脚本。

如果你只看 `.github/workflows_origin/`，会误以为仓库检查面比实际窄。

### 6. “不支持”通常是显式保留，不是偷偷降级

像 `torch.optim.SGD` 带 `momentum`、`dampening` 这些参数时，当前实现不是静默丢参，而是保留原调用并打 `>>>>>>`。

这比“假装支持，实际语义偷偷变了”更保守。

## 还有两个我选择明确标出来的地方

### `paconvert` 和 `PaConvert` 目录名

这次本地读取时同时存在：

1. `./PaConvert`
2. `./paconvert`

而且我实际比对过，两者当前内容一致。  
但打包入口用的是小写 `paconvert.main:main`，所以正文统一用小写路径。

### `TensorRequiresGradTransformer` 为什么没接进默认链路

这件事当前源码里能看到结果，看不到决策原因。  
我在别处都只写了“默认链路没有启用它”，没有继续猜“为什么后来废弃”。
