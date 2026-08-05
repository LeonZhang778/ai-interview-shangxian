from datetime import datetime
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile
from xml.etree import ElementTree as ET

from app.services.client.document_export_service import document_export_service


WORD_TEXT = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"


def extract_docx_text(content: bytes) -> str:
    with ZipFile(BytesIO(content)) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    return "\n".join(node.text or "" for node in root.iter(WORD_TEXT))


def make_note(**overrides):
    data = {
        "id": 7,
        "title": "Redis 复盘",
        "content": "# 背景\n- 缓存穿透\n> 需要补充案例",
        "note_type": "review",
        "visibility": "private",
        "status": "draft",
        "tags": "Redis,缓存",
        "source": "interview",
        "summary": "一次后端面试复盘",
        "key_points": '["掌握缓存策略", "补充限流案例"]',
        "updated_at": datetime(2026, 8, 1, 12, 30),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_build_note_docx_contains_note_metadata_and_markdown_content():
    content = document_export_service.build_note_docx(make_note(), "后端复盘")
    text = extract_docx_text(content)

    assert "Redis 复盘" in text
    assert "后端复盘" in text
    assert "一次后端面试复盘" in text
    assert "掌握缓存策略" in text
    assert "缓存穿透" in text
    assert "需要补充案例" in text


def test_build_interview_report_docx_contains_report_sections():
    interview = SimpleNamespace(
        id=12,
        target_position="后端开发",
        difficulty="hard",
        total_questions=3,
        overall_score=8.5,
        status="completed",
        created_at=datetime(2026, 8, 2, 9, 0),
    )
    report = {
        "summary": "整体表现稳定",
        "strengths": ["表达清晰"],
        "weaknesses": ["系统设计深度不足"],
        "suggestions": ["补充高并发案例"],
        "hire_recommendation": "建议录用",
        "dimension_scores": {"沟通表达": 8},
        "question_scores": [
            {"question": "Redis 如何做缓存淘汰？", "score": 8, "feedback": "回答完整"},
        ],
    }

    content = document_export_service.build_interview_report_docx(interview, report)
    text = extract_docx_text(content)

    assert "后端开发 面试报告" in text
    assert "8.5/10" in text
    assert "建议录用" in text
    assert "表达清晰" in text
    assert "系统设计深度不足" in text
    assert "Redis 如何做缓存淘汰？" in text


def test_build_notes_docx_zip_groups_notes_by_notebook():
    note = make_note(title="Redis/缓存 复盘")
    content = document_export_service.build_notes_docx_zip([(note, "后端/复盘")])

    with ZipFile(BytesIO(content)) as archive:
        names = archive.namelist()
        assert names == ["后端复盘/Redis缓存 复盘_7.docx"]
        text = extract_docx_text(archive.read(names[0]))

    assert "Redis/缓存 复盘" in text
    assert "后端/复盘" in text


def test_build_notes_docx_zip_rejects_dot_path_parts():
    note = make_note(title="..")
    content = document_export_service.build_notes_docx_zip([(note, ".")])

    with ZipFile(BytesIO(content)) as archive:
        assert archive.namelist() == ["未分类/note_7_7.docx"]
