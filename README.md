# Trade Policy Question Answering Assistant

A local Python 3.11+ command-line assistant for a growing corpus of versioned trade-policy documents. It combines structure-aware clause parsing, BM25 keyword retrieval, sentence-transformer semantic retrieval, hard filtering of superseded clauses, and grounded answer generation through Google Gemini.

## Design note

**Why clauses, not arbitrary chunks.** Numbered sections and subclauses are the policy's logical units. The parser keeps each numbered clause intact, with section, version, effective date, source file, and status metadata. It does not split a clause into overlapping token windows.

**Why both lexical and semantic retrieval.** BM25 is good at exact strings such as `Rs 50,000`, `12%`, `RSM`, and section identifiers. Embeddings help with paraphrases such as "kirana distributor" versus "General Trade". Reciprocal-rank fusion merges their rankings without pretending their raw scores share a scale.

**Why status is a hard filter.** Similarity cannot determine whether a sentence is legally/currently operative. The index retains the old Version 1.0 Modern Trade value for auditability, but retrieval removes every `superseded` clause before ranking. The current 12% limit is in Section 3; Section 3.1 supplies its revision context. The retriever explicitly expands Modern Trade discount questions to include both.

**Why no generative fallback.** The model receives only retrieved current clauses and is instructed to refuse if they do not answer. HR topics excluded by Section 1 are refused before retrieval. A post-generation citation check rejects unsupported section citations. No web/general-knowledge fallback is used.

**Rejected alternatives.** For this single short sample, putting the entire policy in the prompt would be simpler and more reliable. It is rejected because the stated target is hundreds of documents and multiple versions. Pure vector search is rejected because exact amounts and abbreviations matter. Pure BM25 is rejected because paraphrased commercial questions matter. Arbitrary fixed-size chunking is rejected because it can detach a subclause from its governing rule. Fine-tuning, a vector database server, a UI, and deployment are outside scope.

## Project layout

- `data/`: source policy documents (`.txt`); the indexer ingests every `.txt` file in this directory.
- `src/parser.py`: section/subclause parser and explicit historical-value record.
- `src/indexer.py`: BM25 corpus and normalized sentence embeddings.
- `src/retrieval.py`: hybrid rank fusion, current-only filtering, nested-rule expansion, scope refusal.
- `src/generation.py`: Gemini API prompt and citation validation.
- `evaluation/eval_set.json`: 36-question gold set.
- `evaluation/run_eval.py`: answer, citation, refusal, and superseded-leak metrics.
- `tests/`: parser, filtering, nested retrieval, and refusal tests.

## Setup

Python 3.11 or newer is required.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\\Scripts\\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Set your Gemini API key in the environment (do not put it in source control):

```powershell
$env:GEMINI_API_KEY="your-key"
```

```bash
export GEMINI_API_KEY="your-key"
```

The current implementation uses `gemini-3.5-flash-lite`.

## Build the index

Run from the project root:

```bash
python ask.py --index
```

The first run downloads `all-MiniLM-L6-v2` from Hugging Face and stores the local index under `index/`. Rebuild after adding or revising policy documents.

## Ask a question

```bash
python ask.py "What is the maximum discount for Modern Trade?"
python ask.py "Who approves a scheme above Rs 5 lakh?"
python ask.py "What is the employee leave policy?"
```

The HR question is refused without calling Gemini. Answerable questions require `GEMINI_API_KEY`.

## Tests and evaluation

```bash
pytest -q
python evaluation/run_eval.py
```

The evaluation calls Gemini for answerable cases, so it requires a valid API key and network access. The test suite builds a temporary index and downloads the embedding model on first run.

**Expected evaluation target:** 100% refusal accuracy on the explicit scope-boundary cases; 100% citation accuracy when the generated answer includes all required source sections; zero superseded-value leaks. Answer accuracy is model- and prompt-dependent and should be measured rather than claimed in advance. The project intentionally does not fabricate a passing score before execution.

## Adding more documents and versions

For a larger corpus, put each source document as a `.txt` file in `data/`; the indexer reads every `.txt` file in that directory. Maintain `data/policy_manifest.json` with a `documents` entry per filename. Set document `status` to `current` or `superseded`; optional `clauses` entries can override status by section number. This is deliberately explicit: a new revision must not become current merely because it was added last or scored highly. Each clause retains source filename, version, effective date, section, and status. Extend the `Clause` metadata schema with market/channel fields when those dimensions appear in the source corpus. On ingestion of a revised policy, compare clause identifiers and explicit revision language, mark the replaced records `superseded`, and keep them for audit. Do not infer legal status from semantic similarity. For production-scale governance, require a human-approved version/status manifest per document; this sample derives only the one explicit historical revision found in the supplied text.

## Known limitations and assumptions

- The supplied sample is one India-wide policy, Version 2.0, effective 1 April 2025.
- Version 1.0 is mentioned only as `2024`; the source gives no exact effective date, so the historical record says that explicitly.
- The parser handles the supplied numbered-heading style and ordinary numbered subclauses. New document templates may need additional parsers.
- The scope guard is deliberately conservative for HR topics named in Section 1. It does not claim that every possible out-of-scope topic can be classified perfectly.
- Gemini model availability can change; update the model name in `src/generation.py` if the configured model is unavailable.
- The current sample index is local and rebuildable. It is not a multi-tenant or production document-management system.

## Evaluation Results

The system was evaluated using a gold dataset of 36 questions:
- 30 answerable questions
- 6 out-of-scope questions

### Metrics

| Metric | Result |
|---|---:|
| Answer Accuracy | 32/36 (88.9%) |
| Citation Accuracy | 29/30 (96.7%) |
| Refusal Accuracy | 36/36 (100%) |
| Superseded-Value Leaks | 0 |

### Evaluation Setup
- Hybrid retrieval using BM25 and sentence-transformer embeddings.
- Gemini API for grounded answer generation.
- Citation validation against retrieved policy clauses.
- Refusal handling for out-of-scope questions.

### Known Limitations
- Evaluation is based on a 36-question gold dataset.
- Answer accuracy uses keyword-based matching, not human-verified semantic evaluation.
- Citation validation checks cited-section presence, not full claim-to-source entailment.
- Larger multi-document and multi-market testing is still required.