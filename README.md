# CMAMSys

**CompetiMath AutoModel System** —— 数学建模竞赛全流程协作系统。

本仓库同时承担两件事：

1. 承载 **MMP-AIR** 这份公开的 AI 使用披露格式规范（[SPEC.md](SPEC.md)）；
2. 提供该规范的**参考实现**（[reference/python](reference/python)）。

---

## 为什么要做这个

2026 年 8 月，全国大学生数学建模竞赛发布《人工智能工具使用规定（2026 年试行）》，
自 2026 年 9 月 1 日起施行。规定要求：

- 论文参考文献之前设置"AI工具使用声明"；
- 使用过 AI 的作品，支撑材料中必须包含 **PDF 格式的详情说明**，
  内容涵盖**工具名称与版本、使用目的与环节、提示方式与使用过程、采纳修改与核验情况**四项；
- 未如实披露的，取消评奖资格。

**规定给出了义务，没有给出格式。** 目前每一支参赛队都是手写一份 PDF。

MMP-AIR 就是为填补这个空缺而写的：一份最小的、机器可读的记录格式，
四项要求逐条对应，可由工具自动生成符合规定的披露文件。

完整对照表见 [docs/cumcm-2026-mapping.md](docs/cumcm-2026-mapping.md)。

---

## 快速开始

```bash
pip install -r reference/python/requirements.txt

python reference/python/render.py examples/typical.json -o out/
```

输出：

- `out/AI工具使用详情.pdf` —— 符合规定四项要求的披露文件；
- 终端打印论文内应填的声明句（置于参考文献之前）。

不希望被占位数据误导，可以先从自己的记录开始：

```bash
cp examples/typical.json my-record.json
# 按 SPEC.md 改写
python reference/python/render.py my-record.json -o out/ --strict
```

`--strict` 会在记录不完整时直接报错退出，而不是照常生成。

---

## 仓库结构

```
SPEC.md                        规范正文（MMP-AIR v0.1）
spec/schema/mmp-air-v0.1.json  JSON Schema（Draft 2020-12）
spec/LICENSE                   规范的许可：CC BY 4.0
examples/                      两份示例记录与生成结果
reference/python/              参考实现：记录 → 披露文件
docs/                          与赛事规定的逐条对照
LICENSE                        参考实现的许可：Apache-2.0
```

---

## 许可

三层分开，这是刻意的：

| 内容 | 许可 | 说明 |
| --- | --- | --- |
| 规范（SPEC.md 及 schema） | **CC BY 4.0** | 任何人可自由实现、再发布，需保留署名 |
| 参考实现（reference/） | **Apache-2.0** | 含明示专利许可，便于被采纳 |
| CMAMSys 完整产品 | 不在本仓库 | 商业部分，独立授权 |

**许可不转让著作权。** 规范与实现的著作权归作者所有，开放的是"格式"本身 ——
任何人在遵守许可条款的前提下，都可以实现、生成和解析 MMP-AIR 文件。

可以自由地：使用本规范、实现本规范、在自己的软件中称"支持 MMP-AIR"。
需要留意的是：不得使用本项目名称与标识暗示自己是官方或唯一实现。

---

## 状态

v0.1 是草案，随赛事规定的修订同步演进。规范文本与参考实现均在本仓库维护，
版本变化记录见 SPEC.md 第 4 节。

---

## 作者

段茗尧（Yogdunana） · 深圳北理莫斯科大学计算机协会
GitHub: https://github.com/Yogdunana
