import argparse
import json

from core.document_loader import load_document
from core.text_splitter import split_document
from core.text_splitter import split_text
from core.vector_store import ChromaVectorStore
from core.retriever import retrieve_evidence

def main():
    print("test_retriever main() started")
    parser = argparse.ArgumentParser(description='Test retriever_evidence')
    parser.add_argument(
        "--paths",
        nargs="+",
        required=True,
        help="待索引文档路径，可传多个"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="检索问题",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="返回结果数量",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="chunk 大小",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=50,
        help="chunk overlap",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="./chroma_db",
        help="Chroma 持久化路径",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="demo_chunks",
        help="collection 名称",
    )

    args = parser.parse_args()
    all_chunk_dicts = []

    for path in args.paths:
        doc = load_document(path)
        chunks = split_document(
            doc,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        for chunk in chunks:
            all_chunk_dicts.append(
                {
                    "chunk_id":chunk.chunk_id,
                    "text":chunk.text,
                    "metadata":chunk.metadata,
                }
            )
    store = ChromaVectorStore(
        db_path=args.db_path,
        collection_name=args.collection,
    )

    print("开始 upsert")
    store.upsert_chunks(all_chunk_dicts)
    print("upsert 完成")

    evidence = retrieve_evidence(
        query=args.query,
        top_k=args.top_k,
        db_path=args.db_path,
        collection_name=args.collection,
    )
    print("\n=== Query ===")
    print(args.query)

    print("\n=== Evidence Results ===")
    for item in evidence:
        print(f"\n--- Rank {item['rank']} ---")
        print(json.dumps(
            {
                "score": item["score"],
                "raw_distance": item["raw_distance"],
                "metadata": item["metadata"],
                "text_preview": item["text"][:300],
            },
            ensure_ascii=False,
            indent=2,
        ))


if __name__ == "__main__":
    main()