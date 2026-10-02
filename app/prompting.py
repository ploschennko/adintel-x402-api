import json
from .schemas import AdIntelRequest

SYSTEM_PROMPT = """You are AdIntel, a performance-advertising creative strategist.
Return only valid JSON matching the requested schema. Create useful advertising concepts, not policy-evasion tactics.
Never provide cloaking, review bypass, fake testimonials, guaranteed-income claims, or instructions to deceive ad platforms.
For regulated verticals, add practical compliance notes and avoid certainty about legal compliance.
Do not claim you inspected a URL unless landing-page text was supplied in the request."""


def _brief(req: AdIntelRequest) -> str:
    return json.dumps(req.model_dump(), ensure_ascii=False, indent=2)


def build_hooks_prompt(req):
    return f'Generate 12 distinct paid-social hooks for this brief. Keep them short, varied and usable.\nBRIEF:\n{_brief(req)}\nOUTPUT JSON: {{"hooks":["12 hooks"]}}'


def build_angles_prompt(req):
    return f'Generate 6 distinct advertising angles. Each angle should explain the strategic framing in one concise sentence.\nBRIEF:\n{_brief(req)}\nOUTPUT JSON: {{"angles":["6 angles"]}}'


def build_storyboard_prompt(req):
    shape={'video_storyboard':[{'seconds':'0-3','visual':'scene','on_screen_text':'text','voiceover':'voiceover'}],'video_prompt':'production-ready vertical-video generation prompt'}
    return f'Create a 15-20 second mobile-first paid-social storyboard with 5 scenes.\nBRIEF:\n{_brief(req)}\nOUTPUT JSON:\n{json.dumps(shape, indent=2)}'


def build_user_prompt(req):
    shape={'hooks':['10 hooks'],'angles':['5 angles'],'headlines':['5 headlines'],'primary_texts':['3 primary texts'],'creative_concepts':[{'name':'name','hook':'hook','visual':'visual','body':'body','cta':'CTA'}],'video_storyboard':[{'seconds':'0-3','visual':'scene','on_screen_text':'text','voiceover':'voiceover'}],'image_prompt':'image prompt','video_prompt':'video prompt','compliance_notes':['notes']}
    return f'Create a complete paid-social creative pack.\nBRIEF:\n{_brief(req)}\nOUTPUT JSON:\n{json.dumps(shape, ensure_ascii=False, indent=2)}'


def build_full_campaign_prompt(req):
    shape={'hooks':['15 hooks'],'angles':['8 angles'],'headlines':['8 headlines'],'primary_texts':['5 primary texts'],'creative_concepts':[{'name':'name','hook':'hook','visual':'visual','body':'body','cta':'CTA'}],'video_storyboard':[{'seconds':'0-3','visual':'scene','on_screen_text':'text','voiceover':'voiceover'}],'image_prompt':'image prompt','video_prompt':'video prompt','compliance_notes':['notes'],'strategy_summary':'campaign strategy','recommended_angle':'single best angle + rationale','audience_insights':['insights'],'testing_plan':['A/B testing steps']}
    return f'Create a premium full campaign strategy and creative pack. Prioritize actionable testing logic.\nBRIEF:\n{_brief(req)}\nOUTPUT JSON:\n{json.dumps(shape, ensure_ascii=False, indent=2)}'
