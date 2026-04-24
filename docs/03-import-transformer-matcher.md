# 03. import、transformer、matcher 的边界

`ImportTransformer` 准备名字。`from torch.nn import functional as F` 进来后，调用点只剩 `F.relu(...)`；`ImportTransformer` 把 `F` 和 `torch.nn.functional` 的关系记进 `imports_map[file]`，后面才能恢复出 `torch.nn.functional.relu`。

`BaseTransformer.get_full_api_from_node()` 做补全，`GlobalManager.ALIAS_MAPPING` 再做 alias 归一。`torch.absolute` 这类名字会先归到 `torch.abs`，再查 `paconvert/api_mapping.json`。

`ImportTransformer` 还会区分 `torch_packages`、`may_torch_packages`、`other_packages`。`tests/code_library/code_case/torch_code/import_analysis.py` 适合拿来对照：相对导入、本地模块、torch 生态前缀混在同一个文件里，正好能看出它为什么不能只按字符串前缀判断。

`BasicTransformer` 接在 `ImportTransformer` 后面。它遍历 AST 时判断当前节点是包级调用、类方法还是属性访问，再查 `paconvert/api_mapping.json`、`paconvert/attribute_mapping.json` 或 wildcard mapping。它决定交给哪个 matcher，不负责手写每条 API 的目标代码。

包级调用看 `visit_Call()` 里的完整 API 名，类方法还要结合对象类型推断，属性访问会走另一套 mapping。`torch.add(...)` 和 `x.add(...)` 的名字很像，分发路径不同。

matcher 接到的是 canonical API、mapping 配置、当前 AST 上下文。`ChangePrefixMatcher` 这种只换前缀，`GenericMatcher` 会走 `BaseMatcher.parse_args_and_kwargs()`、`change_kwargs()`、`set_paddle_default_kwargs()`。需要多行代码、临时变量、helper 函数时，matcher 会生成多节点结果，再由 transformer 插回当前作用域。

matcher 产物最终还是 AST 片段，不是直接落盘的字符串。helper 也只是先登记，目录模式下由 `UtilsFileHelper` 写到 `paddle_utils.py`，单文件模式插回输出文件。

`args_list` 是 `GenericMatcher` 的关键字段。`torch.optim.SGD(conv.parameters(), 0.5)` 先按 `args_list` 变成 `params`、`lr`，再按 `kwargs_change` 变成 `parameters`、`learning_rate`。`args_list` 里的 `"*"` 表示后面的参数必须用 keyword 形式出现。

默认顺序是 `ImportTransformer -> BasicTransformer -> matcher`。`mark_unsupport()` 不在这条边界里，它在 AST 回写成源码后统一打 `>>>>>>`。

改普通 API 时，优先动 `paconvert/api_mapping.json` 和 `tests/test_<api>.py`。只有 canonical API 恢复失败、类方法识别错、属性访问分支错，才回到 `import_transformer.py` 或 `basic_transformer.py`。
