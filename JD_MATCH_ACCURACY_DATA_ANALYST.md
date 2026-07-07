# JD Match Ranking Accuracy — Data Analyst Project

Job description used (Walmart-style Product/Data Analyst role, pasted verbatim into the JD Match tab), ranked against all 51 CVs in the **Data Analyst** project (`project_id=3`), via `POST /cvs/rank`.

**Ground-truth top 10** (provided by the reviewer, order given):

1. `a34.jpg`
2. `a41.jpg`
3. `a50.jpg`
4. `a40.jpg`
5. `a49.jpg`
6. `a39.jpg`
7. `a35.png`
8. `a36.png`
9. `a46.jpg`
10. `a32.jpg`

**Accuracy metric**: precision@10 — how many of the reviewer's 10 ground-truth CVs appear anywhere in each ranker's own top-10 output (order not required to match).

## Summary

| Ranker | Overlap with ground truth | Accuracy (precision@10) |
|---|---|---|
| TF-IDF | 6/10 | 60.0% |
| model-best (embeddings) | 3/10 | 30.0% |
| model-best 2 (embeddings) | 5/10 | 50.0% |
| model-best hybrid (67% embedding + 33% NER) | 3/10 | 30.0% |
| model-best 2 hybrid (67% embedding + 33% NER) | 5/10 | 50.0% |

**Best performer:** TF-IDF at 60.0% precision@10.

## Top 10 results per ranker

### TF-IDF

| # | Filename | Score | In ground truth? |
|---|---|---|---|
| 1 | `a50.jpg` | 17.13 | ✅ |
| 2 | `a39.jpg` | 12.25 | ✅ |
| 3 | `a34.jpg` | 11.84 | ✅ |
| 4 | `a41.jpg` | 10.53 | ✅ |
| 5 | `a32.jpg` | 9.15 | ✅ |
| 6 | `a4.png` | 9.14 | — |
| 7 | `a40.jpg` | 8.93 | ✅ |
| 8 | `a45.jpg` | 8.19 | — |
| 9 | `a43.jpg` | 7.28 | — |
| 10 | `a38.jpg` | 7.23 | — |

### model-best (embeddings)

| # | Filename | Score | In ground truth? |
|---|---|---|---|
| 1 | `a38.jpg` | 98.05 | — |
| 2 | `a27.jpg` | 97.91 | — |
| 3 | `a23.png` | 97.87 | — |
| 4 | `a50.jpg` | 97.11 | ✅ |
| 5 | `a45.jpg` | 96.94 | — |
| 6 | `a49.jpg` | 96.86 | ✅ |
| 7 | `a21.jpg` | 96.24 | — |
| 8 | `a12.jpg` | 96.07 | — |
| 9 | `a13.jpg` | 96.07 | — |
| 10 | `a32.jpg` | 96.07 | ✅ |

### model-best 2 (embeddings)

| # | Filename | Score | In ground truth? |
|---|---|---|---|
| 1 | `a50.jpg` | 95.92 | ✅ |
| 2 | `a23.png` | 94.84 | — |
| 3 | `a39.jpg` | 94.22 | ✅ |
| 4 | `a46.jpg` | 94.18 | ✅ |
| 5 | `a40.jpg` | 94.07 | ✅ |
| 6 | `a32.jpg` | 94.06 | ✅ |
| 7 | `a43.jpg` | 93.37 | — |
| 8 | `a45.jpg` | 93.36 | — |
| 9 | `a38.jpg` | 93.12 | — |
| 10 | `a42.png` | 92.91 | — |

### model-best hybrid (67% embedding + 33% NER)

| # | Filename | Score | In ground truth? |
|---|---|---|---|
| 1 | `a38.jpg` | 65.36 | — |
| 2 | `a27.jpg` | 65.28 | — |
| 3 | `a23.png` | 65.25 | — |
| 4 | `a50.jpg` | 64.74 | ✅ |
| 5 | `a45.jpg` | 64.63 | — |
| 6 | `a49.jpg` | 64.57 | ✅ |
| 7 | `a21.jpg` | 64.16 | — |
| 8 | `a12.jpg` | 64.04 | — |
| 9 | `a13.jpg` | 64.04 | — |
| 10 | `a32.jpg` | 64.04 | ✅ |

