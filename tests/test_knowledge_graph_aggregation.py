import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import aggregate_graph_concepts, aggregate_graph_relations, normalize_concept_name


def test_concepts_merge_normalized_names_and_keep_provenance():
    raw = [
        {'id': 10, 'concept_name': ' BLAST ', 'description': 'A', 'concept_type': 'entity', 'frequency': 5,
         'document_id': 1, 'document_title': 'doc-a', 'position_start': 2, 'position_end': 7},
        {'id': 25, 'concept_name': 'blast', 'description': 'B', 'concept_type': 'entity', 'frequency': 3,
         'document_id': 2, 'document_title': 'doc-b', 'position_start': 8, 'position_end': 13},
    ]
    concepts, id_map = aggregate_graph_concepts(raw)
    assert normalize_concept_name(' BLAST ') == 'blast'
    assert len(concepts) == 1
    assert concepts[0]['frequency'] == 8
    assert {d['title'] for d in concepts[0]['source_documents']} == {'doc-a', 'doc-b'}
    assert {d['text'] for d in concepts[0]['descriptions']} == {'A', 'B'}
    assert id_map == {10: concepts[0]['id'], 25: concepts[0]['id']}


def test_relationships_map_deduplicate_and_drop_self_loops():
    relations = [
        {'id': 1, 'from_concept_id': 10, 'to_concept_id': 30, 'relation_type': 'uses', 'confidence': 0.4},
        {'id': 2, 'from_concept_id': 25, 'to_concept_id': 30, 'relation_type': 'uses', 'confidence': 0.9},
        {'id': 3, 'from_concept_id': 10, 'to_concept_id': 25, 'relation_type': 'same', 'confidence': 1.0},
    ]
    result = aggregate_graph_relations(relations, {10: 10, 25: 10, 30: 30})
    assert len(result) == 1
    assert result[0]['from_concept_id'] == 10
    assert result[0]['to_concept_id'] == 30
    assert result[0]['confidence'] == 0.9
    assert result[0]['raw_relation_ids'] == [1, 2]
