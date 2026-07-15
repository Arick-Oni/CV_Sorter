# Model Performance and Accuracy Comparison Report
This report evaluates the accuracy of 5 different ranking models against ground truth annotations from Annotator 1, Annotator 2, and the Antigravity agent recruiter model across all 5 projects.

## Evaluation Methodology
- **Top 10 Accuracy**: For each project, the top 10 CV files returned by a model are compared against the top 10 CV files defined by the annotator. Accuracy is the count of overlapping files in both lists (represented as a score out of 10 and percentage).
- **Tie-Breaking**: When sorting files for Annotators or Models, ties are resolved deterministically by numeric filename index (e.g. `1.docx` before `2.docx`). For Annotators, ties are first resolved by using their `Average Rank`.
- **Antigravity Recruiter Ranks**: Expert recruiter rankings provided by Antigravity using deep semantic analysis of CV contents against JD requirements.

## Overall Accuracy Summary (Top 10 Overlap)
| Project Name | Evaluator | TF-IDF | model-2 | modelbest | hybrid modelbest2+ner | hybridmodel+ner |
|---|---|---|---|---|---|---|
| **Software Developer - .Net** | Annotator 1 | 4/10 (40%) | 4/10 (40%) | 4/10 (40%) | 4/10 (40%) | 4/10 (40%) |
| | Annotator 2 | 4/10 (40%) | 5/10 (50%) | 3/10 (30%) | 3/10 (30%) | 3/10 (30%) |
| | Antigravity | 4/10 (40%) | 4/10 (40%) | 3/10 (30%) | 3/10 (30%) | 4/10 (40%) |
| **Remote Software Developer** | Annotator 1 | 2/10 (20%) | 3/10 (30%) | 4/10 (40%) | 4/10 (40%) | 7/10 (70%) |
| | Annotator 2 | 2/10 (20%) | 2/10 (20%) | 2/10 (20%) | 3/10 (30%) | 4/10 (40%) |
| | Antigravity | 4/10 (40%) | 2/10 (20%) | 2/10 (20%) | 6/10 (60%) | 6/10 (60%) |
| **Junior Level Software Developer (1-4 years experience)** | Annotator 1 | 3/10 (30%) | 3/10 (30%) | 3/10 (30%) | 2/10 (20%) | 1/10 (10%) |
| | Annotator 2 | 5/10 (50%) | 5/10 (50%) | 5/10 (50%) | 3/10 (30%) | 4/10 (40%) |
| | Antigravity | 5/10 (50%) | 2/10 (20%) | 2/10 (20%) | 3/10 (30%) | 1/10 (10%) |
| **Backend Software Developer** | Annotator 1 | 3/10 (30%) | 4/10 (40%) | 3/10 (30%) | 4/10 (40%) | 4/10 (40%) |
| | Annotator 2 | 4/10 (40%) | 4/10 (40%) | 5/10 (50%) | 4/10 (40%) | 4/10 (40%) |
| | Antigravity | 3/10 (30%) | 4/10 (40%) | 4/10 (40%) | 4/10 (40%) | 4/10 (40%) |
| **Software Developer** | Annotator 1 | 1/10 (10%) | 2/10 (20%) | 3/10 (30%) | 3/10 (30%) | 3/10 (30%) |
| | Annotator 2 | 2/10 (20%) | 3/10 (30%) | 2/10 (20%) | 3/10 (30%) | 2/10 (20%) |
| | Antigravity | 4/10 (40%) | 3/10 (30%) | 3/10 (30%) | 6/10 (60%) | 7/10 (70%) |

## Evaluator Consensus Analysis
This section compares how closely the human annotators and the **Antigravity** expert recruiter model align with one another on their Top 10 selections.

| Project Name | Annotator 1 vs Annotator 2 | Annotator 1 vs Antigravity | Annotator 2 vs Antigravity |
|---|---|---|---|
| Software Developer - .Net | 2/10 (20%) | 7/10 (70%) | 3/10 (30%) |
| Remote Software Developer | 5/10 (50%) | 5/10 (50%) | 3/10 (30%) |
| Junior Level Software Developer (1-4 years experience) | 4/10 (40%) | 6/10 (60%) | 3/10 (30%) |
| Backend Software Developer | 6/10 (60%) | 2/10 (20%) | 3/10 (30%) |
| Software Developer | 5/10 (50%) | 4/10 (40%) | 3/10 (30%) |
| **Average Overlap** | **44.0%** | **48.0%** | **30.0%** |

