from fastapi import FastAPI

from .config import Settings


def install_x402(app: FastAPI, settings: Settings) -> None:
    if not settings.x402_enabled:
        return

    if not settings.pay_to_address:
        raise RuntimeError('X402_ENABLED=true requires PAY_TO_ADDRESS')

    from x402.extensions.bazaar import OutputConfig, declare_discovery_extension
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI
    from x402.http.types import RouteConfig
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    from x402.server import x402ResourceServer

    facilitator = HTTPFacilitatorClient(FacilitatorConfig(url=settings.facilitator_url))
    server = x402ResourceServer(facilitator)
    server.register(settings.x402_network, ExactEvmServerScheme())

    resource_url = settings.public_base_url.rstrip('/') + '/v1/ad-intel'

    input_schema = {
        'type': 'object',
        'properties': {
            'product': {'type': 'string', 'description': 'Product or service name'},
            'offer': {'type': 'string', 'description': 'Main offer or value proposition'},
            'geo': {'type': 'string', 'description': 'Target country or region'},
            'language': {'type': 'string', 'description': 'Desired output language'},
            'vertical': {'type': 'string', 'description': 'Industry or advertising vertical'},
            'audience': {'type': 'string', 'description': 'Target audience'},
            'landing_url': {'type': ['string', 'null'], 'description': 'Optional URL label; not scraped by MVP'},
            'landing_text': {'type': ['string', 'null'], 'description': 'Optional landing page or product copy'},
            'tone': {'type': 'string', 'enum': ['direct', 'premium', 'ugc', 'emotional', 'informational']},
        },
        'required': ['product', 'offer'],
    }

    output_example = {
        'request_id': 'example-request-id',
        'provider': 'openrouter',
        'model': 'configured-model',
        'result': {
            'hooks': ['Hook 1', 'Hook 2', 'Hook 3', 'Hook 4', 'Hook 5'],
            'angles': ['Angle 1', 'Angle 2', 'Angle 3'],
            'headlines': ['Headline 1', 'Headline 2', 'Headline 3'],
            'primary_texts': ['Primary text 1', 'Primary text 2'],
            'creative_concepts': [
                {'name': 'Concept A', 'hook': 'Hook', 'visual': 'Visual', 'body': 'Body', 'cta': 'Learn More'},
                {'name': 'Concept B', 'hook': 'Hook', 'visual': 'Visual', 'body': 'Body', 'cta': 'See Details'},
            ],
            'video_storyboard': [
                {'seconds': '0-3', 'visual': 'Opening', 'on_screen_text': 'Hook', 'voiceover': 'Hook'},
                {'seconds': '3-8', 'visual': 'Product', 'on_screen_text': 'Offer', 'voiceover': 'Offer'},
                {'seconds': '8-15', 'visual': 'CTA', 'on_screen_text': 'Learn More', 'voiceover': 'Learn more'},
            ],
            'image_prompt': 'Image prompt',
            'video_prompt': 'Video prompt',
            'compliance_notes': ['Verify claims and local ad rules'],
        },
    }

    output_schema = {
        'type': 'object',
        'properties': {
            'request_id': {'type': 'string'},
            'provider': {'type': 'string'},
            'model': {'type': ['string', 'null']},
            'result': {'type': 'object'},
            'warning': {'type': ['string', 'null']},
        },
        'required': ['request_id', 'provider', 'result'],
    }

    discovery = declare_discovery_extension(
        input={'product': 'Example App', 'offer': '20% off annual plan', 'geo': 'US', 'language': 'English'},
        input_schema=input_schema,
        output=OutputConfig(example=output_example, schema=output_schema),
    )

    routes: dict[str, RouteConfig] = {
        'POST /v1/ad-intel': RouteConfig(
            accepts=[
                PaymentOption(
                    scheme='exact',
                    price=settings.x402_price,
                    network=settings.x402_network,
                    pay_to=settings.pay_to_address,
                )
            ],
            resource=resource_url,
            mime_type='application/json',
            description='Generate ad hooks, angles, copy, creative concepts, video storyboard and compliance notes from an advertising brief.',
            service_name='AdIntel x402',
            tags=['advertising', 'marketing', 'creative', 'copywriting', 'agents'],
            extensions=discovery,
        )
    }

    app.add_middleware(PaymentMiddlewareASGI, routes=routes, server=server)
