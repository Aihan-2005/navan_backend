from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CEFRLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DifficultyProfile(StrictSchema):
    cefr_level: CEFRLevel
    score: int = Field(description="Difficulty score from 1 (easy) to 10 (hard).")
    sentence_complexity: str
    grammar_complexity: str
    notes_fa: str


class VocabularyProfile(StrictSchema):
    cefr_level: CEFRLevel
    density: Literal["LOW", "MEDIUM", "HIGH"]
    notable_domains: list[str]
    notes_fa: str


class QualityProfile(StrictSchema):
    readability: Literal["POOR", "FAIR", "GOOD", "EXCELLENT"]
    coherence: Literal["POOR", "FAIR", "GOOD", "EXCELLENT"]
    extraction_quality: Literal["POOR", "FAIR", "GOOD", "EXCELLENT"]
    warnings_fa: list[str]


class ReadingOverview(StrictSchema):
    detected_level: CEFRLevel
    title_guess: str
    summary_fa: str
    learning_objectives_fa: list[str]
    difficulty_profile: DifficultyProfile
    vocabulary_profile: VocabularyProfile
    quality_profile: QualityProfile


class VocabularyItem(StrictSchema):
    word: str
    lemma: str
    part_of_speech: str
    cefr_level: CEFRLevel
    meaning_fa: str
    example: str
    example_translation_fa: str


class GrammarItem(StrictSchema):
    title: str
    pattern: str
    explanation_fa: str
    example: str
    example_translation_fa: str


class PhraseItem(StrictSchema):
    phrase: str
    meaning_fa: str
    usage_note_fa: str


class ParagraphAnalysis(StrictSchema):
    order: int
    text: str
    meaning_fa: str
    learning_tip_fa: str
    vocabulary: list[VocabularyItem]
    grammar: list[GrammarItem]
    phrases: list[PhraseItem]


class QuizItem(StrictSchema):
    question_fa: str
    options: list[str]
    correct_option_index: int
    explanation_fa: str


class ReadingSectionAnalysis(StrictSchema):
    title: str
    summary_fa: str
    paragraphs: list[ParagraphAnalysis]
    quiz: list[QuizItem]
