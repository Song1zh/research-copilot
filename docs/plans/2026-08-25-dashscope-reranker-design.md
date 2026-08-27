# DashScope Reranker design

## Scope

Add an explicit `dashscope` reranker after vector/BM25 fusion. The first-stage
retrievers remain responsible for recall; `qwen3-rerank` only reorders the
deduplicated candidate chunks. `none` remains available for offline tests and
controlled A/B evaluation.

## Data flow

1. Retrieve up to 30 vector candidates and 30 BM25 candidates.
2. Normalize scores independently, fuse with the existing 0.6/0.4 weights,
   deduplicate by `paper_id::chunk_id`, and keep the best 30 candidates.
3. Send the query and candidate text to the DashScope-compatible `/reranks`
   endpoint with the Q&A retrieval instruction.
4. Map returned candidate indexes back to the original evidence dictionaries,
   preserve `hybrid_score` as `pre_rerank_score`, add `rerank_score`, and return
   the requested Top-K.

## Failure and observability contract

The provider is selected explicitly as `none` or `dashscope`. Missing API keys,
HTTP errors, malformed responses, duplicate/out-of-range indexes, and empty
documents raise errors. The code never silently falls back to the pre-rerank
order. Each returned evidence item records provider, model, candidate count,
latency, pre-rerank rank, and final rank.

## Verification

Unit tests use an injected fake HTTP client, so they do not consume cloud quota.
Tests cover provider validation, request/response mapping, missing credentials,
malformed responses, hybrid retrieval integration, and explicit error
propagation. The retrieval benchmark accepts both `none` and `dashscope` to
produce comparable Hit@5, Recall@5, MRR@5, latency, and failure reports.
