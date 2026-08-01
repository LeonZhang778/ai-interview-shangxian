"""笔记模板定义与服务。

提供 4 种预设模板：面试复盘、错题分析、面经整理、知识笔记。
新建笔记时前端可选择模板，快速填充 Markdown 骨架。
"""

from typing import Dict, List, Optional


class NoteTemplate:
    """笔记模板定义"""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        icon: str,
        note_type: str,
        markdown: str,
    ):
        self.id = id
        self.name = name
        self.description = description
        self.icon = icon
        self.note_type = note_type
        self.markdown = markdown


# ==================== 模板定义 ====================

TEMPLATES: Dict[str, NoteTemplate] = {
    "interview-review": NoteTemplate(
        id="interview-review",
        name="面试复盘",
        description="结构化复盘一场 AI 模拟面试",
        icon="🎯",
        note_type="review",
        markdown="""# {岗位} 面试复盘

## 基本信息
- **面试岗位：** {岗位}
- **面试难度：**
- **题目数量：**
- **面试时间：** {date}

## 总体评价

> 写一段总结性评价，面试整体表现如何。

## 得分情况

| 题目 | 得分 | 知识点 |
|------|------|--------|
| 1 | /10 | |
| 2 | /10 | |
| 3 | /10 | |

## 亮点

- 哪些题目回答得比较好？
- 思路清晰在哪里？

## 薄弱点

- 哪些题目回答不理想？
- 原因是什么？

## 改进计划

- [ ] 复习知识点：...
- [ ] 练习同类题目：...
- [ ] 3 天后再次面试模拟
""",
    ),
    "mistake-analysis": NoteTemplate(
        id="mistake-analysis",
        name="错题分析",
        description="分析一道面试错题，找出薄弱点",
        icon="❌",
        note_type="mistake",
        markdown="""# {题目名称} — 错题分析

## 题目信息
- **题目：**
- **知识点：**
- **来源：** 面试 / 面经

## 我的回答

```
在这里粘贴你的回答
```

## AI 评语 / 参考答案

```
在这里粘贴参考答案或 AI 反馈
```

## 错误原因分析

- [ ] 知识点不熟悉
- [ ] 思路不清晰
- [ ] 紧张导致失误
- [ ] 没有理解题目

## 正确解法

用 Markdown 或代码块写出正确解法。

## 同类题练习

- [ ] 相关题目 1
- [ ] 相关题目 2
""",
    ),
    "experience-notes": NoteTemplate(
        id="experience-notes",
        name="面经整理",
        description="整理真实面经的核心知识点",
        icon="📚",
        note_type="experience",
        markdown="""# {公司} {岗位} 面经整理

## 信息来源
- **公司：** {公司}
- **岗位：** {岗位}
- **来源：** 面经广场 / 网友分享

## 面试流程

1. 自我介绍
2. 技术面
3. 项目深挖
4. 算法题
5. 反问环节

## 重点题目

### 1. {题目1}

**考察点：**

**思路：**

**答案要点：**

### 2. {题目2}

...

## 知识点总结

### 需要掌握

- [ ] 知识点 1
- [ ] 知识点 2

### 需要深入

- [ ] 深入知识点 1
""",
    ),
    "knowledge-note": NoteTemplate(
        id="knowledge-note",
        name="知识笔记",
        description="系统性记录一个技术知识点",
        icon="📝",
        note_type="note",
        markdown="""# {知识点名称}

## 概述

一句话说明这个知识点是什么。

## 核心概念

### 概念 1

- 定义：
- 特点：
- 应用场景：

### 概念 2

...

## 代码示例

```python
# 示例代码
```

## 面试常见问题

1. **Q：** 常见问题 1
   **A：** 答案要点

2. **Q：** 常见问题 2
   **A：** 答案要点

## 参考资源

- [链接 1]()
- [链接 2]()
""",
    ),
}


def get_templates() -> List[Dict]:
    """获取所有模板列表（不含正文，用于前端选择器）"""
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "icon": t.icon,
            "note_type": t.note_type,
        }
        for t in TEMPLATES.values()
    ]


def get_template(template_id: str) -> Optional[NoteTemplate]:
    """获取单个模板"""
    return TEMPLATES.get(template_id)