# Knowledge Graph Deduplication and Provenance Improvement Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make concepts with the same meaning merge predictably across documents while preserving all source documents, descriptions, positions, and relationships in the knowledge graph.

**Architecture:** Keep raw concept-extraction records unchanged as provenance data. Add a normalized concept key and an aggregation layer for graph presentation. The graph API will return one display node per normalized concept, complete source-document metadata, aggregated frequency, and deduplicated non-self relationships.

**Tech Stack:** Flask, Jinja2, MySQL via `mysql.connector`, D3.js, Python standard library.

---

## Current behavior and confirmed limitations

The current teacher graph route is `app.py:6760-7012`.

- It groups concepts by the exact `concept_name` string (`app.py:6811-6836`).
- It accumulates frequency and recalculates node size.
- It keeps only the first record's description, document ID, document title, and position.
- It maps original concept IDs to the first record's ID (`app.py:6838-6844`).
- It removes relationships that become self-loops after merging (`app.py:6875-6882`).
- The current model cannot distinguish meaningful equivalents such as `BLAST`, `blast`, and `BLAST `.
- One merged node cannot currently show all source documents or all source positions.

Relevant schema: `myscripts/config_modules/my_config.py:307-330`.

## Proposed behavior

1. Preserve every raw `knowledge_concepts` row.
2. Compute a deterministic normalized key:
   - Unicode normalize with NFKC.
   - Trim leading/trailing whitespace.
   - Collapse internal whitespace.
   - Case-fold Latin text.
   - Keep Chinese characters unchanged apart from Unicode normalization.
3. Group display nodes by normalized key, not raw spelling.
4. Select a canonical display name deterministically:
   - Prefer the most frequent spelling.
   - Break ties by first-seen concept ID.
5. Aggregate:
   - Total frequency.
   - Maximum/display size derived from total frequency.
   - All distinct source documents.
   - All non-empty descriptions, with source document attribution.
   - All source positions.
   - Distinct raw concept IDs.
6. Map every raw concept ID to its aggregate display node ID.
7. Transform relationships after mapping:
   - Remove self-loops.
   - Deduplicate identical source-target-relation-type pairs.
   - Keep maximum confidence for duplicates.
   - Preserve a count/list of contributing raw relationship IDs.
8. Expose both `concept_name` and `normalized_name`/`source_documents` to the template.
9. Show provenance in the node tooltip and concept detail panel.
10. Do not fabricate test nodes or test relationships in production graph routes.

---

## Task 1: Add pure normalization and aggregation helpers

**Objective:** Implement testable Python helpers without changing database behavior.

**Files:**
- Modify: `app.py` near the existing graph conversion helpers (`app.py:6747-6758`)
- Test: create `tests/test_knowledge_graph_aggregation.py` if no test directory exists

**Step 1: Write failing tests**

Test at minimum:

- `BLAST`, `blast`, and ` BLAST ` produce the same normalized key.
- Chinese whitespace variants normalize identically.
- Canonical display spelling is deterministic.
- Frequency sums across raw records.
- All source documents, descriptions, positions, and raw IDs are retained.
- A relationship between two spelling variants of the same concept becomes a self-loop and is removed.
- Duplicate mapped relationships retain maximum confidence and one aggregate record.

**Step 2: Run the tests**

Run:

```bash
.venv-hermes/bin/python -m pytest tests/test_knowledge_graph_aggregation.py -q
```

Expected: FAIL because the helpers do not exist.

**Step 3: Implement the minimum helpers**

Recommended helper contracts:

```python
def normalize_concept_name(name: str) -> str:
    """Return a stable comparison key for a concept name."""


def aggregate_graph_concepts(raw_concepts: list[dict]) -> tuple[list[dict], dict]:
    """Return display nodes and raw-id -> display-id mapping."""


def aggregate_graph_relations(raw_relations: list[dict], concept_id_map: dict) -> list[dict]:
    """Map, remove self-loops, and deduplicate graph relationships."""
```

The helper output should include fields such as:

```text
id
concept_name
normalized_name
frequency
size
source_documents: [{id, title, frequency}]
descriptions: [{text, document_id, document_title}]
positions: [{document_id, start, end}]
raw_concept_ids
```

**Step 4: Run the tests again**

Expected: PASS.

---

## Task 2: Replace teacher graph route's exact-name merge

**Objective:** Make `/teacher/knowledge_bases/<kb_id>/graph` use the new aggregation logic.

**Files:**
- Modify: `app.py:6811-6897`
- Test: extend `tests/test_knowledge_graph_aggregation.py`

**Step 1: Add a route-level regression test**

Use a small deterministic fixture or monkeypatched database cursor containing two documents with:

```text
BLAST / blast / BLAST 
```

Assert that the rendered graph data contains one display node, combined frequency, and all source documents.

**Step 2: Run the test to verify it fails**

```bash
.venv-hermes/bin/python -m pytest tests/test_knowledge_graph_aggregation.py -q
```

Expected: FAIL because the route currently groups exact strings and discards provenance.

**Step 3: Implement the route change**

- Keep the existing raw concept query.
- Pass `raw_concepts` to `aggregate_graph_concepts`.
- Keep the returned `concept_id_map`.
- Pass raw relation rows to `aggregate_graph_relations`.
- Remove the old inline exact-name merge and relationship cleanup code.
- Keep frequency sorting and Decimal/datetime conversion.
- Preserve empty-state behavior with no test data.

**Step 4: Run the regression test**

Expected: PASS.

---

## Task 3: Add provenance-aware graph UI

