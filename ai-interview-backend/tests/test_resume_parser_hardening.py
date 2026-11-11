import asyncio
import hashlib
import io
import json
from types import SimpleNamespace

import pytest
from docx import Document
from pydantic import ValidationError as PydanticValidationError
from PIL import Image

from app.models.resume import Resume
from app.prompts.interview import RESUME_PARSE_PROMPT_VERSION
from app.schemas.client.parsed_resume import ParsedResume
from app.services.client import document_parser
from app.services.client.ai_service import AIService
from app.services.client import resume_service as resume_module
from app.services.client.resume_service import ResumeService
from app.services.common import redis as redis_module


def test_parsed_resume_normalizes_model_variants_and_keeps_only_known_fields():
    parsed = ParsedResume.model_validate(
        {
            "name": "  张三  ",
            "education": [{"school": "示例大学", "degree": "本科"}],
            "skills": [
                {"value": "Python", "evidence": "技能栏"},
                "SQL、Redis",
            ],
            "experience": {"company": "示例公司", "role": "后端开发"},
            "projects": ["项目A", {"name": "项目B", "role": "负责人"}],
            "summary": "后端工程师",
            "desired_role": "Python 后端",
        }
    )

    assert parsed.name == "张三"
    assert "示例大学" in parsed.education
    assert parsed.skills == ["Python", "SQL", "Redis"]
    assert parsed.experience == ["company: 示例公司; role: 后端开发"]
    assert parsed.projects == ["项目A", "name: 项目B; role: 负责人"]
    assert "desired_role" not in parsed.model_dump()


def test_parsed_resume_rejects_empty_or_invalid_structure():
    with pytest.raises(PydanticValidationError):
        ParsedResume.model_validate({})

    with pytest.raises(PydanticValidationError):
        ParsedResume.model_validate({"name": "张三", "skills": 42})


def test_parse_resume_cache_uses_full_text_and_model_prompt_versions(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.inputs = []

        async def get_llm_cache(self, prefix, content):
            assert prefix == "parse"
            self.inputs.append(content)
            return None

        async def set_llm_cache(self, prefix, content, result, ttl):
            assert prefix == "parse"
            assert content in self.inputs
            assert ttl == 3600

    cache = FakeRedis()

    async def fake_chat(*args, **kwargs):
        return json.dumps({"name": "候选人", "skills": ["Python"]}, ensure_ascii=False)

    monkeypatch.setattr(redis_module, "redis_client", cache)
    monkeypatch.setattr(AIService, "_chat", staticmethod(fake_chat))

    common_prefix = "简历开头内容" * 100
    first_text = common_prefix + "后续项目：订单系统"
    second_text = common_prefix + "后续项目：推荐系统"
    first = asyncio.run(AIService.parse_resume(first_text))
    second = asyncio.run(AIService.parse_resume(second_text))

    assert first["skills"] == ["Python"]
    assert second["skills"] == ["Python"]
    assert len(cache.inputs) == 2
    first_input, second_input = [json.loads(item) for item in cache.inputs]
    assert first_input["resume_sha256"] == hashlib.sha256(first_text.encode("utf-8")).hexdigest()
    assert second_input["resume_sha256"] == hashlib.sha256(second_text.encode("utf-8")).hexdigest()
    assert first_text[:500] == second_text[:500]
    assert cache.inputs[0] != cache.inputs[1]
    assert first_input["version"] == RESUME_PARSE_PROMPT_VERSION
    assert first_input["model"]
    assert first_input["temperature"] == 0.3
    assert first_input["provider"] in {"qwen", "default"}


def test_parse_pdf_tracks_scanned_pages_individually(monkeypatch):
    class FakePage:
        width = 600
        height = 800

        def __init__(self, has_image, words):
            self.images = [object()] if has_image else []
            self._words = words

        def extract_words(self):
            return self._words

        def extract_tables(self):
            return []

    def word(text):
        return {
            "text": text,
            "x0": 20,
            "x1": 20 + len(text) * 5,
            "top": 20,
            "bottom": 30,
            "size": 10,
        }

    class FakePdf:
        pages = [
            FakePage(True, [word("可复制文字页中有足够长的简历内容与工作经历" * 2)]),
            FakePage(True, []),
        ]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("pdfplumber.open", lambda path: FakePdf())

    parsed = document_parser.parse_pdf("resume.pdf")

    assert parsed.page_count == 2
    assert parsed.has_images is True
    assert parsed.is_scanned is True
    assert parsed.scanned_pages == [2]
    assert len(parsed.page_texts) == 2
    assert "可复制文字页" in parsed.text


def test_vlm_ocr_only_accepts_complete_nonempty_page_results(monkeypatch):
    requested = []
    images = [b"page-2", b"page-4"]

    def fake_render(file_path, page_numbers):
        requested.append(page_numbers)
        return images

    async def fake_ocr(image_bytes, model):
        return "识别内容" if image_bytes == b"page-2" else "  "

    monkeypatch.setattr(document_parser, "_render_pdf_pages", fake_render)
    monkeypatch.setattr(AIService, "ocr_image", staticmethod(fake_ocr))

    result = asyncio.run(
        document_parser.ocr_pdf_with_vlm("resume.pdf", "vision-model", [2, 4])
    )

    assert requested == [[2, 4]]
    assert result is None


def test_vlm_ocr_returns_page_labels_for_selected_pages(monkeypatch):
    monkeypatch.setattr(
        document_parser,
        "_render_pdf_pages",
        lambda file_path, page_numbers: [b"page-2", b"page-4"],
    )

    async def fake_ocr(image_bytes, model):
        return f"识别 {image_bytes.decode()}"

    monkeypatch.setattr(AIService, "ocr_image", staticmethod(fake_ocr))

    result = asyncio.run(
        document_parser.ocr_pdf_with_vlm("resume.pdf", "vision-model", [2, 4])
    )

    assert result == {2: "识别 page-2", 4: "识别 page-4"}


def test_png_bytes_encodes_a_real_png_image():
    image = Image.new("RGB", (2, 2), color="white")
    encoded = document_parser._png_bytes(image)

    assert encoded.startswith(b"\x89PNG\r\n\x1a\n")


def test_parse_docx_extracts_embedded_images(tmp_path):
    image = Image.new("RGB", (4, 4), color="white")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")
    image.close()

    path = tmp_path / "resume.docx"
    document = Document()
    document.add_paragraph("有正文的简历")
    document.add_picture(io.BytesIO(image_bytes.getvalue()))
    document.save(path)

    parsed = document_parser.parse_document(str(path), path.name)

    assert parsed.has_images is True
    assert parsed.image_count == 1
    assert parsed.image_payloads[0][0] == "image/png"
    assert parsed.image_payloads[0][1].startswith(b"\x89PNG\r\n\x1a\n")


def test_docx_image_ocr_normalizes_input_to_png(monkeypatch):
    image = Image.new("RGB", (3, 3), color="white")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="JPEG")
    image.close()
    received = []

    async def fake_ocr(png_bytes, model):
        received.append((png_bytes, model))
        return "图片中的项目名称"

    monkeypatch.setattr(AIService, "ocr_image", staticmethod(fake_ocr))

    result = asyncio.run(
        document_parser.ocr_docx_images_with_vlm(
            [("image/jpeg", image_bytes.getvalue())], "vision-model"
        )
    )

    assert received[0][0].startswith(b"\x89PNG\r\n\x1a\n")
    assert received[0][1] == "vision-model"
    assert "图片中的项目名称" in result


