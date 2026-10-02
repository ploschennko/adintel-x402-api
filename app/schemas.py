from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AdIntelRequest(BaseModel):
    product: str = Field(..., min_length=2, max_length=200, description='Product or service name')
    offer: str = Field(..., min_length=2, max_length=500, description='Main offer, bonus or value proposition')
    geo: str = Field(default='Global', max_length=120, description='Target country or region')
    language: str = Field(default='English', max_length=80, description='Output language')
    vertical: str = Field(default='general', max_length=100, description='Industry or advertising vertical')
    audience: str = Field(default='General adult audience', max_length=500, description='Target audience')
    landing_url: str | None = Field(default=None, max_length=500, description='Optional landing-page URL label; MVP does not scrape it')
    landing_text: str | None = Field(default=None, max_length=5000, description='Optional landing-page copy or product description')
    tone: Literal['direct', 'premium', 'ugc', 'emotional', 'informational'] = 'direct'

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


class AdIntelResponse(BaseModel):
    request_id: str
    provider: str
    model: str | None = None
    result: AdIntelOutput
    warning: str | None = None
