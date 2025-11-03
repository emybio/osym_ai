import json
import os
from typing import Iterable, List

from django.conf import settings
from openai import OpenAI
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Difficulty, Question, Subject, Topic
from .prompts import SYSTEM_PROMPT, USER_TEMPLATE
from .serializers import QuestionSerializer

from zai._client import ZaiClient  # Z.ai SDK

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_openai_client = (
    OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
)
_zai_client = (
    ZaiClient(api_key=settings.ZAI_API_KEY)
    if getattr(settings, "ZAI_API_KEY", None)
    else None
)


def _format_choices(options) -> List[str]:
    if not options:
        return []
    if isinstance(options, list):
        return [opt for opt in options if opt]
    ordered = []
    for key in ["A", "B", "C", "D", "E"]:
        if options.get(key):
            ordered.append(options[key])
    return ordered


def _get_ai_response(provider: str, messages: Iterable[dict], *, json_mode: bool = False):
    """OpenAI veya Z.ai'den yanıt döndürür. Z.ai hata verirse otomatik OpenAI fallback yapılır."""
    # Z.ai seçilmişse dene
    if provider == "zai":
        if not _zai_client:
            print("⚠️  ZAI_API_KEY tanımlı değil, OpenAI fallback'e geçiliyor.")
            provider = "openai"
        else:
            try:
                zai_model = os.getenv("ZAI_MODEL", "glm-4.5")
                return _zai_client.chat.completions.create(
                    model=zai_model,
                    messages=list(messages),
                    response_format={"type": "json_object"} if json_mode else None,
                    temperature=0.5,
                    max_tokens=800,
                )
            except Exception as e:
                import traceback
                print("⚠️  ZAI API hatası:", e)
                print(traceback.format_exc())
                print("➡️  Fallback: OpenAI kullanılacak.")
                provider = "openai"

    # OpenAI fallback veya doğrudan çağrı
    if provider == "openai":
        if not _openai_client:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        kwargs = {
            "model": os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
            "messages": list(messages),
            "max_tokens": 800,
            "temperature": 0.5,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        return _openai_client.chat.completions.create(**kwargs)

    # Eğer başka sağlayıcı varsa (ileride genişletme için)
    raise ValueError(f"Unsupported provider: {provider}")



@api_view(["POST"])
def generate_question(request):
    data = request.data
    subject = data.get("subject", Subject.MATEMATIK)
    topic_name = data.get("topic", "Temel Kavramlar")
    difficulty = data.get("difficulty", Difficulty.MEDIUM)
    provider = data.get("provider", "openai")  # eklenen parametre

    prompt = USER_TEMPLATE.format(
        subject=subject, topic=topic_name, difficulty=difficulty
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    try:
        completion = _get_ai_response(provider, messages, json_mode=True)
        content = completion.choices[0].message.content
        payload = json.loads(content)
    except Exception as exc:
        return Response(
            {"error": f"{provider} API hatası", "detail": repr(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    choices = _format_choices(payload.get("choices"))
    question = Question.objects.create(
        subject=subject,
        topic=Topic.objects.filter(name=topic_name).first(),
        difficulty=difficulty,
        stem=payload.get("stem", ""),
        choices=choices,
        answer=(payload.get("answer", "") or "A")[0],
        rubric=payload.get("rubric", ""),
        source=provider,
    )
    return Response(QuestionSerializer(question).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def explain(request, pk: int):
    try:
        question = Question.objects.get(pk=pk)
    except Question.DoesNotExist:
        return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    provider = request.data.get("provider", "openai")
    user_message = (
        f"Soruyu adım adım açıkla: {question.stem}\nSeçenekler: {question.choices}"
    )

    try:
        completion = _get_ai_response(
            provider,
            [
                {"role": "system", "content": "Kısa, sade ve adım adım açıklama yap."},
                {"role": "user", "content": user_message},
            ],
        )
        explanation = completion.choices[0].message.content
    except Exception as exc:
        return Response(
            {"error": f"{provider} açıklama hatası", "detail": repr(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response({"explanation": explanation})