### model-best 2 hybrid (67% embedding + 33% NER)

| # | Filename | Score | In ground truth? |
|---|---|---|---|
| 1 | `a50.jpg` | 63.95 | ✅ |
| 2 | `a23.png` | 63.23 | — |
| 3 | `a39.jpg` | 62.81 | ✅ |
| 4 | `a46.jpg` | 62.79 | ✅ |
| 5 | `a32.jpg` | 62.71 | ✅ |
| 6 | `a40.jpg` | 62.71 | ✅ |
| 7 | `a43.jpg` | 62.24 | — |
| 8 | `a45.jpg` | 62.24 | — |
| 9 | `a38.jpg` | 62.08 | — |
| 10 | `a42.png` | 61.94 | — |

## Where each ground-truth CV landed in the full ranking

Rank position (1 = best match) within each ranker's complete ordering of all 51 CVs — not just the top 10. Positions ≤10 are the ones counted in the accuracy above.

| Ground-truth CV | TF-IDF | model-best (embeddings) | model-best 2 (embeddings) | model-best hybrid (67% embedding + 33% NER) | model-best 2 hybrid (67% embedding + 33% NER) |
|---|---|---|---|---|---|
| `a34.jpg` | **3** | 18 | 23 | 18 | 23 |
| `a41.jpg` | **4** | 28 | 24 | 28 | 24 |
| `a50.jpg` | **1** | **4** | **1** | **4** | **1** |
| `a40.jpg` | **7** | 11 | **5** | 11 | **6** |
| `a49.jpg` | 12 | **6** | 17 | **6** | 17 |
| `a39.jpg` | **2** | 15 | **3** | 15 | **3** |
| `a35.png` | 14 | 23 | 44 | 23 | 44 |
| `a36.png` | 13 | 36 | 28 | 36 | 28 |
| `a46.jpg` | 18 | 12 | **4** | 12 | **4** |
| `a32.jpg` | **5** | **10** | **6** | **10** | **5** |

## Observations

- **TF-IDF scored highest (60%)** on this JD, likely because the JD is heavily keyword/phrase driven ("click stream data", "A/B Test", "dashboards", "Product Managers") and TF-IDF rewards literal lexical overlap directly, whereas the embedding models compress the whole document into a single vector and are more sensitive to overall topical similarity than exact phrasing.
- **model1 and model1_hybrid tied at the lowest score (30%)**. Both share the same embedding backbone, so the 1/3 NER-keyword blend in the hybrid variant didn't move the needle here — model1's raw embedding ranking is the dominant factor for this project's CVs.
- **model2 and model2_hybrid tied at 50%**, ranking above model1/model1_hybrid but below TF-IDF. Same pattern: the hybrid blend barely shifted model2's ranking (only reordered scores, not membership in the top 10), suggesting the NER-keyword overlap component is contributing a fairly uniform boost/penalty across candidates rather than discriminating sharply for this JD.
- **`a50.jpg` and `a32.jpg` were picked up by all 5 rankers' top 10** — the strongest, most consistent matches for this JD across every method.
- **`a35.png` and `a36.png` were missed by every ranker's top 10**, and in the embedding-based methods (model1/model2 and their hybrids) they fell quite far down the full ranking (23rd–44th) — worth a manual look at those two CVs to see whether they're genuinely weaker fits or whether OCR/NER extraction quality is holding them back.
- **`a41.jpg` also missed every ranker's top 10**, landing in the high teens–20s across all methods — the next-closest miss after a35/a36.

## Method

1. JD text submitted via `POST /cvs/rank` with `project_id=3`, `top_n=51` (i.e. the full project) for each of the 5 methods, to get both the top-10 cut and each ground-truth CV's true rank position.
2. Precision@10 computed as `|top10 ∩ ground_truth| / 10`.
3. Full raw ranked output for all 5 methods saved alongside this analysis for reproducibility.
