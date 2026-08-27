from dataclasses import dataclass
from functools import lru_cache

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)
from pydantic import BaseModel, ValidationError


class ReadingAIError(Exception):
    code = "AI_ERROR"


class ReadingAITransientError(ReadingAIError):
    code = "AI_TRANSIENT_ERROR"


class ReadingAIPermanentError(ReadingAIError):
    code = "AI_PERMANENT_ERROR"


class ReadingAIInvalidResponse(ReadingAIPermanentError):
    code = "AI_INVALID_RESPONSE"


@dataclass(frozen=True, slots=True)
class AIUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True, slots=True)
class StructuredAIResult[SchemaT: BaseModel]:
    data: SchemaT
    usage: AIUsage
    request_id: str | None = None


class OpenAIReadingClient:
    provider_name = "openai"

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise ImproperlyConfigured("OPENAI_API_KEY is required for reading AI.")

        timeout_seconds = float(settings.READING_AI_TIMEOUT_SECONDS)

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            max_retries=int(settings.READING_AI_SDK_MAX_RETRIES),
            timeout=timeout_seconds,
        )

    def parse[SchemaT: BaseModel](
        self,
        *,
        schema: type[SchemaT],
        instructions: str,
        input_text: str,
    ) -> StructuredAIResult[SchemaT]:
        try:
            response = self.client.responses.parse(
                model=settings.READING_AI_MODEL,
                instructions=instructions,
                input=input_text,
                text_format=schema,
            )

        except ValidationError as exc:
            raise ReadingAIInvalidResponse("Structured output validation failed.") from exc

        except (
            APIConnectionError,
            APITimeoutError,
        ) as exc:
            raise ReadingAITransientError(str(exc)) from exc

        except APIStatusError as exc:
            if (
                exc.status_code
                in {
                    408,
                    409,
                    429,
                }
                or exc.status_code >= 500
            ):
                raise ReadingAITransientError(
                    f"OpenAI temporary error ({exc.status_code})."
                ) from exc

            raise ReadingAIPermanentError(
                f"OpenAI rejected the request ({exc.status_code})."
            ) from exc

        parsed = response.output_parsed

        if parsed is None:
            response_status = getattr(
                response,
                "status",
                "unknown",
            )

            incomplete_details = getattr(
                response,
                "incomplete_details",
                None,
            )

            raise ReadingAIInvalidResponse(
                "OpenAI returned no parsed structured "
                "output. "
                f"status={response_status}, "
                f"incomplete={incomplete_details}"
            )

        usage_obj = getattr(
            response,
            "usage",
            None,
        )

        usage = AIUsage(
            input_tokens=int(
                getattr(
                    usage_obj,
                    "input_tokens",
                    0,
                )
                or 0
            ),
            output_tokens=int(
                getattr(
                    usage_obj,
                    "output_tokens",
                    0,
                )
                or 0
            ),
            total_tokens=int(
                getattr(
                    usage_obj,
                    "total_tokens",
                    0,
                )
                or 0
            ),
        )

        return StructuredAIResult(
            data=parsed,
            usage=usage,
            request_id=getattr(
                response,
                "_request_id",
                None,
            ),
        )


@lru_cache(maxsize=1)
def get_reading_ai_client() -> OpenAIReadingClient:
    provider = settings.READING_AI_PROVIDER.lower().strip()

    if provider != "openai":
        raise ImproperlyConfigured(
            f"Unsupported READING_AI_PROVIDER={settings.READING_AI_PROVIDER!r}."
        )

    return OpenAIReadingClient()
