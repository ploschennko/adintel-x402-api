import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .config import Settings
from .prompting import SYSTEM_PROMPT, build_user_prompt
from .schemas import AdIntelOutput, AdIntelRequest


class OpenRouterError(RuntimeError):
    pass


@dataclass(slots=True)
class OpenRouterUsage:
    cost_usd: float = 0.0
    cost_known: bool = False
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    generation_id: str | None = None


def _extract_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.I)
        cleaned = re.sub(r'\s*```$', '', cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _as_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


async def generate_openrouter(
    req: AdIntelRequest,
    settings: Settings,
) -> tuple[AdIntelOutput, str, OpenRouterUsage]:
    if not settings.openrouter_api_key or not settings.openrouter_model:
        raise OpenRouterError('OpenRouter key/model is not configured')

    headers = {
        'Authorization': f'Bearer {settings.openrouter_api_key}',
        'Content-Type': 'application/json',
    }
    if settings.app_url:
        headers['HTTP-Referer'] = settings.app_url
    if settings.app_title:
        headers['X-Title'] = settings.app_title

    body = {
        'model': settings.openrouter_model,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': build_user_prompt(req)},
        ],
        'temperature': 0.7,
        'response_format': {'type': 'json_object'},
        'usage': {'include': True},
    }

    url = settings.openrouter_base_url.rstrip('/') + '/chat/completions'
    try:
        async with httpx.AsyncClient(timeout=settings.openrouter_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError as exc:
        raise OpenRouterError(f'OpenRouter network error: {exc}') from exc

    if response.status_code >= 400:
        raise OpenRouterError(f'OpenRouter HTTP {response.status_code}: {response.text[:500]}')

    data = response.json()
    try:
        text = data['choices'][0]['message']['content']
        output = AdIntelOutput.model_validate(_extract_json(text))
    except Exception as exc:
        raise OpenRouterError(f'Invalid model output: {exc}') from exc

    usage_raw = data.get('usage') or {}
    input_tokens = _as_int(usage_raw.get('prompt_tokens', usage_raw.get('input_tokens')))
    output_tokens = _as_int(usage_raw.get('completion_tokens', usage_raw.get('output_tokens')))
    total_tokens = _as_int(usage_raw.get('total_tokens')) or input_tokens + output_tokens
    cost_known = 'cost' in usage_raw and usage_raw.get('cost') is not None
    cost_usd = _as_float(usage_raw.get('cost')) if cost_known else 0.0

    usage = OpenRouterUsage(
        cost_usd=cost_usd,
        cost_known=cost_known,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        generation_id=response.headers.get('x-generation-id') or data.get('id'),
    )

    return output, data.get('model', settings.openrouter_model), usage
