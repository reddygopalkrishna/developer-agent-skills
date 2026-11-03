# RAG evaluation recipe

Evaluate the two halves separately. If retrieval doesn't surface the right passages, no prompt will fix the answer.

## 1. Build the labeled set

Collect real questions first (search logs, support tickets, chat transcripts, interviews with users). Synthetic questions generated from documents are a useful supplement but tend to reuse the document's own wording, which makes retrieval look better than it is.

One JSONL line per question:

```json
{"id": "q-017", "question": "How long is the refund window for annual plans?", "relevant_doc_ids": ["billing/refunds.md#annual"], "reference_answer": "30 days from purchase.", "answerable": true, "tags": ["billing", "policy"]}
{"id": "q-018", "question": "Do you support payment in Bitcoin?", "relevant_doc_ids": [], "reference_answer": null, "answerable": false, "tags": ["billing", "negative"]}
```

Guidelines:

- 50 questions is a minimum to see big differences; a few hundred to trust small ones.
- Include 10-20% unanswerable questions.
- Cover each source type, each major topic, short keyword queries and long natural questions, follow-up questions that need chat history, and questions needing two documents.
- Label relevance at the level you retrieve (chunk or section). If chunk boundaries change often, label at the section/document level and map chunks back to it.
- Keep a held-out portion you don't look at while tuning.

## 2. Retrieval metrics

Run only the retrieval stage (after filters and reranking) and compare retrieved IDs to `relevant_doc_ids`.

| Metric | Meaning | Use it for |
|---|---|---|
| Recall@k | Fraction of questions where at least one relevant item is in the top k (or fraction of relevant items found) | The main metric: is the answer even available to the model? Use k = what you pass to the model. |
| MRR | Mean of 1 / rank of the first relevant item | How high the first good result lands. |
| nDCG@k | Rank-weighted relevance, supports graded labels | Comparing rerankers when multiple results are relevant. |
| Precision@k | Fraction of top k that are relevant | Noise level in the context you send. |

Also report recall@k for the candidate set before reranking (e.g. k = 50). If it's low, the problem is upstream of reranking (parsing, chunking, embeddings, keyword search).

## 3. Answer metrics

Run the full pipeline and grade each answer.

| Check | How |
|---|---|
| Faithfulness / groundedness | Every claim is supported by the retrieved passages. LLM judge with the passages and answer, binary per answer or per claim. |
| Answer correctness | Matches the reference answer. Exact/normalized match for short facts, LLM judge for prose. |
| Answer relevance | Addresses the question that was asked. |
| Citation validity | Cited IDs exist in the retrieved set (code check) and support the sentence they're attached to (judge). |
| Abstention | On unanswerable questions, the system says it doesn't know. Code check for the "not found" signal, or judge. |

Calibrate any LLM judge on 30-50 human-labeled answers before trusting it, and recheck after changing the judge prompt or model. See the `llm-evals` skill.

## 4. Iteration loop

1. Run the full eval and save results with the pipeline config (parser version, chunk size/overlap, embedding model, k values, reranker, prompt version).
2. Read the failures. Classify each by first failing stage: parsing, chunking, retrieval, reranking, generation, abstention.
3. Fix the most common failure class. Change one component.
4. Re-run. Keep the change only if the target metric improves and nothing else regresses beyond noise.
5. Repeat. Check the held-out set before shipping.

## 5. Report template

```
Pipeline: <config hash or description>
Questions: 240 (36 unanswerable)
Retrieval: recall@50 (pre-rerank) 0.93 | recall@5 0.81 | MRR 0.67
Answers:   correct 0.74 | faithful 0.95 | abstained correctly 0.83 | invalid citations 2
Latency p50/p95: 1.8s / 4.1s   Cost per query: <tokens or currency>
Top failure classes: chunk cut mid-table (11), wrong product version (7)
```
