# Model Performance and Accuracy Comparison Report

This report evaluates the accuracy of 6 different ranking models against ground truth annotations from Annotator 1 and Annotator 2 across all 5 projects.

## Evaluation Methodology
- **Top 10 Accuracy**: For each project, the top 10 CV files returned by a model are compared against the top 10 CV files defined by the annotator. Accuracy is the count of overlapping files in both lists (represented as a score out of 10 and percentage).
- **Tie-Breaking**: When sorting files for Annotators or Models, ties are resolved deterministically by numeric filename index (e.g. `1.docx` before `2.docx`). For Annotators, ties are first resolved by using their `Average Rank`.

---

## Overall Accuracy Summary (Top 10 Overlap)

| Project Name | Evaluator | TF-IDF | model-2 (Zaima Apu) | modelbest (Moushumi Apu) | hybrid modelbest 2 (Zaima Apu)2+ner | hybridmodel(Moushumi Apu)+ner | gemma3:12b (LLM Rubric) |
|---|---|---|---|---|---|---|---|
| **Software Developer - .Net** | Annotator 1 | 4/10 (40%) | 4/10 (40%) | 5/10 (50%) | 3/10 (30%) | 3/10 (30%) | 3/10 (30%) |
| | Annotator 2 | 4/10 (40%) | 5/10 (50%) | 3/10 (30%) | 3/10 (30%) | 3/10 (30%) | 2/10 (20%) |
| **Remote Software Developer** | Annotator 1 | 5/10 (50%) | 4/10 (40%) | 4/10 (40%) | 5/10 (50%) | 4/10 (40%) | 5/10 (50%) |
| | Annotator 2 | 3/10 (30%) | 3/10 (30%) | 3/10 (30%) | 3/10 (30%) | 2/10 (20%) | 1/10 (10%) |
| **Junior Level Software Developer (1-4 years experience)** | Annotator 1 | 2/10 (20%) | 2/10 (20%) | 2/10 (20%) | 1/10 (10%) | 1/10 (10%) | 2/10 (20%) |
| | Annotator 2 | 4/10 (40%) | 4/10 (40%) | 4/10 (40%) | 2/10 (20%) | 3/10 (30%) | 6/10 (60%) |
| **Backend Software Developer** | Annotator 1 | 2/10 (20%) | 3/10 (30%) | 3/10 (30%) | 1/10 (10%) | 2/10 (20%) | 3/10 (30%) |
| | Annotator 2 | 3/10 (30%) | 3/10 (30%) | 4/10 (40%) | 5/10 (50%) | 5/10 (50%) | 4/10 (40%) |
| **Software Developer** | Annotator 1 | 2/10 (20%) | 2/10 (20%) | 3/10 (30%) | 4/10 (40%) | 4/10 (40%) | 2/10 (20%) |
| | Annotator 2 | 3/10 (30%) | 3/10 (30%) | 2/10 (20%) | 3/10 (30%) | 2/10 (20%) | 3/10 (30%) |

## Visual Comparison Charts

### Annotator 1 (Moushumi Apu) Comparison
![Annotator 1 Comparison](annotator1_comparison.png)

### Annotator 2 (Zaima Apu) Comparison
![Annotator 2 Comparison](annotator2_comparison.png)

---

## Evaluator Consensus Analysis

This section compares how closely the two independent human annotators align with one another on their Top 10 selections.

| Project Name | Annotator 1 vs Annotator 2 |
|---|---|
| Software Developer - .Net | 0/10 (0%) |
| Remote Software Developer | 3/10 (30%) |
| Junior Level Software Developer (1-4 years experience) | 4/10 (40%) |
| Backend Software Developer | 3/10 (30%) |
| Software Developer | 4/10 (40%) |
| **Average Overlap** | **28.000000000000004**% |

## Detailed Project Breakdown

### Software Developer - .Net

