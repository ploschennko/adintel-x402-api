from .schemas import AdIntelOutput, AdIntelRequest, CreativeConcept, StoryboardScene


def generate_local(req: AdIntelRequest) -> AdIntelOutput:
    p = req.product
    offer = req.offer
    geo = req.geo
    audience = req.audience
    vertical = req.vertical.lower()

    hooks = [
        f'{p}: the offer worth a second look',
        f'What if {offer} was the reason to try {p} today?',
        f'Before you scroll: here is what makes {p} different',
        f'{audience}: this one is built around your needs',
        f'A simpler way to discover {p}',
        f'The {p} offer people in {geo} should know about',
        f'One product. One clear benefit. {p}.',
        f'Looking for a stronger option? Meet {p}',
        f'The quick version: {offer}',
        f'Why {p} belongs on your shortlist',
    ]

    angles = [
        f'Offer-first: lead with {offer}.',
        f'Problem/solution: position {p} as the answer to a concrete audience pain.',
        'Proof-oriented: show product details, process, or measurable product attributes instead of hype.',
        'UGC-style: first-person discovery with a natural mobile-native presentation.',
        f'Geo-specific relevance: adapt examples and terminology for {geo}.',
    ]

    headlines = [
        f'Discover {p}',
        f'{offer}',
        f'A Better Look at {p}',
        f'Built for {audience}',
        f'See What {p} Offers',
    ]

    primary_texts = [
        f'Meet {p}. {offer}. Clear value, a straightforward message, and a reason to learn more.',
        f'If you are exploring options in {geo}, put {p} on the list. Start with the offer: {offer}.',
        f'No oversized promises. Just {p}, the details that matter, and a simple next step.',
    ]

    concepts = [
        CreativeConcept(
            name='Offer Card',
            hook=headlines[1],
            visual='Clean product/brand hero with one bold benefit, one supporting line, and a high-contrast CTA.',
            body=f'Explain {offer} in one sentence and keep secondary information visually quiet.',
            cta='Learn More',
        ),
        CreativeConcept(
            name='UGC Discovery',
            hook=f'I just found {p} — here is what stood out.',
            visual='Vertical phone-style framing, authentic presenter or hands/product shot, captions, quick cuts.',
            body='Show the offer, one concrete differentiator, then the next step.',
            cta='See Details',
        ),
        CreativeConcept(
            name='Problem to Solution',
            hook='Still comparing options?',
            visual='Split-screen: common frustration on the left, product/solution on the right.',
            body=f'Frame {p} as a practical option and support the claim with verifiable product information.',
            cta='Explore',
        ),
    ]

    storyboard = [
        StoryboardScene(seconds='0-3', visual='Fast product/brand reveal', on_screen_text=hooks[0], voiceover=hooks[0]),
        StoryboardScene(seconds='3-7', visual='Show the main product benefit', on_screen_text=offer, voiceover=f'Here is the main offer: {offer}.'),
        StoryboardScene(seconds='7-12', visual='Feature or proof sequence', on_screen_text='Why it stands out', voiceover=f'{p} is positioned around a clear, practical value proposition.'),
        StoryboardScene(seconds='12-16', visual='Offer recap + trust cue', on_screen_text='Check the details', voiceover='Review the details and decide whether it fits what you need.'),
        StoryboardScene(seconds='16-20', visual='Brand end card + CTA', on_screen_text='Learn More', voiceover=f'Learn more about {p}.'),
    ]

    compliance = [
        'Use only claims that can be substantiated by the advertiser.',
        'Do not use fake scarcity, fabricated testimonials, or guaranteed results.',
        'Confirm platform and local-market advertising rules before launch.',
    ]
    if any(x in vertical for x in ('gambl', 'casino', 'bet', 'igaming')):
        compliance.extend([
            'Restrict targeting and messaging to legally eligible adults in the chosen GEO.',
            'Include required responsible-gambling and licensing disclosures where applicable.',
            'Avoid language implying guaranteed winnings, risk-free play, or financial security.',
        ])

    image_prompt = (
        f'Create a premium paid-social advertising image for {p}. Target: {audience}. '
        f'GEO context: {geo}. Main message: {offer}. Tone: {req.tone}. '
        'Strong visual hierarchy, mobile-first readability, one primary CTA area, no fake logos, no fabricated testimonials.'
    )
    video_prompt = (
        f'Create a 20-second vertical 9:16 paid-social video concept for {p}. '
        f'Open with a strong hook in the first 2 seconds, demonstrate the offer "{offer}", '
        'use fast readable captions, clear product visuals, restrained transitions, and a final CTA card.'
    )

    return AdIntelOutput(
        hooks=hooks,
        angles=angles,
        headlines=headlines,
        primary_texts=primary_texts,
        creative_concepts=concepts,
        video_storyboard=storyboard,
        image_prompt=image_prompt,
        video_prompt=video_prompt,
        compliance_notes=compliance[:8],
    )
