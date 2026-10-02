from typing import Literal
from pydantic import BaseModel, Field, model_validator


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
        self.product = self.product.strip(); self.offer = self.offer.strip(); return self


class CreativeConcept(BaseModel):
    name: str; hook: str; visual: str; body: str; cta: str


class StoryboardScene(BaseModel):
    seconds: str; visual: str; on_screen_text: str; voiceover: str


class HooksOutput(BaseModel):
    hooks: list[str] = Field(min_length=8, max_length=20)


class AnglesOutput(BaseModel):
    angles: list[str] = Field(min_length=4, max_length=10)


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


class FullCampaignOutput(AdIntelOutput):
    strategy_summary: str
    recommended_angle: str
    audience_insights: list[str] = Field(min_length=3, max_length=8)
    testing_plan: list[str] = Field(min_length=3, max_length=8)


class BasePaidResponse(BaseModel):
    request_id: str
    provider: str
    model: str | None = None
    warning: str | None = None


class HooksResponse(BasePaidResponse): result: HooksOutput
class AnglesResponse(BasePaidResponse): result: AnglesOutput
class StoryboardResponse(BasePaidResponse): result: StoryboardOutput
class AdIntelResponse(BasePaidResponse): result: AdIntelOutput
class FullCampaignResponse(BasePaidResponse): result: FullCampaignOutput
