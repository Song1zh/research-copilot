import argparse

from core.document_loader import load_document
from core.text_splitter import split_document


def main():
    print(">>> test_text_splitter main() started")

    parser = argparse.ArgumentParser(description="Test text splitter")
    parser.add_argument("--path", type=str, required=True, help="文档路径")
    parser.add_argument("--chunk-size", type=int, default=500, help="chunk 大小")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="chunk 重叠")
    args = parser.parse_args()

    doc = load_document(args.path)
    chunks = split_document(
        doc,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )

    print("\n=== 文档基本信息 ===")
    print({
        "source_path": doc.source_path,
        "file_type": doc.file_type,
        "text_length": len(doc.text),
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "chunk_count": len(chunks),
    })

    print("\n=== 原文前 300 字符 ===")
    print(doc.text[:300])

    print("\n=== 前 3 个 chunk 预览 ===")
    for chunk in chunks[:3]:
        print(f"\n--- chunk {chunk.chunk_id} [{chunk.start}:{chunk.end}] ---")
        print(chunk.text[:300])


if __name__ == "__main__":
    main()