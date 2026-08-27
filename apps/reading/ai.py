from .ai_client import StructuredAIResult, get_reading_ai_client
from .chunking import build_overview_sample
from .prompts import (
    READING_SYSTEM_PROMPT,
    build_overview_prompt,
    build_section_prompt,
)
from .schemas import (
    ReadingOverview,
    ReadingSectionAnalysis,
)


def analyze_reading_overview(
    *,
    text: str,
    learner_level: str,
) -> StructuredAIResult[ReadingOverview]:
    sample = build_overview_sample(text)

    return get_reading_ai_client().parse(
        schema=ReadingOverview,
        instructions=READING_SYSTEM_PROMPT,
        input_text=build_overview_prompt(
            sample=sample,
            learner_level=learner_level,
        ),
    )


def analyze_reading_section(
    *,
    text: str,
    learner_level: str,
    section_order: int,
) -> StructuredAIResult[ReadingSectionAnalysis]:
    return get_reading_ai_client().parse(
        schema=ReadingSectionAnalysis,
        instructions=READING_SYSTEM_PROMPT,
        input_text=build_section_prompt(
            text=text,
            learner_level=learner_level,
            section_order=section_order,
        ),
    )
