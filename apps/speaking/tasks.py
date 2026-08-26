from celery import shared_task
from django.utils import timezone

from apps.speaking.models import SpeakingEvaluation, SpeakingSession, SpeakingTurn
from apps.speaking.services.dialogue import get_dialogue_provider
from apps.speaking.services.evaluation import get_evaluation_provider
from apps.speaking.services.transcription import get_transcription_provider


@shared_task(bind=True, max_retries=3)
def transcribe_turn_task(self, turn_id):
    try:
        turn = SpeakingTurn.objects.select_related("session").get(id=turn_id)
    except SpeakingTurn.DoesNotExist:
        return

    turn.transcription_status = SpeakingTurn.TranscriptionStatus.PROCESSING
    turn.save(update_fields=["transcription_status"])

    try:
        provider = get_transcription_provider()
        result = provider.transcribe(turn.audio_file)

        turn.text = result.text
        turn.transcription_raw = result.raw
        turn.transcription_status = SpeakingTurn.TranscriptionStatus.COMPLETED
        turn.save(update_fields=["text", "transcription_raw", "transcription_status"])
    except Exception as exc:
        turn.transcription_status = SpeakingTurn.TranscriptionStatus.FAILED
        turn.save(update_fields=["transcription_status"])
        raise self.retry(exc=exc, countdown=5) from exc

    # Only chain to AI reply generation once the transcript is finalized —
    # never on partial/in-progress transcripts, per the agreed design.
    generate_ai_turn_task.delay(str(turn.session_id))


@shared_task(bind=True, max_retries=3)
def generate_ai_turn_task(self, session_id):
    session = SpeakingSession.objects.prefetch_related("turns").get(id=session_id)

    dialogue = get_dialogue_provider()
    result = dialogue.generate_next_turn(session)

    next_order = session.turns.count()

    SpeakingTurn.objects.create(
        session=session,
        speaker=SpeakingTurn.Speaker.AI,
        order=next_order,
        text=result.text,
        transcription_status=SpeakingTurn.TranscriptionStatus.NOT_APPLICABLE,
        transcription_raw=result.raw,
    )


@shared_task(bind=True, max_retries=3)
def evaluate_session_task(self, evaluation_id):
    try:
        evaluation = SpeakingEvaluation.objects.select_related("session").get(id=evaluation_id)
    except SpeakingEvaluation.DoesNotExist:
        return

    evaluation.status = SpeakingEvaluation.Status.PROCESSING
    evaluation.save(update_fields=["status"])

    try:
        provider = get_evaluation_provider()
        result = provider.evaluate_session(evaluation.session)

        evaluation.score = result.score
        evaluation.analysis = result.analysis
        evaluation.raw_response = result.raw
        evaluation.status = SpeakingEvaluation.Status.COMPLETED
        evaluation.completed_at = timezone.now()
        evaluation.save(
            update_fields=[
                "score",
                "analysis",
                "raw_response",
                "status",
                "completed_at",
            ]
        )
    except Exception as exc:
        evaluation.status = SpeakingEvaluation.Status.FAILED
        evaluation.error_message = str(exc)
        evaluation.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc, countdown=5) from exc
