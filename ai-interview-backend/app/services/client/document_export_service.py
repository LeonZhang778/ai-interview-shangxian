import io
import json
import re
import zipfile
from typing import Sequence

from docx import Document

from app.models.interview import Interview
from app.models.learning_note import LearningNote
from app.utils.utils import safe_parse_json


DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class DocumentExportService:
    """生成 AI-Interview 可下载的 DOCX / ZIP 内容。"""

    NOTE_TYPE_LABELS = {
        "note": "笔记",
        "review": "复盘",
        "mistake": "错题",
        "experience": "面经",
        "material": "资料",
    }

    STATUS_LABELS = {
        "draft": "草稿",
        "published": "已发布",
    }

    VISIBILITY_LABELS = {
        "private": "仅自己",
        "public": "公开",
    }

    DIFFICULTY_LABELS = {
        "easy": "简单",
        "medium": "中等",
        "hard": "困难",
    }

    @staticmethod
    def _clean_text(value: str) -> str:
        text = value or ""
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"\1", text)
        text = re.sub(r"_(.+?)_", r"\1", text)
        return text.strip()

    @classmethod
    def _safe_path_part(cls, value: str | None, fallback: str) -> str:
        cleaned = "".join(
            char for char in cls._clean_text(value or "")
            if char not in '\\/:*?"<>|' and ord(char) >= 32 and ord(char) != 127
        ).strip().strip(" .")
        return cleaned or fallback

    @staticmethod
    def _stringify(value, fallback: str = "N/A") -> str:
        if value is None or value == "":
            return fallback
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @staticmethod
    def _format_dt(value) -> str:
        if not value:
            return "N/A"
        try:
            return value.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return str(value)

    @staticmethod
    def _add_kv_table(document: Document, rows: list[tuple[str, str]]) -> None:
        if not rows:
            return
        table = document.add_table(rows=0, cols=2)
        table.style = "Table Grid"
        for label, value in rows:
            cells = table.add_row().cells
            cells[0].text = str(label)
            cells[1].text = str(value)
        document.add_paragraph("")

    @staticmethod
    def _add_section(document: Document, title: str) -> None:
        document.add_heading(title, level=1)

    @classmethod
    def _add_bullets(cls, document: Document, items) -> None:
        if not items:
            return
        for item in items:
            text = item
            if isinstance(item, dict):
                text = item.get("title") or item.get("name") or item.get("text") or item
            paragraph = document.add_paragraph(style="List Bullet")
            paragraph.add_run(cls._clean_text(cls._stringify(text, "")))

    @classmethod
    def _add_markdown_body(cls, document: Document, content: str) -> None:
        lines = (content or "").splitlines()
        if not lines:
            document.add_paragraph("暂无正文")
            return

        in_code = False
        code_lines: list[str] = []
        for raw_line in lines:
            line = raw_line.rstrip()
            if line.strip().startswith("```"):
                if in_code:
                    cls._add_code_block(document, code_lines)
                    code_lines = []
                    in_code = False
                else:
                    in_code = True
                continue
            if in_code:
                code_lines.append(raw_line)
                continue

            stripped = line.strip()
            if not stripped:
                document.add_paragraph("")
                continue

            heading = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading:
                level = min(len(heading.group(1)), 3)
                document.add_heading(cls._clean_text(heading.group(2)), level=level)
                continue

            bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
            if bullet:
                paragraph = document.add_paragraph(style="List Bullet")
                paragraph.add_run(cls._clean_text(bullet.group(1)))
                continue

            number = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
            if number:
                paragraph = document.add_paragraph(style="List Number")
                paragraph.add_run(cls._clean_text(number.group(1)))
                continue

            quote = re.match(r"^\s*>\s?(.*)$", line)
            if quote:
                paragraph = document.add_paragraph()
                run = paragraph.add_run(cls._clean_text(quote.group(1)))
                run.italic = True
                continue

            document.add_paragraph(cls._clean_text(line))

        if in_code and code_lines:
            cls._add_code_block(document, code_lines)

    @staticmethod
    def _add_code_block(document: Document, code_lines: list[str]) -> None:
        paragraph = document.add_paragraph()
        run = paragraph.add_run("\n".join(code_lines).rstrip())
        run.font.name = "Consolas"

    @staticmethod
    def _save_document(document: Document) -> bytes:
        buf = io.BytesIO()
        document.save(buf)
        return buf.getvalue()

    @classmethod
    def build_note_docx(cls, note: LearningNote, notebook_name: str | None = None) -> bytes:
        document = Document()
        title = note.title or f"笔记_{note.id}"
        document.add_heading(title, level=0)

        cls._add_kv_table(document, [
            ("笔记本", notebook_name or "未分类"),
            ("类型", cls.NOTE_TYPE_LABELS.get(note.note_type, note.note_type or "未知")),
            ("状态", cls.STATUS_LABELS.get(note.status, note.status or "未知")),
            ("可见性", cls.VISIBILITY_LABELS.get(note.visibility, note.visibility or "未知")),
            ("来源", "面试回流" if note.source == "interview" else "手动创建"),
            ("标签", note.tags or "无"),
            ("更新时间", cls._format_dt(note.updated_at)),
        ])

        if note.summary:
            cls._add_section(document, "摘要")
            document.add_paragraph(note.summary)

        key_points = safe_parse_json(note.key_points, [])
        if isinstance(key_points, list) and key_points:
            cls._add_section(document, "要点")
            cls._add_bullets(document, key_points)

        cls._add_section(document, "正文")
        cls._add_markdown_body(document, note.content or "")
        return cls._save_document(document)

    @classmethod
    def build_interview_report_docx(cls, interview: Interview, report: dict | None) -> bytes:
        document = Document()
        title = f"{interview.target_position or 'AI 面试'} 面试报告"
        document.add_heading(title, level=0)

        cls._add_kv_table(document, [
            ("岗位", interview.target_position or "模拟面试"),
            ("难度", cls.DIFFICULTY_LABELS.get(interview.difficulty, interview.difficulty or "未知")),
            ("总题数", str(interview.total_questions or 0)),
            ("综合得分", f"{float(interview.overall_score) if interview.overall_score else 0}/10"),
            ("状态", "已完成" if interview.status == "completed" else interview.status or "未知"),
            ("创建时间", cls._format_dt(interview.created_at)),
        ])

        report_data = report if isinstance(report, dict) else {}
        recommendation = cls._stringify(report_data.get("hire_recommendation"), "")
        if recommendation:
            cls._add_section(document, "结论")
            paragraph = document.add_paragraph()
            run = paragraph.add_run(recommendation)
            run.bold = True

        for section_title, key in (
            ("总体评价", "summary"),
            ("优势", "strengths"),
            ("不足", "weaknesses"),
            ("改进建议", "suggestions"),
        ):
            value = report_data.get(key)
            if not value:
                continue
            cls._add_section(document, section_title)
            if isinstance(value, list):
                cls._add_bullets(document, value)
            else:
                document.add_paragraph(cls._clean_text(cls._stringify(value, "")))

        dimensions = report_data.get("dimension_scores") or report_data.get("dimension_avg") or {}
        if isinstance(dimensions, dict) and dimensions:
            cls._add_section(document, "维度评分")
            cls._add_kv_table(document, [
                (name, cls._stringify(score))
                for name, score in dimensions.items()
            ])

        question_scores = report_data.get("question_scores") or []
        if isinstance(question_scores, list) and question_scores:
            cls._add_section(document, "逐题得分")
            table = document.add_table(rows=1, cols=4)
            table.style = "Table Grid"
            headers = ["题目", "得分", "评语", "答案"]
            for index, header in enumerate(headers):
                table.rows[0].cells[index].text = header
            for item in question_scores:
                if not isinstance(item, dict):
                    item = {"question": cls._stringify(item, "")}
                cells = table.add_row().cells
                cells[0].text = cls._clean_text(cls._stringify(item.get("question") or f"第{len(table.rows) - 1}题", ""))
                cells[1].text = cls._stringify(item.get("score"), "0")
                cells[2].text = cls._clean_text(cls._stringify(item.get("feedback"), ""))
                cells[3].text = cls._clean_text(cls._stringify(item.get("answer"), ""))

        return cls._save_document(document)

    @classmethod
    def build_notes_docx_zip(
        cls,
        note_rows: Sequence[tuple[LearningNote, str | None]],
    ) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
            used_paths: set[str] = set()
            for note, notebook_name in note_rows:
                folder = cls._safe_path_part(notebook_name, "未分类")
                title = cls._safe_path_part(note.title, f"note_{note.id}")
                path = f"{folder}/{title}_{note.id}.docx"
                suffix = 1
                while path in used_paths:
                    path = f"{folder}/{title}_{note.id}_{suffix}.docx"
                    suffix += 1
                used_paths.add(path)
                archive.writestr(path, cls.build_note_docx(note, notebook_name))
        return buf.getvalue()


document_export_service = DocumentExportService()