- **Annotator 1 Top 10**: 2.docx, 3.docx, 5.docx, 9.docx, 11.docx, 12.docx, 13.docx, 14.docx, 18.docx, 22.docx
- **Annotator 2 Top 10**: 4.docx, 6.docx, 20.docx, 21.docx, 23.docx, 24.docx, 25.docx, 26.docx, 28.docx, 30.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 4/10 (40%) | 11.docx, 12.docx, 14.docx, 18.docx |
| | Annotator 2 | 4/10 (40%) | 4.docx, 20.docx, 25.docx, 28.docx |
| model-2 (Zaima Apu) | Annotator 1 | 4/10 (40%) | 12.docx, 14.docx, 18.docx, 22.docx |
| | Annotator 2 | 5/10 (50%) | 4.docx, 20.docx, 21.docx, 25.docx, 26.docx |
| modelbest (Moushumi Apu) | Annotator 1 | 5/10 (50%) | 2.docx, 12.docx, 14.docx, 18.docx, 22.docx |
| | Annotator 2 | 3/10 (30%) | 4.docx, 21.docx, 26.docx |
| hybrid modelbest 2 (Zaima Apu)2+ner | Annotator 1 | 3/10 (30%) | 3.docx, 5.docx, 14.docx |
| | Annotator 2 | 3/10 (30%) | 20.docx, 21.docx, 25.docx |
| hybridmodel(Moushumi Apu)+ner | Annotator 1 | 3/10 (30%) | 2.docx, 12.docx, 14.docx |
| | Annotator 2 | 3/10 (30%) | 4.docx, 21.docx, 25.docx |
| gemma3:12b (LLM Rubric) | Annotator 1 | 3/10 (30%) | 3.docx, 12.docx, 14.docx |
| | Annotator 2 | 2/10 (20%) | 25.docx, 26.docx |

---

### Remote Software Developer

- **Annotator 1 Top 10**: 1.docx, 4.docx, 15.docx, 16.docx, 17.docx, 23.docx, 26.docx, 29.docx, 30.docx, 2.docx
- **Annotator 2 Top 10**: 5.docx, 10.docx, 22.docx, 29.docx, 7.docx, 13.docx, 16.docx, 17.docx, 18.docx, 19.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 5/10 (50%) | 1.docx, 4.docx, 16.docx, 23.docx, 29.docx |
| | Annotator 2 | 3/10 (30%) | 16.docx, 18.docx, 29.docx |
| model-2 (Zaima Apu) | Annotator 1 | 4/10 (40%) | 2.docx, 4.docx, 17.docx, 26.docx |
| | Annotator 2 | 3/10 (30%) | 17.docx, 18.docx, 22.docx |
| modelbest (Moushumi Apu) | Annotator 1 | 4/10 (40%) | 2.docx, 4.docx, 17.docx, 26.docx |
| | Annotator 2 | 3/10 (30%) | 17.docx, 18.docx, 22.docx |
| hybrid modelbest 2 (Zaima Apu)2+ner | Annotator 1 | 5/10 (50%) | 2.docx, 15.docx, 17.docx, 23.docx, 26.docx |
| | Annotator 2 | 3/10 (30%) | 5.docx, 7.docx, 17.docx |
| hybridmodel(Moushumi Apu)+ner | Annotator 1 | 4/10 (40%) | 1.docx, 2.docx, 23.docx, 29.docx |
| | Annotator 2 | 2/10 (20%) | 7.docx, 29.docx |
| gemma3:12b (LLM Rubric) | Annotator 1 | 5/10 (50%) | 1.docx, 2.docx, 4.docx, 23.docx, 26.docx |
| | Annotator 2 | 1/10 (10%) | 5.docx |

---

### Junior Level Software Developer (1-4 years experience)

- **Annotator 1 Top 10**: 6.docx, 7.docx, 10.docx, 19.docx, 20.docx, 21.docx, 4.docx, 9.docx, 13.docx, 15.docx
- **Annotator 2 Top 10**: 1.docx, 27.docx, 3.docx, 4.docx, 5.docx, 6.docx, 9.docx, 10.docx, 12.docx, 14.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 2/10 (20%) | 4.docx, 20.docx |
| | Annotator 2 | 4/10 (40%) | 1.docx, 4.docx, 5.docx, 12.docx |
| model-2 (Zaima Apu) | Annotator 1 | 2/10 (20%) | 4.docx, 21.docx |
| | Annotator 2 | 4/10 (40%) | 4.docx, 12.docx, 14.docx, 27.docx |
| modelbest (Moushumi Apu) | Annotator 1 | 2/10 (20%) | 4.docx, 21.docx |
| | Annotator 2 | 4/10 (40%) | 4.docx, 12.docx, 14.docx, 27.docx |
| hybrid modelbest 2 (Zaima Apu)2+ner | Annotator 1 | 1/10 (10%) | 7.docx |
| | Annotator 2 | 2/10 (20%) | 12.docx, 14.docx |
| hybridmodel(Moushumi Apu)+ner | Annotator 1 | 1/10 (10%) | 21.docx |
| | Annotator 2 | 3/10 (30%) | 1.docx, 12.docx, 14.docx |
| gemma3:12b (LLM Rubric) | Annotator 1 | 2/10 (20%) | 4.docx, 6.docx |
| | Annotator 2 | 6/10 (60%) | 1.docx, 4.docx, 5.docx, 6.docx, 12.docx, 27.docx |

