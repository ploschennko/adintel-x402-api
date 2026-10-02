import re
import uuid

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from .admin_auth import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    create_admin_session,
    valid_admin_token,
    verify_admin_session,
)
from .config import get_settings
from .dashboard import render_admin_login, render_dashboard
from .local_engine import (
    generate_angles_local,
    generate_full_campaign_local,
    generate_hooks_local,
    generate_local,
    generate_storyboard_local,
)
from .openrouter import (
    OpenRouterError,
    OpenRouterUsage,
    generate_angles_openrouter,
    generate_full_campaign_openrouter,
    generate_hooks_openrouter,
    generate_openrouter,
    generate_storyboard_openrouter,
)
from .payment_capture import install_payment_capture
from .schemas import (
    AdIntelRequest,
    AdIntelResponse,
    AnglesResponse,
    FullCampaignResponse,
    HooksResponse,
    StoryboardResponse,
)
from .storage import UsageStore
from .x402_setup import install_x402

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description='Pay-per-call advertising intelligence API with x402 USDC payments.',
)
store = UsageStore(settings)
install_x402(app, settings)
# Must be installed after x402 so it can observe the final payment-response header.
install_payment_capture(app, store)


def price_float(value: str) -> float:
    match = re.search(r'([0-9]+(?:\.[0-9]+)?)', value)
    return float(match.group(1)) if match else 0.0


async def _run(req, endpoint, price, ai_func, local_func, response_cls):
    request_id = str(uuid.uuid4())
    warning = None
    provider = 'local'
    model = None
    usage = OpenRouterUsage(cost_known=True)

    if settings.ai_provider == 'openrouter' and settings.openrouter_api_key and settings.openrouter_model:
        try:
            result, model, usage = await ai_func(req, settings)
            provider = 'openrouter'
        except OpenRouterError as exc:
            result = local_func(req)
            provider = 'local_fallback'
            usage = exc.usage or OpenRouterUsage(cost_known=False)
            model = exc.model
            warning = f'OpenRouter unavailable; deterministic fallback used: {str(exc)[:180]}'
    else:
        result = local_func(req)
        if settings.ai_provider == 'openrouter':
            warning = 'OpenRouter selected but key/model is missing; deterministic fallback used.'

    store.record(
        request_id=request_id,
        endpoint=endpoint,
        provider=provider,
        model=model,
        x402_enabled=settings.x402_enabled,
        revenue_usd=price_float(price) if settings.x402_enabled else 0.0,
        ai_cost_usd=usage.cost_usd,
        ai_cost_known=usage.cost_known,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        generation_id=usage.generation_id,
        vertical=req.vertical,
        geo=req.geo,
        network=settings.x402_network if settings.x402_enabled else None,
    )
    return response_cls(
        request_id=request_id,
        provider=provider,
        model=model,
        result=result,
        warning=warning,
    )


@app.get('/')
async def root():
    return {
        'service': settings.app_name,
        'version': settings.app_version,
        'docs': '/docs',
        'pricing': '/pricing',
        'catalog': '/v1/catalog',
    }


@app.get('/health')
async def health():
    return {
        'status': 'ok',
        'service': settings.app_name,
        'version': settings.app_version,
        'x402_enabled': settings.x402_enabled,
        'network': settings.x402_network if settings.x402_enabled else None,
        'prices': settings.endpoint_prices if settings.x402_enabled else {},
        'ai_provider': settings.ai_provider,
        'storage_backend': settings.database_backend,
        'storage_persistent': settings.database_is_persistent,
        'warnings': settings.validate_runtime(),
    }


@app.get('/pricing')
@app.get('/v1/catalog')
async def pricing():
    descriptions = {
        '/v1/hooks': '12 advertising hooks',
        '/v1/angles': '6 strategic ad angles',
        '/v1/video-storyboard': 'short-form storyboard + video prompt',
        '/v1/ad-intel': 'complete creative intelligence pack',
        '/v1/full-campaign': 'premium strategy + creative pack + testing plan',
    }
    return {
        'network': settings.x402_network,
        'currency': 'USDC via x402',
        'endpoints': [
            {'method': 'POST', 'path': path, 'price': price, 'description': descriptions[path]}
            for path, price in settings.endpoint_prices.items()
        ],
    }


@app.get('/demo')
async def demo():
    req = AdIntelRequest(
        product='NOVA Fitness App',
        offer='7-day free trial',
        geo='US',
        vertical='fitness app',
        audience='Busy adults',
    )
    return AdIntelResponse(request_id='demo', provider='local-demo', result=generate_local(req))


@app.post('/v1/hooks', response_model=HooksResponse)
async def hooks(req: AdIntelRequest):
    return await _run(req, '/v1/hooks', settings.x402_price_hooks, generate_hooks_openrouter, generate_hooks_local, HooksResponse)


@app.post('/v1/angles', response_model=AnglesResponse)
async def angles(req: AdIntelRequest):
    return await _run(req, '/v1/angles', settings.x402_price_angles, generate_angles_openrouter, generate_angles_local, AnglesResponse)


@app.post('/v1/video-storyboard', response_model=StoryboardResponse)
async def storyboard(req: AdIntelRequest):
    return await _run(
        req,
        '/v1/video-storyboard',
        settings.x402_price_storyboard,
        generate_storyboard_openrouter,
        generate_storyboard_local,
        StoryboardResponse,
    )


@app.post('/v1/ad-intel', response_model=AdIntelResponse)
async def adintel(req: AdIntelRequest):
    return await _run(req, '/v1/ad-intel', settings.x402_price, generate_openrouter, generate_local, AdIntelResponse)


@app.post('/v1/full-campaign', response_model=FullCampaignResponse)
async def full(req: AdIntelRequest):
    return await _run(
        req,
        '/v1/full-campaign',
        settings.x402_price_full_campaign,
        generate_full_campaign_openrouter,
        generate_full_campaign_local,
        FullCampaignResponse,
    )


def require_admin(
    x_admin_token: str = Header(default=''),
    adintel_admin_session: str = Cookie(default=''),
):
    if valid_admin_token(settings, x_admin_token) or verify_admin_session(settings, adintel_admin_session):
        return
    raise HTTPException(status_code=401, detail='Admin authentication required')


@app.get('/admin', response_class=HTMLResponse)
async def login_page(adintel_admin_session: str = Cookie(default='')):
    if verify_admin_session(settings, adintel_admin_session):
        return RedirectResponse('/admin/dashboard', status_code=303)
    return HTMLResponse(render_admin_login(settings.app_name))


@app.post('/admin/login')
async def login(x_admin_token: str = Header(default='')):
    if not valid_admin_token(settings, x_admin_token):
        raise HTTPException(status_code=401, detail='Invalid admin token')
    response = JSONResponse({'ok': True, 'redirect': '/admin/dashboard'})
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_admin_session(settings),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=settings.public_base_url.startswith('https://'),
        samesite='strict',
        path='/',
    )
    return response


@app.post('/admin/logout')
async def logout():
    response = JSONResponse({'ok': True})
    response.delete_cookie(SESSION_COOKIE_NAME, path='/')
    return response


@app.get('/admin/stats', dependencies=[Depends(require_admin)])
async def stats():
    return store.stats()


@app.get('/admin/dashboard', response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def dashboard():
    return HTMLResponse(
        render_dashboard(
            store.stats(),
            service=settings.app_name,
            network=settings.x402_network,
            price='multi-endpoint pricing',
        )
    )
