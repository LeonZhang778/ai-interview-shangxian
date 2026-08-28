import asyncio
from types import SimpleNamespace

from docx import Document

from app.models.resume import Resume
from app.services.client import resume_service as resume_module
from app.services.client.resume_service import ResumeService


class FakeDb:
    def __init__(self, resume=None):
        self.resume = resume
        self.added = None
        self.commits = 0

    def add(self, obj):
        self.added = obj
        obj.id = 42
        self.resume = obj

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        return None

    async def execute(self, query):
        return SimpleNamespace(scalar_one_or_none=lambda: self.resume)


def test_upload_and_parse_creates_resume_and_enqueues_task(tmp_path, monkeypatch):
    calls = []

    monkeypatch.setattr(resume_module, "UPLOAD_DIR", str(tmp_path))

    from app.schedule.jobs import resume_tasks
    monkeypatch.setattr(resume_tasks.parse_resume_task, "delay", lambda *args: calls.append(args))

    db = FakeDb()
    result = asyncio.run(ResumeService.upload_and_parse(
        db=db,
        user_id=7,
        file_content=b"%PDF-1.4",
        file_name="resume.pdf",
        target_position="后端开发",
    ))

    assert result["resume_id"] == 42
    assert result["status"] == "parsing"
    assert calls == [(42, 7)]
    assert db.resume.file_name == "resume.pdf"
    assert db.resume.file_url.endswith(".pdf")


def test_extract_docx_text_reads_paragraphs(tmp_path):
    path = tmp_path / "resume.docx"
    document = Document()
    document.add_paragraph("项目经验")
    document.add_paragraph("FastAPI 后端开发")
    document.save(path)

    text = ResumeService._extract_resume_text(str(path))

    assert "项目经验" in text
    assert "FastAPI 后端开发" in text


def test_parse_resume_record_marks_completed(monkeypatch, tmp_path):
    path = tmp_path / "resume.docx"
    document = Document()
    document.add_paragraph("Python 后端开发")
    document.save(path)

    async def fake_parse_resume(text):
        assert "Python" in text
        return {"name": "张三"}

    async def fake_analyze_resume(parsed, target_position):
        assert parsed["name"] == "张三"
        assert target_position == "后端开发"
        return {"score": 8}

    monkeypatch.setattr(resume_module.AIService, "parse_resume", fake_parse_resume)
    monkeypatch.setattr(resume_module.AIService, "analyze_resume", fake_analyze_resume)

    resume = Resume(
        id=42,
        user_id=7,
        file_url=str(path),
        file_name="resume.docx",
        target_position="后端开发",
        status="parsing",
    )
    db = FakeDb(resume)

    asyncio.run(ResumeService.parse_resume_record(db, 42, 7))

    assert resume.status == "completed"
    assert '"name": "张三"' in resume.parsed_content
    assert '"score": 8' in resume.analysis
