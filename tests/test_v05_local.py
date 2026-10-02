from app.schemas import AdIntelRequest
from app.local_engine import generate_hooks_local, generate_angles_local, generate_storyboard_local, generate_full_campaign_local

def test_v05_local_products():
    req=AdIntelRequest(product='NOVA App',offer='20% off annual plan')
    assert len(generate_hooks_local(req).hooks)>=8
    assert len(generate_angles_local(req).angles)>=4
    assert len(generate_storyboard_local(req).video_storyboard)>=3
    assert generate_full_campaign_local(req).testing_plan


from app.schemas import AnglesOutput, AdIntelOutput

def test_angles_accept_object_variants_from_llm():
    out = AnglesOutput.model_validate({
        "angles": [
            {"angle": "Offer-first framing", "rationale": "Lead with the discount"},
            {"angle": "Problem-solution framing"},
            {"angle": "Proof framing"},
            {"angle": "UGC framing"},
            {"angle": "Comparison framing"},
            {"angle": "Outcome framing"},
        ]
    })
    assert out.angles[0] == "Offer-first framing"
    assert all(isinstance(x, str) for x in out.angles)

def test_adintel_normalizes_string_list_objects():
    payload = {
        "hooks": [{"hook": f"Hook {i}"} for i in range(1, 6)],
        "angles": [{"angle": f"Angle {i}"} for i in range(1, 4)],
        "headlines": [{"headline": f"Headline {i}"} for i in range(1, 4)],
        "primary_texts": [{"copy": "Primary 1"}, {"copy": "Primary 2"}],
        "creative_concepts": [
            {"name": "A", "hook": "h", "visual": "v", "body": "b", "cta": "c"},
            {"name": "B", "hook": "h", "visual": "v", "body": "b", "cta": "c"},
        ],
        "video_storyboard": [
            {"seconds": "0-3", "visual": "v", "on_screen_text": "t", "voiceover": "o"},
            {"seconds": "3-6", "visual": "v", "on_screen_text": "t", "voiceover": "o"},
            {"seconds": "6-9", "visual": "v", "on_screen_text": "t", "voiceover": "o"},
        ],
        "image_prompt": "image",
        "video_prompt": "video",
        "compliance_notes": [{"note": "Check claims"}],
    }
    out = AdIntelOutput.model_validate(payload)
    assert out.angles == ["Angle 1", "Angle 2", "Angle 3"]
    assert out.headlines[0] == "Headline 1"
