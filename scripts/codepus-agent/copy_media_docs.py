"""将已整理的媒体工具开发文档复制到后端 docs 目录，保留后端现有 docs 内容。"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "spec" / "media-tools"
TARGET = ROOT / "ai-interview-backend" / "docs" / "开发文档" / "媒体工具模块"

if not SOURCE.is_dir():
    raise SystemExit(f"源文档目录不存在: {SOURCE}")

TARGET.mkdir(parents=True, exist_ok=True)
for source_path in SOURCE.rglob("*"):
    relative = source_path.relative_to(SOURCE)
    target_path = TARGET / relative
    if source_path.is_dir():
        target_path.mkdir(parents=True, exist_ok=True)
    else:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        print(target_path.relative_to(ROOT))

print(f"已复制到: {TARGET.relative_to(ROOT)}")
"""
