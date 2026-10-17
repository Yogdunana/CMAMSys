# MMP-AIR 参考实现（Python）

把一份 MMP-AIR v0.1 记录渲染成赛事要求的披露文件。

## 安装

```bash
pip install -r requirements.txt
```

只依赖 `reportlab`。中文字体使用 reportlab 自带的 CID 字体，
不需要额外下载字体文件。

## 用法

```bash
python render.py <记录.json> [-o 输出目录] [--filename 文件名] [--write-hash] [--strict]
```

| 参数 | 说明 |
| --- | --- |
| `<记录.json>` | 必填，MMP-AIR v0.1 记录文件路径 |
| `-o` | 输出目录，默认当前目录 |
| `--filename` | 输出文件名。默认为规定要求的那个文件名，一般不要改 |
| `--write-hash` | 把计算出的哈希写回记录文件的 `integrity.hash` |
| `--strict` | 记录不完整时直接失败退出，而不是照常生成 |

## 输出

1. **PDF 文件**：包含论文内声明句、工具清单、使用目的与环节、
   提示方式与使用过程（含交互示例）、采纳修改与核验情况，以及记录摘要。
2. **终端输出**：论文内应填的声明句，直接复制到参考文献之前即可。

## 校验

`render.py` 内置的检查项：

- `spec` / `version` 是否正确；
- `declaration.used` 为 false 时 `tools` 与 `records` 必须为空；
- 声明使用时 `tools` 与 `records` 不能为空；
- 每条记录的必填字段是否齐全；
- `tool_refs` 是否指向存在的工具；
- `adopted = modified` 时必须填写 `modification_zh`；
- 非语言润色的记录必须填写核验方式与核验状态。

这些是**最小校验**，不替代 `spec/schema/mmp-air-v0.1.json` 的 JSON Schema 校验。

## 设计取舍

- **不联网**。纯本地渲染，比赛期间离线可用。
- **不内置任何模型调用**。本工具只负责"记录并生成"，不负责采集。
- **不隐藏字段**。所有输入都出现在输出的某个章节里 —— 披露文件本来的用途就是给人看。
- **哈希可选**。`integrity` 不填也能正常生成，填了才会输出摘要。