def test_resume_service_keeps_extractable_text_when_adding_ocr(monkeypatch):
    resume = Resume(
        id=42,
        user_id=7,
        file_url="resume.pdf",
        file_name="resume.pdf",
        target_position="后端开发",
        status="parsing",
    )

    class FakeDb:
        commits = 0

        async def execute(self, query):
            return SimpleNamespace(scalar_one_or_none=lambda: resume)

        async def commit(self):
            self.commits += 1

    parsed_document = document_parser.ParsedDocument(source_type="pdf")
    parsed_document.text = "第一页可复制的原始文字"
    parsed_document.is_scanned = True
    parsed_document.scanned_pages = [2]
    parsed_document.page_texts = ["第一页可复制的原始文字", ""]
    monkeypatch.setattr(resume_module, "parse_document", lambda *args: parsed_document)
    monkeypatch.setattr(
        resume_module,
        "settings",
        SimpleNamespace(AI_OCR_ENABLED=True, AI_VISION_MODEL="vision-model"),
    )
    requested_pages = []

    async def fake_ocr(file_path, model, page_numbers):
        requested_pages.extend(page_numbers)
        return {2: "扫描页文字"}

    parsed_text = []

    async def fake_parse_resume(text):
        parsed_text.append(text)
        return {"name": "候选人", "skills": ["Python"]}

    async def fake_analyze_resume(parsed, target_position):
        return {"score": 8}

    monkeypatch.setattr(resume_module, "ocr_pdf_with_vlm", fake_ocr)
    monkeypatch.setattr(AIService, "parse_resume", staticmethod(fake_parse_resume))
    monkeypatch.setattr(AIService, "analyze_resume", staticmethod(fake_analyze_resume))

    asyncio.run(ResumeService.parse_resume_record(FakeDb(), 42, 7))

    assert requested_pages == [2]
    assert "第一页可复制的原始文字" in parsed_text[0]
    assert "扫描页文字" in parsed_text[0]
    assert parsed_text[0].index("第一页可复制的原始文字") < parsed_text[0].index("扫描页文字")
    assert resume.status == "completed"


def test_resume_service_adds_docx_image_ocr_when_enabled(monkeypatch):
    resume = Resume(
        id=43,
        user_id=7,
        file_url="resume.docx",
        file_name="resume.docx",
        target_position="后端开发",
        status="parsing",
    )

    class FakeDb:
        async def execute(self, query):
            return SimpleNamespace(scalar_one_or_none=lambda: resume)

        async def commit(self):
            pass

    parsed_document = document_parser.ParsedDocument(source_type="docx")
    parsed_document.text = "DOCX 正文经历"
    parsed_document.image_payloads = [("image/png", b"image-bytes")]
    parsed_document.image_count = 1
    parsed_document.has_images = True
    monkeypatch.setattr(resume_module, "parse_document", lambda *args: parsed_document)
    monkeypatch.setattr(
        resume_module,
        "settings",
        SimpleNamespace(AI_OCR_ENABLED=True, AI_VISION_MODEL="vision-model"),
    )
    parsed_text = []

    async def fake_ocr(images, model):
        assert images == parsed_document.image_payloads
        assert model == "vision-model"
        return "[DOCX 图片 OCR 补充 1]\n图片中的项目经历"

    async def fake_parse_resume(text):
        parsed_text.append(text)
        return {"name": "候选人", "skills": ["Python"]}

    async def fake_analyze_resume(parsed, target_position):
        return {"score": 8}

    monkeypatch.setattr(resume_module, "ocr_docx_images_with_vlm", fake_ocr)
    monkeypatch.setattr(AIService, "parse_resume", staticmethod(fake_parse_resume))
    monkeypatch.setattr(AIService, "analyze_resume", staticmethod(fake_analyze_resume))

    asyncio.run(ResumeService.parse_resume_record(FakeDb(), 43, 7))

    assert "DOCX 正文经历" in parsed_text[0]
    assert "图片中的项目经历" in parsed_text[0]
    assert resume.status == "completed"
