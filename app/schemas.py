from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _stringify(value: Any, preferred_keys: tuple[str, ...] = ()) -> str:
    """Normalize common LLM JSON variants into a stable string contract."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in preferred_keys + ('text', 'value', 'description', 'name', 'title'):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        parts = [str(v).strip() for v in value.values() if isinstance(v, (str, int, float)) and str(v).strip()]
        if parts:
            return ' — '.join(parts)
    return str(value).strip()


def _normalize_string_list(value: Any, preferred_keys: tuple[str, ...] = ()) -> Any:
    if not isinstance(value, list):
        return value
    return [_stringify(item, preferred_keys) for item in value]


class AdIntelRequest(BaseModel):
    product: str = Field(..., min_length=2, max_length=200)
    offer: str = Field(..., min_length=2, max_length=500)
    geo: str = Field(default='Global', max_length=120)
    language: str = Field(default='English', max_length=80)
    vertical: str = Field(default='general', max_length=100)
    audience: str = Field(default='General adult audience', max_length=500)
    landing_url: str | None = Field(default=None, max_length=500)
    landing_text: str | None = Field(default=None, max_length=5000)
    tone: Literal['direct','premium','ugc','emotional','informational'] = 'direct'

    @model_validator(mode='after')
    def normalize(self):
        self.product = self.product.strip()
        self.offer = self.offer.strip()
        return self


class CreativeConcept(BaseModel):
    name: str
    hook: str
    visual: str
    body: str
    cta: str


class StoryboardScene(BaseModel):
    seconds: str
    visual: str
    on_screen_text: str
    voiceover: str


class HooksOutput(BaseModel):
    hooks: list[str] = Field(min_length=8, max_length=20)

    @field_validator('hooks', mode='before')
    @classmethod
    def normalize_hooks(cls, value):
        return _normalize_string_list(value, ('hook',))


class AnglesOutput(BaseModel):
    angles: list[str] = Field(min_length=4, max_length=10)

    @field_validator('angles', mode='before')
    @classmethod
    def normalize_angles(cls, value):
        return _normalize_string_list(value, ('angle', 'framing'))


class StoryboardOutput(BaseModel):
    video_storyboard: list[StoryboardScene] = Field(min_length=3, max_length=8)
    video_prompt: str


class AdIntelOutput(BaseModel):
    hooks: list[str] = Field(min_length=5, max_length=15)
    angles: list[str] = Field(min_length=3, max_length=8)
    headlines: list[str] = Field(min_length=3, max_length=8)
    primary_texts: list[str] = Field(min_length=2, max_length=5)
    creative_concepts: list[CreativeConcept] = Field(min_length=2, max_length=5)
    video_storyboard: list[StoryboardScene] = Field(min_length=3, max_length=8)
    image_prompt: str
    video_prompt: str
    compliance_notes: list[str] = Field(min_length=1, max_length=8)

    @field_validator('hooks', mode='before')
    @classmethod
    def normalize_hooks(cls, value):
        return _normalize_string_list(value, ('hook',))

    @field_validator('angles', mode='before')
    @classmethod
    def normalize_angles(cls, value):
        return _normalize_string_list(value, ('angle', 'framing'))

    @field_validator('headlines', mode='before')
    @classmethod
    def normalize_headlines(cls, value):
        return _normalize_string_list(value, ('headline',))

    @field_validator('primary_texts', mode='before')
    @classmethod
    def normalize_primary_texts(cls, value):
        return _normalize_string_list(value, ('primary_text', 'copy', 'text'))

    @field_validator('compliance_notes', mode='before')
    @classmethod
    def normalize_compliance_notes(cls, value):
        return _normalize_string_list(value, ('note', 'risk', 'recommendation'))


class FullCampaignOutput(AdIntelOutput):
    strategy_summary: str
    recommended_angle: str
    audience_insights: list[str] = Field(min_length=3, max_length=8)
    testing_plan: list[str] = Field(min_length=3, max_length=8)

    @field_validator('recommended_angle', mode='before')
    @classmethod
    def normalize_recommended_angle(cls, value):
        return _stringify(value, ('angle', 'recommendation'))

    @field_validator('audience_insights', mode='before')
    @classmethod
    def normalize_audience_insights(cls, value):
        return _normalize_string_list(value, ('insight',))

    @field_validator('testing_plan', mode='before')
    @classmethod
    def normalize_testing_plan(cls, value):
        return _normalize_string_list(value, ('step', 'test', 'action'))


class BasePaidResponse(BaseModel):
    request_id: str
    provider: str
    model: str | None = None
    warning: str | None = None


class HooksResponse(BasePaidResponse):
    result: HooksOutput


class AnglesResponse(BasePaidResponse):
    result: AnglesOutput


class StoryboardResponse(BasePaidResponse):
    result: StoryboardOutput


class AdIntelResponse(BasePaidResponse):
    result: AdIntelOutput


class FullCampaignResponse(BasePaidResponse):
    result: FullCampaignOutput
