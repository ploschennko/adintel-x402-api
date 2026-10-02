import sqlite3
from datetime import datetime, timezone
from threading import Lock

from .config import Settings


class UsageStore:
    def __init__(self, settings: Settings):
        self.path = settings.db_path
        self._lock = Lock()
        self._init_db()

    def _connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self):
        with self._connect() as con:
            con.execute(
                '''
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT,
                    x402_enabled INTEGER NOT NULL,
                    revenue_usd REAL NOT NULL,
                    vertical TEXT,
                    geo TEXT
                )
                '''
            )
            columns = {row['name'] for row in con.execute('PRAGMA table_info(calls)').fetchall()}
            additions = {
                'ai_cost_usd': 'REAL NOT NULL DEFAULT 0',
                'profit_usd': 'REAL NOT NULL DEFAULT 0',
                'input_tokens': 'INTEGER NOT NULL DEFAULT 0',
                'output_tokens': 'INTEGER NOT NULL DEFAULT 0',
                'total_tokens': 'INTEGER NOT NULL DEFAULT 0',
                'generation_id': 'TEXT',
                # v0.4.1: lets us distinguish an actual $0 cost from old rows
                # where cost was never measured.
                'ai_cost_known': 'INTEGER NOT NULL DEFAULT 0',
            }
            added_names: set[str] = set()
            for name, ddl in additions.items():
                if name not in columns:
                    con.execute(f'ALTER TABLE calls ADD COLUMN {name} {ddl}')
                    added_names.add(name)

            # Safe migration: v0.4 rows that contain provider usage evidence are
            # known-cost rows. Older OpenRouter rows with all-zero usage remain
            # unknown instead of being treated as free inference.
            if 'ai_cost_known' in added_names:
                con.execute(
                    '''UPDATE calls
                       SET ai_cost_known = 1
                       WHERE ai_cost_known = 0 AND (
                           COALESCE(ai_cost_usd, 0) > 0 OR
                           COALESCE(total_tokens, 0) > 0 OR
                           generation_id IS NOT NULL OR
                           provider IN ('local', 'local-demo')
                       )'''
                )
            con.commit()

    def record(
        self,
        *,
        request_id: str,
        provider: str,
        model: str | None,
        x402_enabled: bool,
        revenue_usd: float,
        ai_cost_usd: float,
        ai_cost_known: bool,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        generation_id: str | None,
        vertical: str,
        geo: str,
    ):
        profit_usd = revenue_usd - ai_cost_usd if ai_cost_known else 0.0
        with self._lock, self._connect() as con:
            con.execute(
                '''INSERT OR IGNORE INTO calls
                   (request_id, created_at, provider, model, x402_enabled, revenue_usd,
                    ai_cost_usd, profit_usd, ai_cost_known, input_tokens, output_tokens,
                    total_tokens, generation_id, vertical, geo)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    request_id,
                    datetime.now(timezone.utc).isoformat(),
                    provider,
                    model,
                    int(x402_enabled),
                    revenue_usd,
                    ai_cost_usd,
                    profit_usd,
                    int(ai_cost_known),
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    generation_id,
                    vertical,
                    geo,
                ),
            )
            con.commit()

    def stats(self) -> dict:
        with self._connect() as con:
            row = con.execute(
                '''SELECT
                    COUNT(*) AS total_calls,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 THEN 1 ELSE 0 END),0) AS paid_calls,
                    COALESCE(SUM(CASE WHEN ai_cost_known=1 THEN 1 ELSE 0 END),0) AS known_cost_calls,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN 1 ELSE 0 END),0) AS measured_paid_calls,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=0 THEN 1 ELSE 0 END),0) AS unmeasured_paid_calls,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 THEN revenue_usd ELSE 0 END),0) AS gross_revenue,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN revenue_usd ELSE 0 END),0) AS measured_revenue,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN ai_cost_usd ELSE 0 END),0) AS measured_ai_cost,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN revenue_usd-ai_cost_usd ELSE 0 END),0) AS measured_profit,
                    COALESCE(SUM(input_tokens),0) AS input_tokens,
                    COALESCE(SUM(output_tokens),0) AS output_tokens,
                    COALESCE(SUM(total_tokens),0) AS total_tokens
                   FROM calls'''
            ).fetchone()
            providers = con.execute(
                'SELECT provider, COUNT(*) AS n FROM calls GROUP BY provider ORDER BY n DESC'
            ).fetchall()
            last = con.execute(
                '''SELECT request_id, created_at, provider, model, x402_enabled,
                          revenue_usd, ai_cost_usd, profit_usd, ai_cost_known,
                          total_tokens, vertical, geo
                   FROM calls ORDER BY id DESC LIMIT 20'''
            ).fetchall()

        gross_revenue = float(row['gross_revenue'] or 0)
        measured_revenue = float(row['measured_revenue'] or 0)
        measured_ai_cost = float(row['measured_ai_cost'] or 0)
        measured_profit = float(row['measured_profit'] or 0)
        measured_paid_calls = int(row['measured_paid_calls'] or 0)
        margin = (measured_profit / measured_revenue * 100.0) if measured_revenue > 0 else 0.0
        avg_ai_cost = measured_ai_cost / measured_paid_calls if measured_paid_calls else 0.0

        return {
            'successful_calls': int(row['total_calls'] or 0),
            'paid_mode_calls': int(row['paid_calls'] or 0),
            'known_cost_calls': int(row['known_cost_calls'] or 0),
            'measured_paid_calls': measured_paid_calls,
            'unmeasured_paid_calls': int(row['unmeasured_paid_calls'] or 0),
            'configured_gross_revenue_usd': round(gross_revenue, 6),
            'measured_revenue_usd': round(measured_revenue, 6),
            'measured_ai_cost_usd': round(measured_ai_cost, 6),
            'measured_gross_profit_usd': round(measured_profit, 6),
            'measured_margin_percent': round(margin, 2),
            'average_measured_ai_cost_per_paid_call_usd': round(avg_ai_cost, 6),
            # Backward-compatible aliases. In v0.4.1 these intentionally use
            # only rows whose inference cost is actually known.
            'openrouter_cost_usd': round(measured_ai_cost, 6),
            'estimated_gross_profit_usd': round(measured_profit, 6),
            'estimated_margin_percent': round(margin, 2),
            'average_ai_cost_per_call_usd': round(avg_ai_cost, 6),
            'tokens': {
                'input': int(row['input_tokens'] or 0),
                'output': int(row['output_tokens'] or 0),
                'total': int(row['total_tokens'] or 0),
            },
            'providers': {r['provider']: r['n'] for r in providers},
            'recent_calls': [dict(r) for r in last],
            'note': (
                'Configured gross revenue counts successful protected calls at the configured x402 price. '
                'Measured revenue/cost/profit/margin include only paid calls whose AI cost was actually observed. '
                'Older OpenRouter rows without usage cost are marked N/A instead of being treated as $0. '
                'Reconcile revenue with wallet/on-chain receipts before treating it as accounting data.'
            ),
        }
