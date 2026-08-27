from dataclasses import dataclass, field
from typing import Any

from core.document_loader import LoadedDocument


@dataclass
class TextChunk:
    chunk_id: int
    text: str
    start: int
    end: int
    metadata: dict[str, Any] = field(default_factory=dict)


def _find_best_split(text: str, start: int, target_end: int, search_window: int = 80) -> int:
    """
    尽量把切分点放在更自然的位置：
    1. 优先找换行
    2. 其次找中文句号/问号/感叹号/分号
    3. 再找空格
    4. 实在找不到就硬切
    """
    text_length = len(text)
    if target_end >= text_length:
        return text_length

    lower_bound = max(start + 1, target_end - search_window)

    preferred_chars = set("\n。！？；!?;")
    for i in range(target_end, lower_bound - 1, -1):
        if text[i - 1] in preferred_chars:
            return i

    for i in range(target_end, lower_bound - 1, -1):
        if text[i - 1].isspace():
            return i

    return target_end


def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    search_window: int = 80,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap 不能小于 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        target_end = min(start + chunk_size, text_length)
        end = _find_best_split(text, start, target_end, search_window=search_window)

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(start + 1, end - chunk_overlap)
        while next_start < text_length and text[next_start].isspace():
            next_start += 1

        start = next_start

    return chunks


def split_document(
    doc: LoadedDocument,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    search_window: int = 80,
) -> list[TextChunk]:
    raw_chunks = split_text(
        doc.text,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        search_window=search_window,
    )

    chunks: list[TextChunk] = []
    cursor = 0

    for idx, chunk in enumerate(raw_chunks):
        start = doc.text.find(chunk, cursor)
        if start == -1:
            start = cursor
        end = start + len(chunk)
        cursor = end

        chunks.append(
            TextChunk(
                chunk_id=idx,
                text=chunk,
                start=start,
                end=end,
                metadata={
                    "source_path": doc.source_path,
                    "file_type": doc.file_type,
                    **doc.metadata,
                },
            )
        )

    return chunks