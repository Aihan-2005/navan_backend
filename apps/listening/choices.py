from django.db import models


class CefrLevel(models.TextChoices):
    A1 = "A1", "A1"
    A2 = "A2", "A2"
    B1 = "B1", "B1"
    B2 = "B2", "B2"
    C1 = "C1", "C1"
    C2 = "C2", "C2"


class ListeningContentType(models.TextChoices):
    PODCAST = "podcast", "Podcast"
    CONVERSATION = "conversation", "Conversation"
    STORY = "story", "Story"
    NEWS = "news", "News"
    INTERVIEW = "interview", "Interview"
    LECTURE = "lecture", "Lecture"
    EXAM = "exam", "Exam"
    CUSTOM = "custom", "Custom"


class ListeningSourceType(models.TextChoices):
    PLATFORM = "platform", "Platform"
    USER_UPLOAD = "user_upload", "User upload"
    EXTERNAL_URL = "external_url", "External URL"


class ListeningPracticeMode(models.TextChoices):
    FULL_DICTATION = "full_dictation", "Full dictation"
    GUIDED_DICTATION = "guided_dictation", "Guided dictation"
    FILL_IN_THE_BLANK = "fill_in_the_blank", "Fill in the blank"
    COMPREHENSION = "comprehension", "Comprehension"
    SHADOWING = "shadowing", "Shadowing"


class ListeningAccent(models.TextChoices):
    AMERICAN = "american", "American"
    BRITISH = "british", "British"
    AUSTRALIAN = "australian", "Australian"
    CANADIAN = "canadian", "Canadian"
    MIXED = "mixed", "Mixed"
    UNKNOWN = "unknown", "Unknown"


class ListeningContentStatus(models.TextChoices):
    READY = "ready", "Ready"
    PROCESSING = "processing", "Processing"
    COMING_SOON = "coming_soon", "Coming soon"