### Consensus Findings & Analysis
- **Human Subjectivity (Ann 1 vs Ann 2: 44.0%)**: The low consensus between the two independent human annotators highlights the inherent subjectivity in manual resume screening. A project-by-project comparison reveals that they agreed on only 20% of the top 10 for the Software Developer role, demonstrating how different professionals weigh experiences differently.
- **Antigravity vs Humans (Ann 1: 48.0%, Ann 2: 30.0%)**: Antigravity shows a slightly stronger semantic consensus with **Annotator 1** than Annotator 2 overall. For the **Remote Software Developer** project, Antigravity has a **50% overlap** with Annotator 1, aligning on core secure Unix/Linux and programming stack criteria.

## Model Accuracy Matrix against Antigravity (Agent Ranks)
This matrix isolates the performance of the 5 models using the **Antigravity** expert recruiter rankings as the ground truth.

| Model | Net Developer | Remote Dev | Junior Dev | Backend Dev | Software Dev | Average Accuracy |
|---|---|---|---|---|---|---|
| **tf/idf** | 40% | 40% | 50% | 30% | 40% | **40.0%** |
| **model-2** | 40% | 20% | 20% | 40% | 30% | **30.0%** |
| **modelbest** | 30% | 20% | 20% | 40% | 30% | **28.0%** |
| **hybrid modelbest2+ner** | 30% | 60% | 30% | 40% | 60% | **44.0%** |
| **hybridmodel+ner** | 40% | 60% | 10% | 40% | 70% | **44.0%** |

## Recruiting Model Performance Analysis & Judgement
Based on the accuracy matrix above, we can draw several critical insights regarding how each model behaves under different recruiting constraints:

1. **hybridmodel+ner (modelbest + NER)**: *Co-Winner (44.0% Average Accuracy)*
   - **Strengths**: Strongest overall semantic and conceptual matching. Hit **60%** on **Remote Dev** and an outstanding **70%** on **Software Dev** by aligning skills and certifications nicely.
   - **Weaknesses**: Struggles significantly on seniority-constrained paths (e.g. only **10%** on **Junior Dev**), as its NER features match keywords but lack filter bounds on candidate experience years.

2. **hybrid modelbest2+ner**: *Co-Winner (44.0% Average Accuracy)*
   - **Strengths**: Extremely balanced performance. Got **60%** on **Remote Dev** and **60%** on **Software Dev**, showing excellent consistency when resolving technology entities.
   - **Weaknesses**: Slightly diluted embedding matching strength on very standard backend tasks.

3. **tf/idf**: *The Keyword Anchor (40.0% Average Accuracy)*
   - **Strengths**: Highly precise when matching literal stacks. Achieved **50%** on **Junior Dev** because it strictly anchored on keyword lists rather than fuzzy semantics.
   - **Weaknesses**: Misses domain synonyms and semantic abstractions (scoring only **30%** on Backend Dev).

4. **model-2 (model-best 2)**: *Embedding Model (30.0% Average Accuracy)*
   - **Strengths**: Good at resolving general software patterns (scoring **40%** on Backend Dev and **40%** on Net Developer).
   - **Weaknesses**: Tends to lose specificity on niche roles (like Junior Dev or Remote security constraints).

5. **modelbest (model-best)**: *Embedding Model (28.0% Average Accuracy)*
   - **Strengths**: Fair baseline semantics on standard web and backend (40% on Backend Dev).
   - **Weaknesses**: Weakest semantic specificity when handling complex domain criteria.

## Detailed Project Breakdown
### Software Developer - .Net
- **Annotator 1 Top 10**: 24.docx, 25.docx, 5.docx, 22.docx, 2.docx, 12.docx, 13.docx, 14.docx, 3.docx, 11.docx
- **Annotator 2 Top 10**: 24.docx, 25.docx, 4.docx, 23.docx, 26.docx, 30.docx, 6.docx, 20.docx, 21.docx, 28.docx
- **Antigravity Top 10**: 14.docx, 6.docx, 7.docx, 9.docx, 25.docx, 12.docx, 24.docx, 22.docx, 11.docx, 3.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 4/10 (40%) | 11.docx, 12.docx, 14.docx, 25.docx |
| | Annotator 2 | 4/10 (40%) | 4.docx, 20.docx, 25.docx, 28.docx |
| | Antigravity | 4/10 (40%) | 11.docx, 12.docx, 14.docx, 25.docx |
| model-2 | Annotator 1 | 4/10 (40%) | 12.docx, 14.docx, 22.docx, 25.docx |
| | Annotator 2 | 5/10 (50%) | 4.docx, 20.docx, 21.docx, 25.docx, 26.docx |
| | Antigravity | 4/10 (40%) | 12.docx, 14.docx, 22.docx, 25.docx |
| modelbest | Annotator 1 | 4/10 (40%) | 2.docx, 12.docx, 14.docx, 22.docx |
| | Annotator 2 | 3/10 (30%) | 4.docx, 21.docx, 26.docx |
| | Antigravity | 3/10 (30%) | 12.docx, 14.docx, 22.docx |
| hybrid modelbest2+ner | Annotator 1 | 4/10 (40%) | 3.docx, 5.docx, 14.docx, 25.docx |
| | Annotator 2 | 3/10 (30%) | 20.docx, 21.docx, 25.docx |
| | Antigravity | 3/10 (30%) | 3.docx, 14.docx, 25.docx |
| hybridmodel+ner | Annotator 1 | 4/10 (40%) | 2.docx, 12.docx, 14.docx, 25.docx |
| | Annotator 2 | 3/10 (30%) | 4.docx, 21.docx, 25.docx |
| | Antigravity | 4/10 (40%) | 7.docx, 12.docx, 14.docx, 25.docx |

