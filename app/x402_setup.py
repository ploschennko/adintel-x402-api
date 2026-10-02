from fastapi import FastAPI
from .config import Settings

def install_x402(app:FastAPI,settings:Settings)->None:
    if not settings.x402_enabled:return
    if not settings.pay_to_address: raise RuntimeError('X402_ENABLED=true requires PAY_TO_ADDRESS')
    from x402.extensions.bazaar import OutputConfig, declare_discovery_extension
    from x402.http import FacilitatorConfig, HTTPFacilitatorClient, PaymentOption
    from x402.http.middleware.fastapi import PaymentMiddlewareASGI
    from x402.http.types import RouteConfig
    from x402.mechanisms.evm.exact import ExactEvmServerScheme
    from x402.server import x402ResourceServer
    facilitator=HTTPFacilitatorClient(FacilitatorConfig(url=settings.facilitator_url)); server=x402ResourceServer(facilitator); server.register(settings.x402_network,ExactEvmServerScheme())
    input_schema={'type':'object','properties':{'product':{'type':'string'},'offer':{'type':'string'},'geo':{'type':'string'},'language':{'type':'string'},'vertical':{'type':'string'},'audience':{'type':'string'},'landing_url':{'type':['string','null']},'landing_text':{'type':['string','null']},'tone':{'type':'string'}},'required':['product','offer']}
    base_out={'type':'object','properties':{'request_id':{'type':'string'},'provider':{'type':'string'},'model':{'type':['string','null']},'result':{'type':'object'},'warning':{'type':['string','null']}},'required':['request_id','provider','result']}
    defs=[('/v1/hooks',settings.x402_price_hooks,'Generate short paid-social advertising hooks.',['advertising','hooks','copywriting']),('/v1/angles',settings.x402_price_angles,'Generate strategic advertising angles for a campaign brief.',['advertising','marketing','strategy']),('/v1/video-storyboard',settings.x402_price_storyboard,'Generate a short-form paid-social video storyboard and production prompt.',['video','storyboard','creative']),('/v1/ad-intel',settings.x402_price,'Generate a complete ad creative intelligence pack.',['advertising','creative','copywriting','agents']),('/v1/full-campaign',settings.x402_price_full_campaign,'Generate premium campaign strategy, creatives, audience insights and testing plan.',['advertising','campaign','strategy','agents'])]
    routes={}
    for path,price,desc,tags in defs:
        discovery=declare_discovery_extension(input={'product':'Example App','offer':'20% off annual plan','geo':'US','language':'English'},input_schema=input_schema,output=OutputConfig(example={'request_id':'example','provider':'openrouter','result':{}},schema=base_out))
        routes[f'POST {path}']=RouteConfig(accepts=[PaymentOption(scheme='exact',price=price,network=settings.x402_network,pay_to=settings.pay_to_address)],resource=settings.public_base_url.rstrip('/')+path,mime_type='application/json',description=desc,service_name='AdIntel x402',tags=tags,extensions=discovery)
    app.add_middleware(PaymentMiddlewareASGI,routes=routes,server=server)