**Objective:** Let teachers understand where a merged concept came from.

**Files:**
- Modify: `templates/teacher/knowledge_graph.html:437-1134`
- Optional modify: `templates/student/knowledge_graph.html`

**Step 1: Add failing browser/HTML assertions**

Assert that rendered graph data includes:

- `source_documents`
- `descriptions`
- `positions`
- `raw_concept_ids`

Assert that the tooltip does not rely on a single `docTitleMap[document_id]` value.

**Step 2: Implement concise provenance display**

Update the node model and tooltip to show:

```text
概念：BLAST
频率：8
来源文档：2
来源：文档 A、文档 B
```

On click or in the side panel, show the full source-document list and descriptions. Keep the graph readable by showing only a compact summary in the tooltip and details in a panel/modal.

Avoid exposing raw JSON in the visible UI.

**Step 3: Verify manually and with an HTTP fixture**

- Open the teacher graph route for a knowledge base containing duplicate concepts.
- Confirm one node is displayed.
- Confirm tooltip/panel lists all source documents.
- Confirm no JavaScript reference errors.

---

## Task 4: Improve manual concept insertion and duplicate handling

**Objective:** Prevent manually added concepts from creating avoidable duplicates.

**Files:**
- Modify: `app.py:8402-8485` (manual concept add route)
- Modify: `templates/teacher/knowledge_graph.html` modal code
- Test: `tests/test_knowledge_graph_aggregation.py`

**Step 1: Write failing tests**

Test that adding a manually entered concept whose normalized key already exists:

- Does not create an accidental visually separate graph node.
- Returns a clear message such as “已存在同名概念，将补充到现有概念来源” or rejects the duplicate according to the chosen policy.

**Step 2: Choose and document policy**

Recommended policy: retain a separate raw record only when it comes from a different document/extraction event, but aggregate it in the graph. For manual insertion into a knowledge base, reject an exact normalized duplicate in the same document with HTTP 409 and a clear message.

**Step 3: Implement validation**

- Normalize the submitted name.
- Query existing concepts for the target document.
- Compare normalized keys in Python.
- Return a conflict response for same-document duplicates.
- Continue to permit a concept with the same meaning in a different document; the graph aggregator will merge it visually and preserve provenance.

**Step 4: Verify**

Test same-document duplicate, cross-document duplicate, and genuinely different concept names.

---

## Task 5: Add schema/index support only if profiling justifies it

**Objective:** Keep the improvement safe for the current database while preparing for larger knowledge bases.

**Files:**
- Modify: `myscripts/config_modules/my_config.py:307-330`
- Add: a small idempotent migration helper if needed

**Recommended initial approach:** Do not add a stored normalized column immediately. The graph route can normalize the already-fetched concept names in Python, which avoids a schema migration and keeps raw data unchanged.

If the concept table becomes large and route profiling shows the Python grouping is too slow:

- Add `normalized_name VARCHAR(191)`.
- Backfill it using the same normalization implementation or a controlled migration script.
- Add an index on `(knowledge_document_id, normalized_name)`.
- Ensure the application writes the normalized value on extraction/manual insertion.
- Verify migration is idempotent and never deletes raw records.

---

## Task 6: End-to-end verification

**Objective:** Prove the graph is correct for teachers, administrators, and students.

**Files:**
- Test: `tests/test_knowledge_graph_aggregation.py`
- Verify: `app.py`, `templates/teacher/knowledge_graph.html`, `templates/student/knowledge_graph.html`

Run:

```bash
python3 -m py_compile app.py
.venv-hermes/bin/python -m pytest tests/test_knowledge_graph_aggregation.py -q
```

Then verify live routes with an authenticated admin/teacher session:

```text
GET /teacher/knowledge_bases/<kb_id>/graph → HTTP 200
```

Acceptance criteria:

- Same normalized concept across two documents creates one display node.
- Total frequency equals the sum of raw concept frequencies.
- All source documents are visible in provenance details.
- Different descriptions are retained and attributed to their source documents.
- All source positions are retained.
- Relationships map to aggregate nodes.
- Self-loops are removed.
- Duplicate relationships are collapsed with maximum confidence.
- Empty knowledge bases show an honest empty state, not fake nodes/edges.
- Admin, teacher, and student graph routes show the correct knowledge base data and do not leak private knowledge bases.
- Browser console contains no graph initialization errors.

---

## Risks and trade-offs

- Aggressive normalization can merge distinct biological entities whose names differ only by case or whitespace. Use exact Unicode/case/whitespace normalization first; do not add synonym dictionaries without domain review.
- Canonical spelling selection must be deterministic so graph labels do not change between requests.
- Aggregating relationships may hide the fact that two documents asserted the same relation. Preserve contributing relationship IDs/counts in the response for traceability.
- Retaining raw rows preserves provenance but may increase response payload size. Limit the UI detail list or paginate only if real data requires it.
- The current application has duplicated/legacy graph routes (`/teacher/knowledge_bases/<kb_id>/graph`, `/teacher/kg/<kb_id>`, and student graph routes). The main teacher route should be fixed first; legacy routes should either delegate to the same aggregation helpers or be clearly marked as diagnostic/deprecated.

## Open questions

- Should `BLAST` and `blast` always merge, or should biological symbol case be significant for selected concept types?
- Should concepts with known aliases/synonyms merge? If yes, define a curated alias table rather than fuzzy matching.
- Should students see full concept provenance, or only source-document titles?
- Should the graph display one aggregate node per normalized name, or optionally offer a “按文档拆分节点” view?
