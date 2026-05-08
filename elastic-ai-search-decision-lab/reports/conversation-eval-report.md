# Conversational Retrieval Evaluation

Generated: `2026-05-08T07:29:55.279Z`
Corpus pages: `6`
Conversations: `2`

## Aggregate

| Metric | Value |
| --- | ---: |
| nDCG@5 | 0.833 |
| MRR@5 | 1.000 |
| Precision@3 | 0.722 |
| Recall@5 | 0.944 |

## By Turn Index

| Turn | nDCG@5 | MRR@5 | Precision@3 | Recall@5 |
| --- | ---: | ---: | ---: | ---: |
| turn_1 | 0.824 | 1.000 | 0.667 | 0.833 |
| turn_2 | 0.890 | 1.000 | 0.667 | 1.000 |
| turn_3 | 0.784 | 1.000 | 0.833 | 1.000 |

## By Strategy

| Strategy | nDCG@5 | MRR@5 | Precision@3 | Recall@5 |
| --- | ---: | ---: | ---: | ---: |
| isolated | 0.824 | 1.000 | 0.667 | 0.833 |
| contextual | 0.837 | 1.000 | 0.750 | 1.000 |

## Turn Metrics

| Conversation | Turn | Strategy | Top result | nDCG@5 | MRR@5 | Precision@3 | Recall@5 | Effective query |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| conv-hybrid-tuning | 1 | isolated | hybrid-search | 0.812 | 1.000 | 0.667 | 0.667 | How should I combine keyword and semantic search? |
| conv-hybrid-tuning | 2 | contextual | hybrid-search | 0.831 | 1.000 | 0.667 | 1.000 | combine keyword search semantic How do I tune it? |
| conv-hybrid-tuning | 3 | contextual | evaluation-metrics | 0.972 | 1.000 | 1.000 | 1.000 | combine keyword search semantic tune Which metrics prove the ranking improved? |
| conv-latency-filters | 1 | isolated | hybrid-search | 0.835 | 1.000 | 0.667 | 1.000 | When should I add reranking after hybrid retrieval? |
| conv-latency-filters | 2 | contextual | semantic-filters | 0.950 | 1.000 | 0.667 | 1.000 | add hybrid reranking retrieval What should I watch for in filters? |
| conv-latency-filters | 3 | contextual | semantic-filters | 0.596 | 1.000 | 0.667 | 1.000 | add filters hybrid reranking retrieval watch How do follow-up questions change the evaluation? |

## Retrieval Insight

Contextual follow-up turns carry prior terms into retrieval. This prevents short turns such as `How do I tune it?` and `What should I watch for in filters?` from being evaluated as isolated keyword queries.