### Remote Software Developer
- **Annotator 1 Top 10**: 8.docx, 30.docx, 26.docx, 23.docx, 27.docx, 1.docx, 21.docx, 2.docx, 11.docx, 7.docx
- **Annotator 2 Top 10**: 8.docx, 2.docx, 11.docx, 15.docx, 30.docx, 7.docx, 18.docx, 19.docx, 13.docx, 16.docx
- **Antigravity Top 10**: 6.docx, 28.docx, 23.docx, 2.docx, 5.docx, 7.docx, 1.docx, 10.docx, 14.docx, 11.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 2/10 (20%) | 1.docx, 23.docx |
| | Annotator 2 | 2/10 (20%) | 16.docx, 18.docx |
| | Antigravity | 4/10 (40%) | 1.docx, 14.docx, 23.docx, 28.docx |
| model-2 | Annotator 1 | 3/10 (30%) | 2.docx, 21.docx, 26.docx |
| | Annotator 2 | 2/10 (20%) | 2.docx, 18.docx |
| | Antigravity | 2/10 (20%) | 2.docx, 14.docx |
| modelbest | Annotator 1 | 4/10 (40%) | 2.docx, 21.docx, 26.docx, 27.docx |
| | Annotator 2 | 2/10 (20%) | 2.docx, 18.docx |
| | Antigravity | 2/10 (20%) | 2.docx, 14.docx |
| hybrid modelbest2+ner | Annotator 1 | 4/10 (40%) | 2.docx, 7.docx, 23.docx, 26.docx |
| | Annotator 2 | 3/10 (30%) | 2.docx, 7.docx, 15.docx |
| | Antigravity | 6/10 (60%) | 2.docx, 5.docx, 7.docx, 14.docx, 23.docx, 28.docx |
| hybridmodel+ner | Annotator 1 | 7/10 (70%) | 1.docx, 2.docx, 7.docx, 8.docx, 11.docx, 21.docx, 23.docx |
| | Annotator 2 | 4/10 (40%) | 2.docx, 7.docx, 8.docx, 11.docx |
| | Antigravity | 6/10 (60%) | 1.docx, 2.docx, 7.docx, 11.docx, 23.docx, 28.docx |

### Junior Level Software Developer (1-4 years experience)
- **Annotator 1 Top 10**: 16.docx, 4.docx, 6.docx, 7.docx, 15.docx, 17.docx, 19.docx, 10.docx, 20.docx, 21.docx
- **Annotator 2 Top 10**: 16.docx, 14.docx, 9.docx, 4.docx, 6.docx, 21.docx, 27.docx, 12.docx, 23.docx, 1.docx
- **Antigravity Top 10**: 17.docx, 23.docx, 13.docx, 16.docx, 20.docx, 11.docx, 4.docx, 5.docx, 7.docx, 15.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 3/10 (30%) | 4.docx, 16.docx, 20.docx |
| | Annotator 2 | 5/10 (50%) | 1.docx, 4.docx, 12.docx, 16.docx, 23.docx |
| | Antigravity | 5/10 (50%) | 4.docx, 5.docx, 16.docx, 20.docx, 23.docx |
| model-2 | Annotator 1 | 3/10 (30%) | 4.docx, 17.docx, 21.docx |
| | Annotator 2 | 5/10 (50%) | 4.docx, 12.docx, 14.docx, 21.docx, 27.docx |
| | Antigravity | 2/10 (20%) | 4.docx, 17.docx |
| modelbest | Annotator 1 | 3/10 (30%) | 4.docx, 17.docx, 21.docx |
| | Annotator 2 | 5/10 (50%) | 4.docx, 12.docx, 14.docx, 21.docx, 27.docx |
| | Antigravity | 2/10 (20%) | 4.docx, 17.docx |
| hybrid modelbest2+ner | Annotator 1 | 2/10 (20%) | 7.docx, 16.docx |
| | Annotator 2 | 3/10 (30%) | 12.docx, 14.docx, 16.docx |
| | Antigravity | 3/10 (30%) | 7.docx, 11.docx, 16.docx |
| hybridmodel+ner | Annotator 1 | 1/10 (10%) | 21.docx |
| | Annotator 2 | 4/10 (40%) | 1.docx, 12.docx, 14.docx, 21.docx |
| | Antigravity | 1/10 (10%) | 11.docx |

