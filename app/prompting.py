import json

from .schemas import AdIntelRequest


SYSTEM_PROMPT = """You are AdIntel, a performance-advertising creative strategist.
Return only valid JSON matching the requested schema.
Create useful advertising concepts, not policy-evasion tactics.
Never provide cloaking, review bypass, fake testimonials, guaranteed-income claims, or instructions to deceive ad platforms.
For regulated verticals, add practical compliance notes and avoid certainty about legal compliance.
Do not claim you inspected a URL unless landing-page text was supplied in the request."""


def build_user_prompt(req: AdIntelRequest) -> str:
    payload = req.model_dump()
    schema = {
        'hooks': ['10 short hooks'],
        'angles': ['5 advertising angles'],
        'headlines': ['5 headlines'],
        'primary_texts': ['3 primary ad texts'],
        'creative_concepts': [
            {'name': 'concept name', 'hook': 'opening hook', 'visual': 'visual direction', 'body': 'message', 'cta': 'CTA'}
        ],
        'video_storyboard': [
            {'seconds': '0-3', 'visual': 'scene', 'on_screen_text': 'text', 'voiceover': 'voiceover'}
        ],
        'image_prompt': 'production-ready image-generation prompt',
        'video_prompt': 'production-ready short-video-generation prompt',
        'compliance_notes': ['practical risk/compliance notes']
    }
    return (
        'Create a complete paid-social creative pack from this campaign brief.\n\n'
        f'BRIEF:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n'
        'Important: landing_url is only contextual metadata. Do not say you visited or scraped it. '
        'Use landing_text when supplied.\n\n'
        f'OUTPUT JSON SHAPE:\n{json.dumps(schema, ensure_ascii=False, indent=2)}'
    )