---

### Backend Software Developer

- **Annotator 1 Top 10**: 8.docx, 9.docx, 5.docx, 28.docx, 1.docx, 18.docx, 30.docx, 2.docx, 3.docx, 4.docx
- **Annotator 2 Top 10**: 2.docx, 7.docx, 8.docx, 9.docx, 12.docx, 13.docx, 14.docx, 15.docx, 16.docx, 17.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 2/10 (20%) | 4.docx, 18.docx |
| | Annotator 2 | 3/10 (30%) | 12.docx, 14.docx, 17.docx |
| model-2 (Zaima Apu) | Annotator 1 | 3/10 (30%) | 4.docx, 18.docx, 30.docx |
| | Annotator 2 | 3/10 (30%) | 12.docx, 14.docx, 17.docx |
| modelbest (Moushumi Apu) | Annotator 1 | 3/10 (30%) | 2.docx, 4.docx, 18.docx |
| | Annotator 2 | 4/10 (40%) | 2.docx, 12.docx, 14.docx, 17.docx |
| hybrid modelbest 2 (Zaima Apu)2+ner | Annotator 1 | 1/10 (10%) | 28.docx |
| | Annotator 2 | 5/10 (50%) | 7.docx, 12.docx, 14.docx, 15.docx, 17.docx |
| hybridmodel(Moushumi Apu)+ner | Annotator 1 | 2/10 (20%) | 2.docx, 28.docx |
| | Annotator 2 | 5/10 (50%) | 2.docx, 7.docx, 12.docx, 14.docx, 17.docx |
| gemma3:12b (LLM Rubric) | Annotator 1 | 3/10 (30%) | 1.docx, 2.docx, 5.docx |
| | Annotator 2 | 4/10 (40%) | 2.docx, 12.docx, 14.docx, 16.docx |

---

### Software Developer

- **Annotator 1 Top 10**: 27.docx, 5.docx, 29.docx, 7.docx, 9.docx, 18.docx, 22.docx, 23.docx, 24.docx, 1.docx
- **Annotator 2 Top 10**: 3.docx, 11.docx, 18.docx, 1.docx, 21.docx, 24.docx, 5.docx, 10.docx, 20.docx, 25.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 2/10 (20%) | 1.docx, 22.docx |
| | Annotator 2 | 3/10 (30%) | 1.docx, 20.docx, 21.docx |
| model-2 (Zaima Apu) | Annotator 1 | 2/10 (20%) | 18.docx, 27.docx |
| | Annotator 2 | 3/10 (30%) | 18.docx, 20.docx, 21.docx |
| modelbest (Moushumi Apu) | Annotator 1 | 3/10 (30%) | 18.docx, 22.docx, 27.docx |
| | Annotator 2 | 2/10 (20%) | 18.docx, 21.docx |
| hybrid modelbest 2 (Zaima Apu)2+ner | Annotator 1 | 4/10 (40%) | 1.docx, 7.docx, 9.docx, 24.docx |
| | Annotator 2 | 3/10 (30%) | 1.docx, 11.docx, 24.docx |
| hybridmodel(Moushumi Apu)+ner | Annotator 1 | 4/10 (40%) | 1.docx, 7.docx, 9.docx, 22.docx |
| | Annotator 2 | 2/10 (20%) | 1.docx, 11.docx |
| gemma3:12b (LLM Rubric) | Annotator 1 | 2/10 (20%) | 1.docx, 5.docx |
| | Annotator 2 | 3/10 (30%) | 1.docx, 3.docx, 5.docx |

---
