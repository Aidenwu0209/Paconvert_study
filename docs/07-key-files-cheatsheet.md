# 07. 核心文件速查

## 主链路

| 文件路径 | 主要职责 | 上游 | 下游 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `setup.py` | 注册 CLI | shell / pip | `paconvert.main:main` | A | console script |
| `paconvert/main.py` | 解析参数 | CLI | `Converter.run()` | A | 不做 AST |
| `paconvert/converter.py` | 调度任务 | `main()` | transformer / output | A | 主链入口 |
| `paconvert/transformer/import_transformer.py` | 恢复 import | `transfer_node()` | `imports_map` | A | 先于 matcher |
| `paconvert/transformer/basic_transformer.py` | 识别并分发 API | `ImportTransformer` | matcher | A | 普通 API 主入口 |

## 规则与公共能力

| 文件路径 | 主要职责 | 上游 | 下游 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `paconvert/global_var.py` | 加载全局映射 | JSON 配置 | transformer / matcher | A | 包名前缀 |
| `paconvert/base.py` | 公共基类 | transformer / matcher | 参数归一化 / 插入节点 | A | 看 `BaseMatcher` |
| `paconvert/api_mapping.json` | API 规则 | `GlobalManager` | `get_api_matcher()` | A | 新增 API 先看 |
| `paconvert/api_matcher.py` | 生成目标代码 | `BasicTransformer` | AST 节点 / helper | A | 带 API 搜 |

## 测试与校验

| 文件路径 | 主要职责 | 上游 | 下游 | 优先级 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `tests/apibase.py` | 单测基座 | `tests/test_*.py` | `Converter` | A | 真实转换 |
| `tests/test_add.py` | 简单 API 样板 | `APIBase` | `torch.add` | A | `ChangePrefixMatcher` |
| `tests/test_optim_SGD.py` | 参数改写样板 | `APIBase` | `torch.optim.SGD` | A | `GenericMatcher` |
| `tools/validate_unittest/validate_unittest.py` | 检查测试形态 | `tests/test_*.py` | report | A | pytest 外一层 |
