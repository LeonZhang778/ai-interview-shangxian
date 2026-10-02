"""
文档解析模块（Document Parsing）

在原有 pdfplumber 纯文本抽取之上，补齐复杂文件解析能力：
- 多栏（multi-column）阅读顺序重排，避免双栏简历文字错乱；
- 表格结构识别并转为 Markdown（保留在正文供 LLM 理解）；
- 基于字号 / 关键词的标题（section）检测，输出结构感知的文本；
- 扫描件检测（含图片且几乎抽不到文字）；
- DOCX / TXT 多格式接入；
- 多模态 VLM OCR 兜底（能力检测后降级，不引入新依赖即可启用）。

设计原则（遵循项目最小改动铁律）：
- 仅依赖已安装库（pdfplumber / python-docx / PIL），不新增第三方库；
- VLM OCR 仅在配置 AI_OCR_ENABLED=True 且环境具备渲染器（PyMuPDF 或 pdf2image）
  与多模态模型（AI_VISION_MODEL）时启用，否则自动降级为清晰错误提示。
"""
import logging
import os
import re

logger = logging.getLogger(__name__)

# ---- 阈值常量（集中配置，便于调参）----
COLUMN_GAP_RATIO = 0.16        # 横向连续空白带宽度 > 页面宽度 16% 视为分栏分隔
LINE_TOL_RATIO = 0.6           # 行合并容差（相对字高）
HEADING_SIZE_RATIO = 1.22      # 字号 > 页面中位数 * 1.22 视为标题候选
HEADING_MAX_LEN = 30           # 标题最大字符数，超过则不当标题
SECTION_KEYWORDS = (
    "教育", "工作", "项目", "实习", "经历", "技能", "荣誉", "奖励", "证书",
    "自我", "评价", "社团", "校园", "研究", "竞赛", "语言", "兴趣", "求职",
    "意向", "获奖", "社会", "实践",
)


def _median(vals):
    vals = [v for v in vals if v]
    if not vals:
        return 0
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _looks_like_heading(text: str) -> bool:
    t = text.strip()
    if not t or len(t) > HEADING_MAX_LEN:
        return False
    if any(k in t for k in SECTION_KEYWORDS):
        return True
    # 全大写英文短词（如 EDUCATION / SKILLS）
    if t.isupper() and 2 <= len(t) <= 18 and any(c.isalpha() for c in t):
        return True
    return False


def _group_lines(words: list) -> list:
    """把已按 top 排序的 word 列表，按纵向邻近度聚合成行；行内按 x0 排序。"""
    if not words:
        return []
    lines = []
    cur = [words[0]]
    cur_top = words[0]["top"]
    h = (words[0].get("bottom") or words[0]["top"] + 10) - words[0]["top"]
    tol = max(2.0, h * LINE_TOL_RATIO)
    for w in words[1:]:
        if abs(w["top"] - cur_top) <= tol:
            cur.append(w)
        else:
            lines.append(cur)
            cur = [w]
            cur_top = w["top"]
            h = (w.get("bottom") or w["top"] + 10) - w["top"]
            tol = max(2.0, h * LINE_TOL_RATIO)
    lines.append(cur)
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def _detect_column_divider(words: list, page_w: float) -> float | None:
    """
    基于词的水平投影，查找贯穿页面高度的竖向空白带，作为分栏分隔线 x 坐标。
    找不到返回 None（单栏）。
    """
    bins = 100
    col_w = page_w / bins
    col_span = [None] * bins
    for w in words:
        b = min(bins - 1, int(w["x0"] / col_w))
        e = min(bins - 1, int(w["x1"] / col_w))
        for i in range(b, e + 1):
            if col_span[i] is None:
                col_span[i] = [w["top"], w["bottom"]]
            else:
                col_span[i][0] = min(col_span[i][0], w["top"])
                col_span[i][1] = max(col_span[i][1], w["bottom"])

    min_gap_bins = max(2, int(COLUMN_GAP_RATIO * bins))
    i = 0
    n = bins
    while i < n:
        if col_span[i] is None:
            j = i
            while j < n and col_span[j] is None:
                j += 1
            if j - i >= min_gap_bins and i > 0 and j < n:
                # 空白带左右均有文字 → 视为分栏分隔
                return (i + (j - i) / 2.0) * col_w
            i = j
        else:
            i += 1
    return None


