import time


def analyze_reading_with_ai_stream(*, file, user):
    time.sleep(2)

    yield {
        "type": "overview",
        "data": {
            "detected_level": "B1",
            "difficulty_profile": {},
            "vocabulary_profile": {},
            "quality_profile": {},
        },
    }

    time.sleep(20)

    yield {
        "type": "section",
        "data": {
            "title": "Section One",
            "order": 1,
            "paragraphs": [
                {
                    "order": 1,
                    "text": "This is the first paragraph.",
                    "meaning": "این پاراگراف اول است.",
                    "tip": "Sample learning tip.",
                    "vocabulary": [],
                    "grammar": [],
                    "phrases": [],
                }
            ],
            "quiz": [],
        },
    }

    time.sleep(20)

    yield {
        "type": "section",
        "data": {
            "title": "Section Two",
            "order": 2,
            "paragraphs": [],
            "quiz": [],
        },
    }