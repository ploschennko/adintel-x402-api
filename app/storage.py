import sqlite3
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from .config import Settings


class UsageStore:
    """Usage/economics storage with SQLite locally and Postgres in production.

    If DATABASE_URL starts with postgres:// or postgresql://, Postgres is used.
    Otherwise the existing SQLite DATABASE_PATH behavior is preserved.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.backend = settings.database_backend
        self.path = settings.db_path
        self.database_url = self._normalize_postgres_url(settings.database_url)
        self._lock = Lock()
        self._init_db()

    @staticmethod
    def _normalize_postgres_url(url: str) -> str:
        value = (url or '').strip()
        if value.startswith('postgres://'):
            return 'postgresql://' + value[len('postgres://'):]
        return value

    def _sqlite_connect(self):
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        return con

    def _pg_connect(self):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:  # pragma: no cover - dependency is in requirements
            raise RuntimeError('Postgres configured but psycopg is not installed') from exc
        return psycopg.connect(self.database_url, row_factory=dict_row, connect_timeout=8)

    def _init_db(self):
        if self.backend == 'postgres':
            self._init_postgres()
        else:
            self._init_sqlite()

    def _init_sqlite(self):
        with self._sqlite_connect() as con:
            con.execute(
                '''CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT,
                    x402_enabled INTEGER NOT NULL,
                    revenue_usd REAL NOT NULL,
                    vertical TEXT,
                    geo TEXT
                )'''
            )
            cols = {r['name'] for r in con.execute('PRAGMA table_info(calls)').fetchall()}
            additions = {
                'ai_cost_usd': 'REAL NOT NULL DEFAULT 0',
                'profit_usd': 'REAL NOT NULL DEFAULT 0',
                'input_tokens': 'INTEGER NOT NULL DEFAULT 0',
                'output_tokens': 'INTEGER NOT NULL DEFAULT 0',
                'total_tokens': 'INTEGER NOT NULL DEFAULT 0',
                'generation_id': 'TEXT',
                'ai_cost_known': 'INTEGER NOT NULL DEFAULT 0',
                'endpoint': "TEXT NOT NULL DEFAULT '/v1/ad-intel'",
                'payer': 'TEXT',
                'tx_hash': 'TEXT',
                'network': 'TEXT',
            }
            added: set[str] = set()
            for name, ddl in additions.items():
                if name not in cols:
                    con.execute(f'ALTER TABLE calls ADD COLUMN {name} {ddl}')
                    added.add(name)
            if 'ai_cost_known' in added:
                con.execute(
                    """UPDATE calls SET ai_cost_known=1
                       WHERE ai_cost_known=0 AND (
                           COALESCE(ai_cost_usd,0)>0 OR
                           COALESCE(total_tokens,0)>0 OR
                           generation_id IS NOT NULL OR
                           provider IN ('local','local-demo')
                       )"""
                )
            con.execute('CREATE INDEX IF NOT EXISTS idx_calls_created_at ON calls(created_at)')
            con.execute('CREATE INDEX IF NOT EXISTS idx_calls_endpoint ON calls(endpoint)')
            con.execute('CREATE INDEX IF NOT EXISTS idx_calls_tx_hash ON calls(tx_hash)')
            con.commit()

    def _init_postgres(self):
        with self._pg_connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    '''CREATE TABLE IF NOT EXISTS calls (
                        id BIGSERIAL PRIMARY KEY,
                        request_id TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        endpoint TEXT NOT NULL DEFAULT '/v1/ad-intel',
                        provider TEXT NOT NULL,
                        model TEXT,
                        x402_enabled INTEGER NOT NULL,
                        revenue_usd DOUBLE PRECISION NOT NULL,
                        ai_cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
                        profit_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
                        ai_cost_known INTEGER NOT NULL DEFAULT 0,
                        input_tokens BIGINT NOT NULL DEFAULT 0,
                        output_tokens BIGINT NOT NULL DEFAULT 0,
                        total_tokens BIGINT NOT NULL DEFAULT 0,
                        generation_id TEXT,
                        vertical TEXT,
                        geo TEXT,
                        payer TEXT,
                        tx_hash TEXT,
                        network TEXT
                    )'''
                )
                # Safe for a DB created by an earlier v0.5.2 preview.
                cur.execute("ALTER TABLE calls ADD COLUMN IF NOT EXISTS endpoint TEXT NOT NULL DEFAULT '/v1/ad-intel'")
                cur.execute('ALTER TABLE calls ADD COLUMN IF NOT EXISTS payer TEXT')
                cur.execute('ALTER TABLE calls ADD COLUMN IF NOT EXISTS tx_hash TEXT')
                cur.execute('ALTER TABLE calls ADD COLUMN IF NOT EXISTS network TEXT')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_calls_created_at ON calls(created_at)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_calls_endpoint ON calls(endpoint)')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_calls_tx_hash ON calls(tx_hash)')
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
        endpoint: str = '/v1/ad-intel',
        network: str | None = None,
    ):
        profit = revenue_usd - ai_cost_usd if ai_cost_known else 0.0
        created_at = datetime.now(timezone.utc)

        with self._lock:
            if self.backend == 'postgres':
                with self._pg_connect() as con:
                    with con.cursor() as cur:
                        cur.execute(
                            '''INSERT INTO calls (
                                request_id,created_at,endpoint,provider,model,x402_enabled,revenue_usd,
                                ai_cost_usd,profit_usd,ai_cost_known,input_tokens,output_tokens,total_tokens,
                                generation_id,vertical,geo,network
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (request_id) DO NOTHING''',
                            (
                                request_id, created_at, endpoint, provider, model, int(x402_enabled),
                                revenue_usd, ai_cost_usd, profit, int(ai_cost_known), input_tokens,
                                output_tokens, total_tokens, generation_id, vertical, geo, network,
                            ),
                        )
                    con.commit()
            else:
                with self._sqlite_connect() as con:
                    con.execute(
                        '''INSERT OR IGNORE INTO calls (
                            request_id,created_at,endpoint,provider,model,x402_enabled,revenue_usd,
                            ai_cost_usd,profit_usd,ai_cost_known,input_tokens,output_tokens,total_tokens,
                            generation_id,vertical,geo,network
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (
                            request_id, created_at.isoformat(), endpoint, provider, model, int(x402_enabled),
                            revenue_usd, ai_cost_usd, profit, int(ai_cost_known), input_tokens,
                            output_tokens, total_tokens, generation_id, vertical, geo, network,
                        ),
                    )
                    con.commit()

    def attach_payment(
        self,
        *,
        request_id: str,
        payer: str | None,
        tx_hash: str | None,
        network: str | None,
    ) -> None:
        if not request_id:
            return
        with self._lock:
            if self.backend == 'postgres':
                with self._pg_connect() as con:
                    with con.cursor() as cur:
                        cur.execute(
                            '''UPDATE calls
                               SET payer=COALESCE(%s,payer),
                                   tx_hash=COALESCE(%s,tx_hash),
                                   network=COALESCE(%s,network)
                               WHERE request_id=%s''',
                            (payer, tx_hash, network, request_id),
                        )
                    con.commit()
            else:
                with self._sqlite_connect() as con:
                    con.execute(
                        '''UPDATE calls
                           SET payer=COALESCE(?,payer),
                               tx_hash=COALESCE(?,tx_hash),
                               network=COALESCE(?,network)
                           WHERE request_id=?''',
                        (payer, tx_hash, network, request_id),
                    )
                    con.commit()

    def _stats_sqlite(self) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        with self._sqlite_connect() as con:
            row = con.execute(
                '''SELECT COUNT(*) total_calls,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 THEN 1 ELSE 0 END),0) paid_calls,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN 1 ELSE 0 END),0) measured_paid_calls,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=0 THEN 1 ELSE 0 END),0) unmeasured_paid_calls,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 THEN revenue_usd ELSE 0 END),0) gross_revenue,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN revenue_usd ELSE 0 END),0) measured_revenue,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN ai_cost_usd ELSE 0 END),0) measured_ai_cost,
                    COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN revenue_usd-ai_cost_usd ELSE 0 END),0) measured_profit,
                    COALESCE(SUM(input_tokens),0) input_tokens,
                    COALESCE(SUM(output_tokens),0) output_tokens,
                    COALESCE(SUM(total_tokens),0) total_tokens
                   FROM calls'''
            ).fetchone()
            last = con.execute(
                '''SELECT request_id,created_at,endpoint,provider,model,x402_enabled,revenue_usd,
                          ai_cost_usd,profit_usd,ai_cost_known,total_tokens,vertical,geo,payer,tx_hash,network
                   FROM calls ORDER BY id DESC LIMIT 20'''
            ).fetchall()
            eps = con.execute(
                '''SELECT endpoint,COUNT(*) calls,COALESCE(SUM(revenue_usd),0) revenue,
                          COALESCE(SUM(CASE WHEN ai_cost_known=1 THEN ai_cost_usd ELSE 0 END),0) ai_cost,
                          COALESCE(SUM(CASE WHEN ai_cost_known=1 THEN revenue_usd-ai_cost_usd ELSE 0 END),0) profit
                   FROM calls WHERE x402_enabled=1 GROUP BY endpoint ORDER BY revenue DESC'''
            ).fetchall()
            return dict(row), [dict(x) for x in last], [dict(x) for x in eps]

    def _stats_postgres(self) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        with self._pg_connect() as con:
            with con.cursor() as cur:
                cur.execute(
                    '''SELECT COUNT(*) AS total_calls,
                        COALESCE(SUM(CASE WHEN x402_enabled=1 THEN 1 ELSE 0 END),0) AS paid_calls,
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
                )
                row = cur.fetchone()
                cur.execute(
                    '''SELECT request_id,created_at,endpoint,provider,model,x402_enabled,revenue_usd,
                              ai_cost_usd,profit_usd,ai_cost_known,total_tokens,vertical,geo,payer,tx_hash,network
                       FROM calls ORDER BY id DESC LIMIT 20'''
                )
                last = cur.fetchall()
                cur.execute(
                    '''SELECT endpoint,COUNT(*) AS calls,COALESCE(SUM(revenue_usd),0) AS revenue,
                              COALESCE(SUM(CASE WHEN ai_cost_known=1 THEN ai_cost_usd ELSE 0 END),0) AS ai_cost,
                              COALESCE(SUM(CASE WHEN ai_cost_known=1 THEN revenue_usd-ai_cost_usd ELSE 0 END),0) AS profit
                       FROM calls WHERE x402_enabled=1 GROUP BY endpoint ORDER BY revenue DESC'''
                )
                eps = cur.fetchall()
                return dict(row), [dict(x) for x in last], [dict(x) for x in eps]

    def stats(self) -> dict[str, Any]:
        row, last, eps = self._stats_postgres() if self.backend == 'postgres' else self._stats_sqlite()

        mr = float(row['measured_revenue'] or 0)
        mp = float(row['measured_profit'] or 0)
        mc = float(row['measured_ai_cost'] or 0)
        n = int(row['measured_paid_calls'] or 0)
        return {
            'storage_backend': self.backend,
            'storage_persistent': self.backend == 'postgres',
            'successful_calls': int(row['total_calls'] or 0),
            'paid_mode_calls': int(row['paid_calls'] or 0),
            'measured_paid_calls': n,
            'unmeasured_paid_calls': int(row['unmeasured_paid_calls'] or 0),
            'configured_gross_revenue_usd': round(float(row['gross_revenue'] or 0), 6),
            'measured_revenue_usd': round(mr, 6),
            'measured_ai_cost_usd': round(mc, 6),
            'measured_gross_profit_usd': round(mp, 6),
            'measured_margin_percent': round(mp / mr * 100, 2) if mr else 0.0,
            'average_measured_ai_cost_per_paid_call_usd': round(mc / n, 6) if n else 0.0,
            'tokens': {
                'input': int(row['input_tokens'] or 0),
                'output': int(row['output_tokens'] or 0),
                'total': int(row['total_tokens'] or 0),
            },
            'recent_calls': last,
            'by_endpoint': eps,
            'note': (
                'Revenue uses the configured price of the endpoint that was called. '
                'Measured economics include only rows whose AI cost was observed. '
                'x402 payer/transaction metadata is attached when the payment-response header is available. '
                'Reconcile with on-chain receipts for accounting.'
            ),
        }
