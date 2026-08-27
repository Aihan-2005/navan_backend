from django.test import SimpleTestCase
from pydantic import ValidationError

from apps.reading.schemas import (
    ReadingSectionAnalysis,
    VocabularyItem,
)


class ReadingSchemaTests(SimpleTestCase):
    def test_extra_fields_rejected(
        self,
    ):
        with self.assertRaises(ValidationError):
            ReadingSectionAnalysis(
                title="Section",
                summary_fa="Summary",
                paragraphs=[],
                quiz=[],
                unexpected="should fail",
            )

    def test_invalid_cefr_rejected(
        self,
    ):
        with self.assertRaises(ValidationError):
            VocabularyItem(
                word="hello",
                lemma="hello",
                part_of_speech=("interjection"),
                cefr_level="Z9",
                meaning_fa="سلام",
                example="Hello there",
                example_translation_fa=("سلام"),
            )
