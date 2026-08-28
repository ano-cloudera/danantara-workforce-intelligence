from __future__ import annotations

import re
import textwrap


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _strip_markdown(text: str) -> str:
    """Strip list markers and bold/italic tokens for a plain-text PDF; this
    renderer has no font styling, so leaving them in would just show up as
    literal asterisks/underscores rather than structure or emphasis."""
    text = re.sub(r"(?m)^\s*[*-]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!_)_([^_\n]+?)_(?!_)", r"\1", text)
    return text


def _message_lines(role: str, content: str, sources: list[dict]) -> list[str]:
    speaker = "You" if role == "user" else "Policy Intelligence"
    lines = [f"{speaker}:", _strip_markdown(content)]
    for index, source in enumerate(sources, start=1):
        location = f'page {source.get("page")}' if source.get("page") else "section unavailable"
        lines.append(
            f'  [{index}] {source.get("title", "Policy source")} '
            f'({source.get("entity") or "Entity unavailable"}, {location})'
        )
    return lines


def _lines(title: str, messages: list[dict]) -> list[str]:
    lines = [title, ""]
    for message in messages:
        lines.extend(_message_lines(message.get("role", ""), message.get("content", ""), message.get("sources") or []))
        lines.append("")
    wrapped = []
    for line in lines:
        if not line:
            wrapped.append("")
        else:
            wrapped.extend(textwrap.wrap(str(line), width=94, break_long_words=False) or [""])
    return wrapped


def build_policy_pdf(title: str, messages: list[dict]) -> bytes:
    """Create a dependency-free, text-only PDF transcript of a policy chat session."""
    lines = _lines(title, messages)
    pages = [lines[index : index + 54] for index in range(0, len(lines), 54)] or [[title]]
    font_id = 3
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        font_id: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    }
    page_ids = []
    for index, page_lines in enumerate(pages):
        page_id = 4 + index * 2
        content_id = page_id + 1
        page_ids.append(page_id)
        commands = ["BT", "/F1 10 Tf", "45 790 Td", "13 TL"]
        for line in page_lines:
            encoded = str(line).encode("latin-1", "replace").decode("latin-1")
            commands.append(f"({_pdf_escape(encoded)}) Tj")
            commands.append("T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode("ascii")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        )
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[2] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {0: 0}
    for object_id in range(1, max(objects) + 1):
        offsets[object_id] = len(output)
        output.extend(f"{object_id} 0 obj\n".encode("ascii"))
        output.extend(objects[object_id])
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {max(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for object_id in range(1, max(objects) + 1):
        output.extend(f"{offsets[object_id]:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {max(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)