def _extract_page_text(page) -> tuple[str, list]:
    """返回 (按阅读顺序重排的正文, 检测到的章节标题列表)。"""
    words = page.extract_words()
    if not words:
        return "", []

    page_w = page.width
    divider = _detect_column_divider(words, page_w)
    if divider is not None:
        # 双栏：左栏整体读完再读右栏，避免上下错乱
        left = sorted([w for w in words if w["x0"] < divider], key=lambda w: w["top"])
        right = sorted([w for w in words if w["x0"] >= divider], key=lambda w: w["top"])
        lines = _group_lines(left) + _group_lines(right)
        logger.info(f"[doc-parse] 检测到多栏，分隔线 x={divider:.1f}（页面宽 {page_w:.1f}）")
    else:
        lines = _group_lines(sorted(words, key=lambda w: w["top"]))

    sizes = [w.get("size") or 0 for w in words]
    median_size = _median(sizes) or 0

    headings = []
    out_lines = []
    for line in lines:
        line_text = " ".join(w["text"] for w in line).strip()
        if not line_text:
            continue
        line_size = max((w.get("size") or 0) for w in line)
        is_heading = (line_size >= median_size * HEADING_SIZE_RATIO) or _looks_like_heading(line_text)
        if is_heading:
            headings.append({"title": line_text, "level": 2})
            out_lines.append(f"\n## {line_text}")
        else:
            out_lines.append(line_text)

    return "\n".join(out_lines).strip(), headings


def _table_to_markdown(rows: list) -> str:
    """把二维 cell 列表（含 None）转成 Markdown 表格（首行作表头）。"""
    clean = [r for r in rows if any(c is not None and str(c).strip() for c in r)]
    if not clean:
        return ""
    ncols = max(len(r) for r in clean)
    lines = []
    for ri, r in enumerate(clean):
        cells = [( "" if c is None else str(c).replace("\n", " ").strip()) for c in r]
        while len(cells) < ncols:
            cells.append("")
        lines.append("| " + " | ".join(cells) + " |")
        if ri == 0:
            lines.append("| " + " | ".join(["---"] * ncols) + " |")
    return "\n".join(lines)


def _extract_page_tables(page) -> list:
    """抽取页面表格并转 Markdown，失败则降级跳过。"""
    try:
        tables = page.extract_tables()
    except Exception as e:  # 极少数 PDF 表格解析会抛错，不能影响整页
        logger.warning(f"[doc-parse] extract_tables 失败: {e}")
        return []
    md_tables = []
    for tbl in tables:
        if not tbl:
            continue
        md = _table_to_markdown(tbl)
        if md:
            md_tables.append(md)
    return md_tables


def parse_pdf(file_path: str) -> "ParsedDocument":
    import pdfplumber
    from app.core.config import settings

    doc = ParsedDocument(source_type="pdf")
    with pdfplumber.open(file_path) as pdf:
        doc.page_count = len(pdf.pages)
        parts = []
        for pi, page in enumerate(pdf.pages, start=1):
            if page.images:
                doc.has_images = True
            page_text, headings = _extract_page_text(page)
            for h in headings:
                doc.sections.append({**h, "page": pi})
            for t in _extract_page_tables(page):
                doc.tables.append({"page": pi, "markdown": t})
                parts.append(f"\n[表格 P{pi}]\n" + t)
            if page_text:
                parts.append(f"\n[第 {pi} 页]\n" + page_text)
        doc.text = "\n".join(parts).strip()

    min_chars = getattr(settings, "DOC_PARSER_MIN_TEXT_CHARS", 30)
    if doc.has_images and len(doc.text) < min_chars:
        doc.is_scanned = True
        doc.warnings.append("检测到扫描件/图片型 PDF，纯文本抽取为空，建议开启 OCR / 多模态解析")
    if not doc.text and not doc.tables:
        doc.warnings.append("未抽取到任何文本或表格")
    return doc


