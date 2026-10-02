import sqlite3
from datetime import datetime, timezone
from threading import Lock
from .config import Settings

class UsageStore:
    def __init__(self, settings:Settings): self.path=settings.db_path; self._lock=Lock(); self._init_db()
    def _connect(self):
        c=sqlite3.connect(self.path); c.row_factory=sqlite3.Row; return c
    def _init_db(self):
        with self._connect() as con:
            con.execute('''CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY AUTOINCREMENT,request_id TEXT UNIQUE NOT NULL,created_at TEXT NOT NULL,provider TEXT NOT NULL,model TEXT,x402_enabled INTEGER NOT NULL,revenue_usd REAL NOT NULL,vertical TEXT,geo TEXT)''')
            cols={r['name'] for r in con.execute('PRAGMA table_info(calls)').fetchall()}
            additions={'ai_cost_usd':'REAL NOT NULL DEFAULT 0','profit_usd':'REAL NOT NULL DEFAULT 0','input_tokens':'INTEGER NOT NULL DEFAULT 0','output_tokens':'INTEGER NOT NULL DEFAULT 0','total_tokens':'INTEGER NOT NULL DEFAULT 0','generation_id':'TEXT','ai_cost_known':'INTEGER NOT NULL DEFAULT 0','endpoint':"TEXT NOT NULL DEFAULT '/v1/ad-intel'"}
            added=set()
            for n,d in additions.items():
                if n not in cols: con.execute(f'ALTER TABLE calls ADD COLUMN {n} {d}'); added.add(n)
            if 'ai_cost_known' in added:
                con.execute("""UPDATE calls SET ai_cost_known=1 WHERE ai_cost_known=0 AND (COALESCE(ai_cost_usd,0)>0 OR COALESCE(total_tokens,0)>0 OR generation_id IS NOT NULL OR provider IN ('local','local-demo'))""")
            con.commit()
    def record(self,*,request_id,provider,model,x402_enabled,revenue_usd,ai_cost_usd,ai_cost_known,input_tokens,output_tokens,total_tokens,generation_id,vertical,geo,endpoint='/v1/ad-intel'):
        profit=revenue_usd-ai_cost_usd if ai_cost_known else 0.0
        with self._lock,self._connect() as con:
            con.execute('''INSERT OR IGNORE INTO calls (request_id,created_at,endpoint,provider,model,x402_enabled,revenue_usd,ai_cost_usd,profit_usd,ai_cost_known,input_tokens,output_tokens,total_tokens,generation_id,vertical,geo) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(request_id,datetime.now(timezone.utc).isoformat(),endpoint,provider,model,int(x402_enabled),revenue_usd,ai_cost_usd,profit,int(ai_cost_known),input_tokens,output_tokens,total_tokens,generation_id,vertical,geo)); con.commit()
    def stats(self):
        with self._connect() as con:
            r=con.execute('''SELECT COUNT(*) total_calls,COALESCE(SUM(CASE WHEN x402_enabled=1 THEN 1 ELSE 0 END),0) paid_calls,COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN 1 ELSE 0 END),0) measured_paid_calls,COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=0 THEN 1 ELSE 0 END),0) unmeasured_paid_calls,COALESCE(SUM(CASE WHEN x402_enabled=1 THEN revenue_usd ELSE 0 END),0) gross_revenue,COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN revenue_usd ELSE 0 END),0) measured_revenue,COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN ai_cost_usd ELSE 0 END),0) measured_ai_cost,COALESCE(SUM(CASE WHEN x402_enabled=1 AND ai_cost_known=1 THEN revenue_usd-ai_cost_usd ELSE 0 END),0) measured_profit,COALESCE(SUM(input_tokens),0) input_tokens,COALESCE(SUM(output_tokens),0) output_tokens,COALESCE(SUM(total_tokens),0) total_tokens FROM calls''').fetchone()
            last=con.execute('''SELECT request_id,created_at,endpoint,provider,model,x402_enabled,revenue_usd,ai_cost_usd,profit_usd,ai_cost_known,total_tokens,vertical,geo FROM calls ORDER BY id DESC LIMIT 20''').fetchall()
            eps=con.execute('''SELECT endpoint,COUNT(*) calls,COALESCE(SUM(revenue_usd),0) revenue,COALESCE(SUM(CASE WHEN ai_cost_known=1 THEN ai_cost_usd ELSE 0 END),0) ai_cost,COALESCE(SUM(CASE WHEN ai_cost_known=1 THEN revenue_usd-ai_cost_usd ELSE 0 END),0) profit FROM calls WHERE x402_enabled=1 GROUP BY endpoint ORDER BY revenue DESC''').fetchall()
        mr=float(r['measured_revenue'] or 0); mp=float(r['measured_profit'] or 0); mc=float(r['measured_ai_cost'] or 0); n=int(r['measured_paid_calls'] or 0)
        return {'successful_calls':int(r['total_calls'] or 0),'paid_mode_calls':int(r['paid_calls'] or 0),'measured_paid_calls':n,'unmeasured_paid_calls':int(r['unmeasured_paid_calls'] or 0),'configured_gross_revenue_usd':round(float(r['gross_revenue'] or 0),6),'measured_revenue_usd':round(mr,6),'measured_ai_cost_usd':round(mc,6),'measured_gross_profit_usd':round(mp,6),'measured_margin_percent':round(mp/mr*100,2) if mr else 0.0,'average_measured_ai_cost_per_paid_call_usd':round(mc/n,6) if n else 0.0,'tokens':{'input':int(r['input_tokens'] or 0),'output':int(r['output_tokens'] or 0),'total':int(r['total_tokens'] or 0)},'recent_calls':[dict(x) for x in last],'by_endpoint':[dict(x) for x in eps],'note':'Revenue uses the configured price of the endpoint that was called. Measured economics include only rows whose AI cost was observed. Reconcile with on-chain receipts for accounting.'}
