from app.local_engine import generate_local
from app.schemas import AdIntelRequest


def test_local_output_is_valid():
    req = AdIntelRequest(product='Example', offer='10% launch offer')
    output = generate_local(req)
    assert len(output.hooks) >= 5
    assert len(output.angles) >= 3
    assert len(output.video_storyboard) >= 3


def test_gambling_adds_compliance_notes():
    req = AdIntelRequest(product='Example Casino', offer='Welcome bonus', vertical='igaming')
    output = generate_local(req)
    joined = ' '.join(output.compliance_notes).lower()
    assert 'responsible' in joined or 'winnings' in joined
