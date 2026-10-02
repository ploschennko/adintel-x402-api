from app.schemas import AdIntelRequest
from app.local_engine import generate_hooks_local, generate_angles_local, generate_storyboard_local, generate_full_campaign_local

def test_v05_local_products():
    req=AdIntelRequest(product='NOVA App',offer='20% off annual plan')
    assert len(generate_hooks_local(req).hooks)>=8
    assert len(generate_angles_local(req).angles)>=4
    assert len(generate_storyboard_local(req).video_storyboard)>=3
    assert generate_full_campaign_local(req).testing_plan
