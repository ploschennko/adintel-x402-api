import sqlite3
from pathlib import Path

from app.config import Settings
from app.storage import UsageStore


def test_economics_are_aggregated(tmp_path: Path):
    settings = Settings(database_path=str(tmp_path / 'test.sqlite3'))
    store = UsageStore(settings)
    store.record(
        request_id='abc', provider='openrouter', model='m', x402_enabled=True,
        revenue_usd=0.05, ai_cost_usd=0.007, ai_cost_known=True,
        input_tokens=100, output_tokens=200, total_tokens=300,
        generation_id='gen', vertical='saas', geo='US',
    )
    stats = store.stats()
    assert stats['successful_calls'] == 1
    assert stats['paid_mode_calls'] == 1
    assert stats['measured_paid_calls'] == 1
    assert stats['unmeasured_paid_calls'] == 0
    assert stats['configured_gross_revenue_usd'] == 0.05
    assert stats['measured_revenue_usd'] == 0.05
    assert stats['measured_ai_cost_usd'] == 0.007
    assert stats['measured_gross_profit_usd'] == 0.043
    assert stats['measured_margin_percent'] == 86.0
    assert stats['tokens']['total'] == 300


def test_old_openrouter_zero_cost_is_not_treated_as_free(tmp_path: Path):
    db = tmp_path / 'legacy.sqlite3'
    with sqlite3.connect(db) as con:
        con.execute(
            '''CREATE TABLE calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT,
                x402_enabled INTEGER NOT NULL,
                revenue_usd REAL NOT NULL,
                vertical TEXT,
                geo TEXT,
                ai_cost_usd REAL NOT NULL DEFAULT 0,
                profit_usd REAL NOT NULL DEFAULT 0,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                generation_id TEXT
            )'''
        )
        con.execute(
            '''INSERT INTO calls
               (request_id, created_at, provider, model, x402_enabled, revenue_usd,
                vertical, geo, ai_cost_usd, profit_usd, total_tokens, generation_id)
               VALUES ('legacy', '2026-10-02T00:00:00+00:00', 'openrouter', 'm', 1, 0.05,
                       'mobile app', 'US', 0, 0, 0, NULL)'''
        )
        con.commit()

    store = UsageStore(Settings(database_path=str(db)))
    store.record(
        request_id='new', provider='openrouter', model='m', x402_enabled=True,
        revenue_usd=0.05, ai_cost_usd=0.004, ai_cost_known=True,
        input_tokens=100, output_tokens=100, total_tokens=200,
        generation_id='gen-new', vertical='mobile app', geo='US',
    )

    stats = store.stats()
    assert stats['paid_mode_calls'] == 2
    assert stats['configured_gross_revenue_usd'] == 0.10
    assert stats['measured_paid_calls'] == 1
    assert stats['unmeasured_paid_calls'] == 1
    assert stats['measured_revenue_usd'] == 0.05
    assert stats['measured_ai_cost_usd'] == 0.004
    assert stats['measured_gross_profit_usd'] == 0.046
    assert stats['measured_margin_percent'] == 92.0
    legacy = next(item for item in stats['recent_calls'] if item['request_id'] == 'legacy')
    assert legacy['ai_cost_known'] == 0
