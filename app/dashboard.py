from html import escape


def _money(value: float, digits: int = 4) -> str:
    return f'${float(value or 0):.{digits}f}'


def render_admin_login(service: str) -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(service)} — Admin</title>
<style>
body{{font-family:Inter,system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0;min-height:100vh;display:grid;place-items:center}}
.card{{width:min(420px,calc(100% - 36px));background:#161b22;border:1px solid #30363d;border-radius:16px;padding:24px;box-sizing:border-box}}
h1{{margin:0 0 8px;font-size:25px}}p{{color:#8b949e;line-height:1.45}}
input{{width:100%;box-sizing:border-box;background:#0d1117;color:#e6edf3;border:1px solid #30363d;border-radius:9px;padding:12px;margin:8px 0 12px}}
button{{width:100%;border:0;border-radius:9px;padding:12px;background:#238636;color:white;font-weight:700;cursor:pointer}}
.err{{color:#f85149;min-height:20px;font-size:13px;margin-top:10px}}
</style></head><body><div class="card">
<h1>{escape(service)}</h1><p>Enter the admin token. It is sent in a request header and is not placed in the URL or browser history.</p>
<form id="login"><input id="token" type="password" autocomplete="current-password" placeholder="ADMIN_TOKEN" autofocus required><button>Open dashboard</button></form>
<div class="err" id="err"></div>
<script>
document.getElementById('login').addEventListener('submit', async (event) => {{
  event.preventDefault(); const token=document.getElementById('token').value; const err=document.getElementById('err'); err.textContent='';
  const response=await fetch('/admin/login', {{method:'POST', headers:{{'X-Admin-Token':token}}}});
  if(response.ok){{ window.location='/admin/dashboard'; }} else {{ err.textContent='Invalid admin token'; }}
}});
</script></div></body></html>'''


def render_dashboard(stats: dict, *, service: str, network: str, price: str) -> str:
    recent = stats.get('recent_calls', [])
    rows = []
    for item in recent:
        known = bool(item.get('ai_cost_known'))
        ai_cost = _money(item.get('ai_cost_usd', 0), 6) if known else 'N/A'
        profit = _money(item.get('profit_usd', 0), 4) if known else 'N/A'
        token_value = str(int(item.get('total_tokens') or 0)) if known else '—'
        rows.append(
            '<tr>'
            f"<td>{escape(str(item.get('created_at', ''))[:19].replace('T', ' '))}</td>"
            f"<td>{escape(str(item.get('endpoint', '')))}</td>" f"<td>{escape(str(item.get('provider', '')))}</td>"
            f"<td>{_money(item.get('revenue_usd', 0), 4)}</td>"
            f"<td>{ai_cost}</td>"
            f"<td>{profit}</td>"
            f"<td>{token_value}</td>"
            f"<td>{escape(str(item.get('vertical', '')))}</td>"
            f"<td>{escape(str(item.get('geo', '')))}</td>"
            '</tr>'
        )
    if not rows:
        rows.append('<tr><td colspan="9">No calls recorded yet.</td></tr>')

    unknown = int(stats.get('unmeasured_paid_calls', 0))
    unknown_note = (
        f'<div class="banner">{unknown} older paid call(s) have no measured AI cost and are excluded from measured profit/margin.</div>'
        if unknown else ''
    )

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(service)} — Economics</title>
<style>
body{{font-family:Inter,system-ui,sans-serif;background:#0d1117;color:#e6edf3;margin:0;padding:28px}}
.wrap{{max-width:1260px;margin:auto}} .top{{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}} h1{{margin:0 0 6px}} .muted{{color:#8b949e}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:24px 0}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:14px;padding:18px}}
.big{{font-size:28px;font-weight:750;margin-top:5px}} .good{{color:#3fb950}} .warn{{color:#d29922}}
.banner{{background:#2d220c;border:1px solid #9e6a03;color:#e3b341;border-radius:10px;padding:10px 13px;margin:0 0 18px}}
button{{border:1px solid #30363d;background:#161b22;color:#e6edf3;border-radius:8px;padding:8px 11px;cursor:pointer}}
table{{width:100%;border-collapse:collapse;background:#161b22;border:1px solid #30363d;border-radius:12px;overflow:hidden}}
th,td{{padding:10px 12px;border-bottom:1px solid #30363d;text-align:left;font-size:13px}} th{{color:#8b949e}}
.note{{margin-top:18px;color:#8b949e;font-size:13px;line-height:1.5}}
</style></head><body><div class="wrap">
<div class="top"><div><h1>{escape(service)}</h1><div class="muted">x402 economics dashboard · {escape(network)} · {escape(price)} per paid call</div></div><button onclick="logout()">Log out</button></div>
<div class="grid">
<div class="card"><div class="muted">Successful calls</div><div class="big">{stats['successful_calls']}</div></div>
<div class="card"><div class="muted">Paid-mode calls</div><div class="big">{stats['paid_mode_calls']}</div></div>
<div class="card"><div class="muted">Configured gross revenue</div><div class="big">{_money(stats['configured_gross_revenue_usd'], 4)}</div></div>
<div class="card"><div class="muted">Measured paid calls</div><div class="big">{stats['measured_paid_calls']}</div></div>
<div class="card"><div class="muted">Measured revenue</div><div class="big">{_money(stats['measured_revenue_usd'], 4)}</div></div>
<div class="card"><div class="muted">Measured AI cost</div><div class="big warn">{_money(stats['measured_ai_cost_usd'], 6)}</div></div>
<div class="card"><div class="muted">Measured profit</div><div class="big good">{_money(stats['measured_gross_profit_usd'], 4)}</div></div>
<div class="card"><div class="muted">Measured margin</div><div class="big">{stats['measured_margin_percent']:.1f}%</div></div>
</div>
{unknown_note}
<h2>Recent calls</h2>
<table><thead><tr><th>UTC</th><th>Endpoint</th><th>Provider</th><th>Revenue</th><th>AI cost</th><th>Profit</th><th>Tokens</th><th>Vertical</th><th>GEO</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<div class="note">{escape(stats['note'])}<br>Dashboard authentication uses an HttpOnly session cookie; the ADMIN_TOKEN is never put in the URL.</div>
<script>async function logout(){{await fetch('/admin/logout',{{method:'POST'}});window.location='/admin';}}</script>
</div></body></html>'''
