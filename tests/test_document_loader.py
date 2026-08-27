import argparse

from core.document_loader import load_document, split_document

def main():
    parser = argparse.ArgumentParser(description="Test document loader")
    parser.add_argument("--path", type=str, required=True, help="文档路径")
    parser.add_argument("--chunk-size", type=int, default=300, help="切分长度")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="切分重叠长度")

    #解析命令行参数
    args = parser.parse_args()

    doc = load_document(args.path)

    print("\n=== 文档基本信息 ===")
    print({
        "source_path": doc.source_path,
        "file_type": doc.file_type,
        "text_length": len(doc.text),
        "metadata": doc.metadata,
    })

    print("\n=== 切分前预览（前 300 字符） ===")
    print(doc.text[:300])

    chunks = split_document(
        doc,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    print("\n=== 切分后结果 ===")
    print({
        "chunk_count": len(chunks),
        "first_chunk_length": len(chunks[0]["text"]) if chunks else 0,
    })

    for chunk in chunks[:2]:
        print(f"\n--- chunk {chunk['chunk_id']} ---")
        print(chunk["text"][:300])

if __name__ == "__main__":
    main()