# Design note — Trade Policy QA

**Unit of retrieval:** numbered clause/subclause, not arbitrary token windows. This preserves legal hierarchy and keeps each clause intact.

**Retrieval:** BM25 plus normalized sentence embeddings, merged with reciprocal-rank fusion. BM25 protects exact values, amounts, abbreviations and section numbers; embeddings handle paraphrases.

**Version safety:** status is metadata, not a similarity feature. Superseded clauses remain auditable in the parsed corpus but are excluded before ranking. The 15% Modern Trade value is stored as a Version 1.0 historical record; only current clauses can reach the answer model. For added files, `data/policy_manifest.json` requires an explicit current/superseded designation rather than inferring legal status from similarity or ingestion order.

**Nested rules:** Modern Trade discount questions retrieve Section 3 and 3.1 together. Section 3 contains the channel table and 3.1 contains the revision/effective-current instruction.

**Refusal:** HR topics expressly excluded by Section 1 are refused before generation. Other questions are answered only when retrieved current clauses explicitly support them; Claude is instructed to use no outside knowledge, and citations are checked against retrieved section IDs.

**Rejected:** vector-only search (weak on exact strings); BM25-only search (weak on paraphrases); fixed-size chunking (can detach subclauses); putting the entire document in every prompt (fine for one page, not 200 documents × versions); fine-tuning and deployment (out of scope).

**Caveat:** automated status inference does not scale safely. In a real multi-version corpus, a human-approved ingestion manifest should declare document/version/effective date and supersession relationships.
