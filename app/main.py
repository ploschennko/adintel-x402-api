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
from .local_engine import generate_local
from .openrouter import OpenRouterError, OpenRouterUsage, generate_openrouter
from .schemas import AdIntelRequest, AdIntelResponse
from .storage import UsageStore
from .x402_setup import install_x402

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description='Pay-per-call advertising creative intelligence API with optional x402 USDC payments.',
)
store = UsageStore(settings)
install_x402(app, settings)


def configured_price_float(price: str) -> float:
    match = re.search(r'([0-9]+(?:\.[0-9]+)?)', price)
    return float(match.group(1)) if match else 0.0


@app.get('/health')
async def health():
    return {
        'status': 'ok',
        'service': settings.app_name,
        'version': settings.app_version,
        'x402_enabled': settings.x402_enabled,
        'network': settings.x402_network if settings.x402_enabled else None,
        'price': settings.x402_price if settings.x402_enabled else None,
        'ai_provider': settings.ai_provider,
        'warnings': settings.validate_runtime(),
    }


@app.get('/pricing')
async def pricing():
    return {
        'endpoint': 'POST /v1/ad-intel',
        'price': settings.x402_price,
        'currency': 'USDC via x402 when enabled',
        'network': settings.x402_network,
        'free_endpoints': ['/health', '/pricing', '/demo'],
    }


@app.get('/demo')
async def demo():
    req = AdIntelRequest(
        product='NOVA Fitness App',
        offer='7-day free trial',
        geo='United States',
        language='English',
        vertical='fitness app',
        audience='Busy adults who want short home workouts',
        tone='ugc',
    )
    result = generate_local(req)
    return AdIntelResponse(request_id='demo', provider='local-demo', result=result)


@app.post('/v1/ad-intel', response_model=AdIntelResponse)
async def ad_intel(req: AdIntelRequest):
    request_id = str(uuid.uuid4())
    warning = None
    provider = 'local'
    model = None
    usage = OpenRouterUsage(cost_known=True)

    if settings.ai_provider == 'openrouter' and settings.openrouter_api_key and settings.openrouter_model:
        try:
            result, model, usage = await generate_openrouter(req, settings)
            provider = 'openrouter'
        except OpenRouterError as exc:
            result = generate_local(req)
            provider = 'local_fallback'
            # A failed/invalid OpenRouter generation can theoretically have incurred
            # inference cost even when no usable usage object reached us.
            usage = OpenRouterUsage(cost_known=False)
            warning = f'OpenRouter unavailable; deterministic fallback used: {str(exc)[:180]}'
    else:
        result = generate_local(req)
        if settings.ai_provider == 'openrouter':
            warning = 'OpenRouter selected but key/model is missing; deterministic fallback used.'

    revenue_usd = configured_price_float(settings.x402_price) if settings.x402_enabled else 0.0
    store.record(
        request_id=request_id,
        provider=provider,
        model=model,
        x402_enabled=settings.x402_enabled,
        revenue_usd=revenue_usd,
        ai_cost_usd=usage.cost_usd,
        ai_cost_known=usage.cost_known,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        total_tokens=usage.total_tokens,
        generation_id=usage.generation_id,
        vertical=req.vertical,
        geo=req.geo,
    )

    return AdIntelResponse(
        request_id=request_id,
        provider=provider,
        model=model,
        result=result,
        warning=warning,
    )


def require_admin(
    x_admin_token: str = Header(default=''),
    adintel_admin_session: str = Cookie(default=''),
):
    if valid_admin_token(settings, x_admin_token):
        return
    if verify_admin_session(settings, adintel_admin_session):
        return
    raise HTTPException(status_code=401, detail='Admin authentication required')


@app.get('/admin', response_class=HTMLResponse)
async def admin_login_page(adintel_admin_session: str = Cookie(default='')):
    if verify_admin_session(settings, adintel_admin_session):
        return RedirectResponse('/admin/dashboard', status_code=303)
    return HTMLResponse(render_admin_login(settings.app_name))


@app.post('/admin/login')
async def admin_login(x_admin_token: str = Header(default='')):
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
async def admin_logout():
    response = JSONResponse({'ok': True})
    response.delete_cookie(SESSION_COOKIE_NAME, path='/')
    return response


@app.get('/admin/stats', dependencies=[Depends(require_admin)])
async def admin_stats():
    return store.stats()


@app.get('/admin/dashboard', response_class=HTMLResponse, dependencies=[Depends(require_admin)])
async def admin_dashboard():
    return HTMLResponse(
        render_dashboard(
            store.stats(),
            service=settings.app_name,
            network=settings.x402_network,
            price=settings.x402_price,
        )
    )
