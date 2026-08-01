"""Extract readable text from a legacy MS Word .doc file.

Strategy (in order):
1. olefile + parse WordDocument stream piece table (best, pure-python)
2. textract (if installed)
3. antiword (if installed)
4. raw OLE stream UTF-16-LE / cp936 scan fallback

Usage:
    python extract_doc_text.py <input.doc> [output.txt]
"""
from __future__ import annotations

import codecs
import re
import struct
import subprocess
import sys
from pathlib import Path


def _read_worddocument_stream(path: Path) -> str | None:
    """Parse the WordDocument stream from the OLE2 compound document.

    This is a minimal reader: it locates the 'WordDocument' stream via olefile,
    then reads the text according to the FIB (fcMin/fcMac for older docs, or
    the piece table in the table stream for newer .doc). Good enough for
    extraction of plain body text from most legacy .doc files.
    """
    try:
        import olefile  # type: ignore
    except ImportError:
        return None

    try:
        ole = olefile.OleFileIO(str(path))
    except Exception as exc:  # noqa: BLE001
        print(f"[olefile] open failed: {exc}", file=sys.stderr)
        return None

    try:
        if not ole.exists("WordDocument"):
            return None
        word = ole.openstream("WordDocument").read()
        # FIB: magic at 0x0000, nFib at 0x0002 (LE uint16), flags at 0x000A
        # fcMin (uint32) at 0x0018, fcMac (uint32) at 0x001C for nFib < 0x00C1
        if len(word) < 0x20:
            return None
        n_fib = struct.unpack_from("<H", word, 0x0002)[0]
        fc_min = struct.unpack_from("<I", word, 0x0018)[0]
        fc_mac = struct.unpack_from("<I", word, 0x001C)[0]

        text_bytes = b""
        # Piece table path: 0Table or 1Table stream holds CLX
        table_stream = None
        for name in ("1Table", "0Table"):
            if ole.exists(name):
                table_stream = ole.openstream(name).read()
                break

        if n_fib >= 0x00C1 and table_stream is not None:
            # fcClx / lcbClx are in the FIB; their offset depends on FIB version.
            # For nFib >= 0x00C1, fcClx is at 0x01A2 and lcbClx at 0x01A6.
            if len(word) >= 0x01AA:
                fc_clx = struct.unpack_from("<I", word, 0x01A2)[0]
                lcb_clx = struct.unpack_from("<I", word, 0x01A6)[0]
                if lcb_clx > 0 and fc_clx + lcb_clx <= len(table_stream):
                    text_bytes = _parse_clx(
                        table_stream, fc_clx, lcb_clx, word
                    )

        if not text_bytes and fc_mac > fc_min:
            # Legacy direct-text path: text sits inline in WordDocument stream.
            text_bytes = word[fc_min:fc_mac]

        # Word stores text as UTF-16-LE when fComplex bit is off; cp1252/cp936
        # when on. Try UTF-16 first, then cp936 (GBK, common for Chinese docs),
        # then cp1252.
        for enc in ("utf-16-le", "utf-16", "cp936", "gb18030", "cp1252"):
            try:
                decoded = text_bytes.decode(enc)
                # Heuristic: if UTF-16 decode yields too many CJK / control
                # junk, prefer cp936. Accept if printable ratio high.
                printable = sum(
                    1 for c in decoded if c.isprintable() or c in "\n\r\t"
                )
                if decoded and printable / max(1, len(decoded)) > 0.55:
                    return _clean(decoded)
            except (UnicodeDecodeError, ValueError):
                continue
        if text_bytes:
            return _clean(text_bytes.decode("utf-16-le", errors="ignore"))
        return None
    finally:
        ole.close()


def _parse_clx(table: bytes, fc_clx: int, lcb_clx: int, word: bytes) -> bytes:
    """Parse a CLX (piece table) from the table stream and assemble text."""
    out = bytearray()
    pos = fc_clx
    end = fc_clx + lcb_clx
    while pos < end:
        # Each entry: 0x01 = grpprl (property table, skip), 0x02 = pcdt
        if pos >= len(table):
            break
        clxt = table[pos]
        if clxt == 0x01:
            cb = struct.unpack_from("<H", table, pos + 1)[0]
            pos += 3 + cb
        elif clxt == 0x02:
            lcb_pcdt = struct.unpack_from("<I", table, pos + 1)[0]
            pcd_start = pos + 5
            pcd_end = pcd_start + lcb_pcdt
            # PlcfPcd: array of CP (uint32) followed by array of PCD (8 bytes)
            # number of pieces = (lcb_pcdt - 4) / (4 + 8)
            n_pieces = (lcb_pcdt - 4) // 12
            cps = [
                struct.unpack_from("<I", table, pcd_start + i * 4)[0]
                for i in range(n_pieces + 1)
            ]
            pcd_base = pcd_start + (n_pieces + 1) * 4
            for i in range(n_pieces):
                pcd = table[pcd_base + i * 8 : pcd_base + (i + 1) * 8]
                fc_field = struct.unpack_from("<I", pcd, 2)[0]
                f_compressed = (fc_field >> 30) & 1  # bit 30 (1 = ANSI/cp1252)
                fc = fc_field & 0x3FFFFFFF
                cp_start = cps[i]
                cp_end = cps[i + 1]
                char_count = cp_end - cp_start
                if f_compressed:
                    real_fc = fc // 2
                    chunk = word[real_fc : real_fc + char_count]
                    out += chunk  # cp1252 decode later
                else:
                    chunk = word[fc : fc + char_count * 2]
                    out += chunk
            pos = pcd_end
        else:
            break
    return bytes(out)


def _clean(text: str) -> str:
    """Normalize whitespace and strip binary junk."""
    text = text.replace("\r", "\n")
    text = re.sub(r"\x00+", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _try_antitword(path: Path) -> str | None:
    for exe in ("antiword", "catdoc"):
        try:
            res = subprocess.run(
                [exe, str(path)], capture_output=True, timeout=30
            )
            if res.returncode == 0 and res.stdout:
                for enc in ("utf-8", "cp936", "gb18030", "cp1252"):
                    try:
                        return _clean(res.stdout.decode(enc))
                    except UnicodeDecodeError:
                        continue
        except FileNotFoundError:
            continue
        except Exception:  # noqa: BLE001
            continue
    return None


def _raw_scan(path: Path) -> str:
    """Last-resort: scan raw bytes for UTF-16-LE and cp936 printable runs."""
    data = path.read_bytes()
    # Try UTF-16-LE scan: every other byte should be 0x00 for ASCII/CJK BMP.
    try:
        decoded = data.decode("utf-16-le", errors="ignore")
        cleaned = _clean(decoded)
        if len(cleaned) > 50:
            return cleaned
    except Exception:  # noqa: BLE001
        pass
    # cp936 / gb18030 whole-file decode
    for enc in ("gb18030", "cp936", "cp1252"):
        try:
            return _clean(data.decode(enc, errors="ignore"))
        except Exception:  # noqa: BLE001
            continue
    return ""


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    src = Path(argv[1])
    if not src.exists():
        print(f"NOT FOUND: {src}", file=sys.stderr)
        return 1
    out_path = Path(argv[2]) if len(argv) > 2 else src.with_suffix(".txt")

    text = _read_worddocument_stream(src)
    method = "olefile+CLX"
    if not text:
        text = _try_antitword(src)
        method = "antiword/catdoc"
    if not text:
        text = _raw_scan(src)
        method = "raw-scan"

    out_path.write_text(text or "", encoding="utf-8")
    print(f"[{method}] extracted {len(text or '')} chars -> {out_path}")
    return 0 if text else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