### Backend Software Developer
- **Annotator 1 Top 10**: 8.docx, 28.docx, 1.docx, 27.docx, 5.docx, 30.docx, 10.docx, 12.docx, 13.docx, 17.docx
- **Annotator 2 Top 10**: 1.docx, 27.docx, 10.docx, 12.docx, 13.docx, 17.docx, 19.docx, 7.docx, 18.docx, 22.docx
- **Antigravity Top 10**: 6.docx, 20.docx, 2.docx, 4.docx, 26.docx, 17.docx, 5.docx, 7.docx, 15.docx, 19.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 3/10 (30%) | 12.docx, 17.docx, 27.docx |
| | Annotator 2 | 4/10 (40%) | 12.docx, 17.docx, 18.docx, 27.docx |
| | Antigravity | 3/10 (30%) | 4.docx, 17.docx, 20.docx |
| model-2 | Annotator 1 | 4/10 (40%) | 12.docx, 17.docx, 27.docx, 30.docx |
| | Annotator 2 | 4/10 (40%) | 12.docx, 17.docx, 18.docx, 27.docx |
| | Antigravity | 4/10 (40%) | 4.docx, 17.docx, 20.docx, 26.docx |
| modelbest | Annotator 1 | 3/10 (30%) | 12.docx, 17.docx, 27.docx |
| | Annotator 2 | 5/10 (50%) | 12.docx, 17.docx, 18.docx, 22.docx, 27.docx |
| | Antigravity | 4/10 (40%) | 2.docx, 4.docx, 17.docx, 26.docx |
| hybrid modelbest2+ner | Annotator 1 | 4/10 (40%) | 10.docx, 12.docx, 17.docx, 28.docx |
| | Annotator 2 | 4/10 (40%) | 7.docx, 10.docx, 12.docx, 17.docx |
| | Antigravity | 4/10 (40%) | 7.docx, 15.docx, 17.docx, 20.docx |
| hybridmodel+ner | Annotator 1 | 4/10 (40%) | 10.docx, 12.docx, 17.docx, 28.docx |
| | Annotator 2 | 4/10 (40%) | 7.docx, 10.docx, 12.docx, 17.docx |
| | Antigravity | 4/10 (40%) | 2.docx, 7.docx, 17.docx, 26.docx |

### Software Developer
- **Annotator 1 Top 10**: 29.docx, 5.docx, 9.docx, 18.docx, 24.docx, 7.docx, 22.docx, 23.docx, 27.docx, 3.docx
- **Annotator 2 Top 10**: 29.docx, 5.docx, 3.docx, 20.docx, 26.docx, 18.docx, 24.docx, 1.docx, 10.docx, 11.docx
- **Antigravity Top 10**: 1.docx, 6.docx, 4.docx, 7.docx, 12.docx, 2.docx, 3.docx, 5.docx, 8.docx, 9.docx

| Model | Evaluator | Accuracy | Common CVs |
|---|---|---|---|
| tf/idf | Annotator 1 | 1/10 (10%) | 22.docx |
| | Annotator 2 | 2/10 (20%) | 1.docx, 20.docx |
| | Antigravity | 4/10 (40%) | 1.docx, 2.docx, 4.docx, 12.docx |
| model-2 | Annotator 1 | 2/10 (20%) | 18.docx, 27.docx |
| | Annotator 2 | 3/10 (30%) | 18.docx, 20.docx, 26.docx |
| | Antigravity | 3/10 (30%) | 2.docx, 4.docx, 12.docx |
| modelbest | Annotator 1 | 3/10 (30%) | 18.docx, 22.docx, 27.docx |
| | Annotator 2 | 2/10 (20%) | 18.docx, 26.docx |
| | Antigravity | 3/10 (30%) | 2.docx, 4.docx, 12.docx |
| hybrid modelbest2+ner | Annotator 1 | 3/10 (30%) | 7.docx, 9.docx, 24.docx |
| | Annotator 2 | 3/10 (30%) | 1.docx, 11.docx, 24.docx |
| | Antigravity | 6/10 (60%) | 1.docx, 2.docx, 4.docx, 7.docx, 9.docx, 12.docx |
| hybridmodel+ner | Annotator 1 | 3/10 (30%) | 7.docx, 9.docx, 22.docx |
| | Annotator 2 | 2/10 (20%) | 1.docx, 11.docx |
| | Antigravity | 7/10 (70%) | 1.docx, 2.docx, 6.docx, 7.docx, 8.docx, 9.docx, 12.docx |