def parse_docx(file_path: str) -> "ParsedDocument":
    from docx import Document

    doc = ParsedDocument(source_type="docx")
    d = Document(file_path)
    parts = []
    for p in d.paragraphs:
        t = p.text.strip()
        if t:
            parts.append(t)
    doc.text = "\n".join(parts)

    for tbl in d.tables:
        rows = [[c.text.strip().replace("\n", " ") for c in r.cells] for r in tbl.rows]
        md = _table_to_markdown(rows)
        if md:
            doc.tables.append({"page": 0, "markdown": md})
            doc.text += f"\n[表格]\n{md}"
    doc.page_count = 1
    return doc


def parse_text(file_path: str) -> "ParsedDocument":
    doc = ParsedDocument(source_type="txt")
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        doc.text = f.read().strip()
    doc.page_count = 1
    return doc


def parse_document(file_path: str, file_name: str) -> "ParsedDocument":
    """按扩展名分发解析器。"""
    ext = os.path.splitext(file_name)[1].lower()
    if ext == ".pdf":
        return parse_pdf(file_path)
    if ext in (".docx",):
        return parse_docx(file_path)
    if ext in (".txt", ".md", ".text"):
        return parse_text(file_path)
    raise ValueError(f"不支持的文件类型：{ext}（当前支持 PDF / DOCX / TXT / MD）")


def _render_pdf_pages(file_path: str) -> list:
    """
    把 PDF 每页渲染为 PNG 字节。优先 PyMuPDF(fitz)，其次 pdf2image。
    两者均未安装则返回空列表（由调用方降级）。
    """
    try:
        import fitz  # PyMuPDF
        pdf = fitz.open(file_path)
        return [page.get_pixmap(dpi=150).tobytes("png") for page in pdf]
    except ImportError:
        pass
    try:
        from pdf2image import convert_from_path
        imgs = convert_from_path(file_path, dpi=150)
        return [img.tobytes("png") for img in imgs]
    except ImportError:
        logger.warning("[doc-parse] 未安装 PyMuPDF/fitz 或 pdf2image，无法渲染 PDF 页面做 VLM OCR")
        return []


async def ocr_pdf_with_vlm(file_path: str, vision_model: str | None = None) -> str | None:
    """
    扫描件兜底：将 PDF 每页渲染为图片并调用多模态模型识别。
    需环境安装 PyMuPDF/pdf2image 且配置 AI_VISION_MODEL；任一缺失则降级返回 None。
    """
    if not vision_model:
        return None
    images = _render_pdf_pages(file_path)
    if not images:
        return None

    from app.services.client.ai_service import AIService
    texts = []
    for idx, img_bytes in enumerate(images, 1):
        try:
            txt = await AIService.ocr_image(img_bytes, vision_model)
            texts.append(f"[第 {idx} 页]\n{txt}")
        except Exception as e:
            logger.warning(f"[doc-parse] VLM OCR 第 {idx} 页失败: {e}")
    return "\n".join(texts) if texts else None


class ParsedDocument:
    """解析结果载体。"""

    def __init__(self, source_type: str = "unknown"):
        self.text = ""
        self.tables = []          # [{"page": int, "markdown": str}]
        self.sections = []        # [{"title": str, "level": int, "page": int}]
        self.page_count = 0
        self.has_images = False
        self.is_scanned = False
        self.warnings = []
        self.source_type = source_type

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "tables": self.tables,
            "sections": self.sections,
            "page_count": self.page_count,
            "has_images": self.has_images,
            "is_scanned": self.is_scanned,
            "warnings": self.warnings,
            "source_type": self.source_type,
        }
