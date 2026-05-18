# output_layout.json — 排版布局规范

文档所有视觉格式的**唯一数据源**。`tools.py` 的 `_layout_css()` 从此生成打印 CSS，`workflow.py` 的提示词引用其中的规则。修改此文件即修改全局排版，无需改动代码或提示词。

## 配置节一览

```
output_layout.json
├── page_setup          # 纸张 + 页边距
├── font                # 字体栈
├── headings            # 5 级标题样式
│   └── levels[]        # 每级: html_tag, markdown_prefix, numbering_*, font_size, ...
├── body_text           # 正文段落
├── document_title      # 文档总标题 (项目名前缀 + 文档名)
├── document_meta       # 元数据模板 (fields 数组)
├── figures             # 图标题格式、编号
├── tables              # 表标题格式、编号、单元格样式
├── code_blocks         # 代码块样式
├── lists               # 列表样式 + 无序列表开关
├── page_breaks         # 分页规则
├── pdf_rendering       # PDF 渲染细节（图片、页脚、表格间距等）
├── rendering_conventions  # 渲染习惯 (LLM 参考)
└── boilerplate_rules   # 禁止的 LLM 客套话
```

---

## page_setup

```json
{
  "paper_size": "A4",
  "margin_top": "2.54cm",
  "margin_bottom": "2.54cm",
  "margin_left": "3.17cm",
  "margin_right": "3.17cm"
}
```

生成 `@page { size: A4; margin-* }`。

---

## font

| 字段 | 值 | 用途 |
|------|-----|------|
| `body_font` | SimSun | 正文 (宋体) |
| `body_font_fallback` | Times New Roman | 正文 fallback |
| `title_font` | SimHei | 标题 (黑体) |
| `title_font_fallback` | Arial | 标题 fallback |
| `mono_font` | Consolas | 代码 |
| `mono_font_fallback` | Courier New | 代码 fallback |
| `body_size` | 10.5pt | 正文 = 五号 |

---

## headings

`global` 定义所有标题的默认对齐 (`left`)、缩进 (`0`)、段前距 (`1.5em`)、段后距 (`0.8em`)。

`levels[]` 定义 5 级标题:

| level | tag | prefix | style | format | font | 说明 |
|-------|-----|--------|-------|--------|------|------|
| 1 | h1 | `#` | none | — | 26pt/center | 文档总标题 |
| 2 | h2 | `##` | chinese_upper | `{number}、{title}` | 22pt | 一、引言 |
| 3 | h3 | `###` | decimal_dot | `{number} {title}` | 18pt | 1.1 目的 |
| 4 | h4 | `####` | decimal_dot | `{number} {title}` | 16pt | 1.1.1 范围 |
| 5 | h5 | `#####` | parentheses_decimal | `({number}) {title}` | 14pt | (1) 子项 |

level 5 支持两种编号风格:
- 默认 `parentheses_decimal`: `(1)` `(2)` `(3)`
- 备选 `decimal_dot_4`: `3.1.1.2` (四段十进制，由 `numbering_style_alt` / `numbering_format_alt` 定义)

---

## body_text

```json
{
  "alignment": "justified",
  "first_line_indent": "2em",
  "line_spacing": "1.25"
}
```

生成 `p { text-align: justified; text-indent: 2em; line-height: 1.25 }`。

---

## document_title

```json
{
  "prefix": "DRG入组智能体系统",
  "font_size": "22pt",
  "alignment": "center"
}
```

标题页呈现: `{prefix}{文档标题}` (如 "DRG入组智能体系统需求规格说明书")。

---

## document_meta

模板化元数据，`_extract_doc_info()` 和 `_format_title_html()` 据此提取和格式化:

```json
{
  "fields": [
    {"key": "文档编号", "pattern": "SRS-DRG-AGENT-V{version}", "example": "SRS-DRG-AGENT-V1.0"},
    {"key": "版本号",   "pattern": "V{major}.{minor}",           "example": "V1.0"},
    {"key": "编制日期", "pattern": "{YYYY}年{M}月",               "example": "2026年3月"},
    {"key": "文档状态", "pattern": "正式发布 | 草案 | 已定稿",      "example": "正式发布"}
  ]
}
```

**数据流**:
1. LLM 按 fields 顺序生成 `**{key}：{value}**` 行
2. `_extract_doc_info()` 按 `key` 精确匹配提取
3. `_format_title_html()` 按 `fields` 顺序垂直渲染到标题页

新增字段只需在此数组追加即可，代码自动适配。

---

## figures

```json
{
  "require_caption": true,
  "caption_format": "{prefix}{chapter}-{number}：{caption}",
  "prefix": "图",
  "numbering_scope": "per_chapter",
  "caption_position": "below",
  "font_size": "10pt"
}
```

- `numbering_scope: per_chapter` — 每章从 1 开始: `图1-1`, `图2-1`, ...
- 图编号 = `{一级章节序号}-{章节内图片序号}`
- 图和表在各章内独立计数的

---

## tables

```json
{
  "require_caption": true,
  "caption_format": "{prefix}{chapter}-{number}：{caption}",
  "prefix": "表",
  "numbering_scope": "per_chapter",
  "caption_position": "above"
}
```

表格 CSS:
- `th/td`: `text-align: center; vertical-align: middle`
- `td.cell-text`: `text-align: justify; text-indent: 2em` (大段文字时使用)

---

## lists

```json
{
  "allow_unordered": false,
  "ordered_style": "decimal",
  "indent": "2em"
}
```

- `allow_unordered: false` — LLM 禁止 `- * ·` 无序列表，只用 `(1)(2)` 或分段
- 设为 `true` 则恢复无序列表支持

---

## page_breaks

```json
{
  "enabled": true,
  "exclude_first_h2": true
}
```

生成 CSS:
```css
h2 { page-break-before: always; }
h2:first-of-type { page-break-before: avoid; }
```

---

## rendering_conventions

LLM 渲染习惯参考: `auto_caption`、`diagram_placement`、`note_file_for_omissions`。图表编号范围以 `figures.numbering_scope` 和 `tables.numbering_scope` 为准。

---

## pdf_rendering

PDF 专用渲染细节，如标题页高度、图片最大高度、表格外边距、页眉页脚模板等。`tools.py` 不再直接硬编码这些值，而是从该配置节读取。

---

## boilerplate_rules

```json
{
  "forbidden_patterns": [
    "好的,我这就为您生成...",
    "以下是为您生成的...",
    "以上内容由AI生成仅供参考",
    "本文档由AI生成"
  ]
}
```

`_clean_boilerplate()` 在 PDF 转换时正则剔除这些模式。
