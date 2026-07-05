"""Tests for COG conversation understanding NER module."""

from __future__ import annotations

from ayeneh.cog.conversation.ner import EntityRecognizer


# ---------------------------------------------------------------------------
# EntityRecognizer tests
# ---------------------------------------------------------------------------


class TestEntityRecognizer:
    def setup_method(self):
        self.recognizer = EntityRecognizer()

    def test_extract_person_full_name(self):
        entities = self.recognizer.recognize('Alice Johnson went to the store.')
        person_entities = [e for e in entities if e['type'] == 'person']
        assert len(person_entities) >= 1
        assert any('Alice Johnson' in e['text'] for e in person_entities)

    def test_extract_person_with_title(self):
        entities = self.recognizer.recognize('Mr. Smith is a teacher.')
        person_entities = [e for e in entities if e['type'] == 'person']
        assert len(person_entities) >= 1
        assert any('Mr. Smith' in e['text'] for e in person_entities)

    def test_extract_kinship(self):
        entities = self.recognizer.recognize('My mother is very kind.')
        kinship = [e for e in entities if e['type'] == 'kinship']
        assert len(kinship) >= 1
        assert any('my mother' in e['text'].lower() for e in kinship)

    def test_extract_organization(self):
        entities = self.recognizer.recognize('She works at Google Inc.')
        org_entities = [e for e in entities if e['type'] == 'organization']
        assert len(org_entities) >= 1
        assert any('Google Inc' in e['text'] for e in org_entities)

    def test_extract_organization_team(self):
        entities = self.recognizer.recognize('The Marketing Team met today.')
        org_entities = [e for e in entities if e['type'] == 'organization']
        assert len(org_entities) >= 1

    def test_extract_location_in(self):
        entities = self.recognizer.recognize('I live in Paris.')
        loc_entities = [e for e in entities if e['type'] == 'location']
        assert len(loc_entities) >= 1
        assert any('Paris' in e['text'] for e in loc_entities)

    def test_extract_location_at(self):
        entities = self.recognizer.recognize('She is at New York now.')
        loc_entities = [e for e in entities if e['type'] == 'location']
        assert len(loc_entities) >= 1
        assert any('New York' in e['text'] for e in loc_entities)

    def test_extract_location_city_of(self):
        entities = self.recognizer.recognize('The city of London is beautiful.')
        loc_entities = [e for e in entities if e['type'] == 'location']
        assert len(loc_entities) >= 1
        assert any('London' in e['text'] for e in loc_entities)

    def test_deduplication(self):
        entities = self.recognizer.recognize('Alice Johnson met Alice Johnson.')
        person_entities = [e for e in entities if e['type'] == 'person']
        # Should be deduplicated
        alice_matches = [e for e in person_entities if 'Alice Johnson' in e['text']]
        assert len(alice_matches) == 1

    def test_multiple_entity_types(self):
        entities = self.recognizer.recognize(
            'Mr. Smith went to Google Inc in Paris.'
        )
        types = {e['type'] for e in entities}
        assert 'person' in types
        assert 'organization' in types
        assert 'location' in types

    def test_no_entities(self):
        entities = self.recognizer.recognize('hello world')
        person_entities = [e for e in entities if e['type'] == 'person']
        org_entities = [e for e in entities if e['type'] == 'organization']
        assert len(person_entities) == 0
        assert len(org_entities) == 0

    def test_empty_text(self):
        entities = self.recognizer.recognize('')
        assert entities == []

    def test_entities_have_offsets(self):
        entities = self.recognizer.recognize('Alice Johnson is here.')
        for ent in entities:
            assert 'start' in ent
            assert 'end' in ent
            assert ent['start'] >= 0
            assert ent['end'] > ent['start']
