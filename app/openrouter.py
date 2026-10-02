import json, re
from dataclasses import dataclass
from typing import Any, TypeVar
import httpx
from pydantic import BaseModel
from .config import Settings
from .prompting import SYSTEM_PROMPT, build_user_prompt, build_hooks_prompt, build_angles_prompt, build_storyboard_prompt, build_full_campaign_prompt
from .schemas import AdIntelRequest, AdIntelOutput, HooksOutput, AnglesOutput, StoryboardOutput, FullCampaignOutput


@dataclass(slots=True)
class OpenRouterUsage:
    cost_usd: float=0.0
    cost_known: bool=False
    input_tokens:int=0
    output_tokens:int=0
    total_tokens:int=0
    generation_id:str|None=None


class OpenRouterError(RuntimeError):
    def __init__(self, message: str, *, usage: OpenRouterUsage | None = None, model: str | None = None):
        super().__init__(message)
        self.usage = usage
        self.model = model


T=TypeVar('T', bound=BaseModel)


def _extract_json(text:str)->dict:
    cleaned=text.strip(); cleaned=re.sub(r'^```(?:json)?\s*','',cleaned,flags=re.I); cleaned=re.sub(r'\s*```$','',cleaned)
    try:return json.loads(cleaned)
    except json.JSONDecodeError:
        s,e=cleaned.find('{'),cleaned.rfind('}')
        if s>=0 and e>s:return json.loads(cleaned[s:e+1])
        raise


def _i(v:Any)->int:
    try:return int(v or 0)
    except (TypeError, ValueError):return 0


def _f(v:Any)->float:
    try:return float(v or 0)
    except (TypeError, ValueError):return 0.0


def _usage_from_response(data: dict, response: httpx.Response) -> OpenRouterUsage:
    u=data.get('usage') or {}
    known='cost' in u and u.get('cost') is not None
    inp=_i(u.get('prompt_tokens',u.get('input_tokens')))
    out=_i(u.get('completion_tokens',u.get('output_tokens')))
    return OpenRouterUsage(
        _f(u.get('cost')) if known else 0.0,
        known,
        inp,
        out,
        _i(u.get('total_tokens')) or inp+out,
        response.headers.get('x-generation-id') or data.get('id'),
    )


async def _generate(req:AdIntelRequest, settings:Settings, model_type:type[T], prompt:str, temperature:float=.7)->tuple[T,str,OpenRouterUsage]:
    if not settings.openrouter_api_key or not settings.openrouter_model:
        raise OpenRouterError('OpenRouter key/model is not configured')
    headers={'Authorization':f'Bearer {settings.openrouter_api_key}','Content-Type':'application/json'}
    if settings.app_url: headers['HTTP-Referer']=settings.app_url
    if settings.app_title: headers['X-Title']=settings.app_title
    body={'model':settings.openrouter_model,'messages':[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':prompt}],'temperature':temperature,'response_format':{'type':'json_object'},'usage':{'include':True}}
    try:
        async with httpx.AsyncClient(timeout=settings.openrouter_timeout_seconds) as client:
            response=await client.post(settings.openrouter_base_url.rstrip('/')+'/chat/completions',headers=headers,json=body)
    except httpx.HTTPError as exc:
        raise OpenRouterError(f'OpenRouter network error: {exc}') from exc
    if response.status_code>=400:
        raise OpenRouterError(f'OpenRouter HTTP {response.status_code}: {response.text[:500]}')
    data=response.json()
    model_name=data.get('model',settings.openrouter_model)
    usage=_usage_from_response(data,response)
    try:
        output=model_type.model_validate(_extract_json(data['choices'][0]['message']['content']))
    except Exception as exc:
        raise OpenRouterError(f'Invalid model output: {exc}', usage=usage, model=model_name) from exc
    return output,model_name,usage


async def generate_openrouter(req,s): return await _generate(req,s,AdIntelOutput,build_user_prompt(req))
async def generate_hooks_openrouter(req,s): return await _generate(req,s,HooksOutput,build_hooks_prompt(req),.8)
async def generate_angles_openrouter(req,s): return await _generate(req,s,AnglesOutput,build_angles_prompt(req),.75)
async def generate_storyboard_openrouter(req,s): return await _generate(req,s,StoryboardOutput,build_storyboard_prompt(req),.7)
async def generate_full_campaign_openrouter(req,s): return await _generate(req,s,FullCampaignOutput,build_full_campaign_prompt(req),.7)
