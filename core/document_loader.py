from dataclasses import dataclass,field
from pathlib import Path
from pydoc import pager
from typing import Any

from pypdf import PdfReader

# 保存文档加载结果
# 语法糖，自动生成构造函数，不用写_init_
@dataclass
class LoadedDocument:
    source_path: str
    file_type: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]

    cleaned_lines = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)

# 做编码兜底，避免乱码
def _read_text_with_fallback(path: Path) -> str:
    encoding = ["utf-8", "utf-8-sig", "gb18030", "gbk"]

    for encoding in encoding:
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue

    raise ValueError(f"无法识别文件编码： {path}")

def load_txt(path: str | Path) -> LoadedDocument:
    path = Path(path)
    text = _read_text_with_fallback(path)

    return LoadedDocument(
        source_path=str(path),
        file_type="txt",
        text=_normalize_text(text),
        metadata={
            "filename": path.name,
            "suffix": path.suffix.lower(),
        },
    )

def load_md(path: str | Path) -> LoadedDocument:
    path = Path(path)
    text = _read_text_with_fallback(path)

    return LoadedDocument(
        source_path=str(path),
        file_type="md",
        text=_normalize_text(text),
        metadata={
            "file_name": path.name,
            "suffix": path.suffix.lower(),
        },
    )

def load_pdf(path: str | Path) -> LoadedDocument:
    path = Path(path)
    reader = PdfReader(str(path))

    page_texts = []
    for page_idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        page_texts.append(page_text)

    full_text = "\n\n".join(page_texts)

    return LoadedDocument(
        source_path=str(path),
        file_type="pdf",
        text=_normalize_text(full_text),
        metadata={
            "file_name": path.name,
            "suffix": path.suffix.lower(),
            "page_count": len(reader.pages),
        },
    )

# 统一调度入口
def load_document(path: str | Path) -> LoadedDocument:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在：{path}")

    suffix = path.suffix.lower()

    if suffix == ".md":
        return load_md(path)
    if suffix == ".pdf":
        return load_pdf(path)
    if suffix == ".txt":
        return load_txt(path)
    raise ValueError(f"暂不支持的文件类型：{suffix}")




# 把长文本切成chunk
def split_text(text: str, chunk_size: int = 500, chunk_overlap:int = 50) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于0")
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
        end = min(text_length, start + chunk_size)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == text_length:
            break

        start = end - chunk_overlap
    return chunks

def split_document(
        doc: LoadedDocument,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
) -> list[dict[str, Any]]:
    chunks = split_text(doc.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    return [
        {
            "chunk_id": idx,
            "source_path": doc.source_path,
            "file_type": doc.file_type,
            "text": chunk,
            "metadata": doc.metadata,
        }
        for idx, chunk in enumerate(chunks)
    ]
