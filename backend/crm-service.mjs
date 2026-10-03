import { readFileSync } from 'node:fs';
import { serve, json, readJson, delay, badRequest } from '../support/http.mjs';
const seed = JSON.parse(readFileSync(new URL('./fixtures/seed.json', import.meta.url), 'utf8'));
// CRM fixture values, not candidate valuation/calculation code.
const metadata = {
  'P-9001': { amt: 48930, change: 30, pct: 30 / 48900, inception: 0.187 },
  'P-9002': { amt: 500, change: 500, pct: 0, inception: 0.25 },
  'P-EMPTY': { amt: 0, change: 0, pct: 0, inception: 0 },
  'P-SINGLE': { amt: 2275, change: 25, pct: 25 / 2250, inception: 0.1375 },
};
const modes = ['auto', 'ok', 'error', 'timeout', 'missing', 'nested'];

export function startCrm(options) {
  let mode = 'auto';
  let calls = 0;
  const callsByPortfolio = {};
  return serve(async (req, res, url) => {
    if (req.method === 'GET' && url.pathname === '/__stats') return json(res, 200, { mode, calls, callsByPortfolio });
    if (req.method === 'POST' && url.pathname === '/__control') {
      const body = await readJson(req);
      if (!body || !modes.includes(body.mode)) throw badRequest(`mode must be one of: ${modes.join(', ')}`);
      mode = body.mode;
      return json(res, 200, { mode, calls });
    }
    if (req.method !== 'GET') return json(res, 405, { error: 'method_not_allowed', message: 'Use GET, or POST /__control.' });
    if (url.pathname === '/') return json(res, 200, { routes: ['/crm/portfolios/P-9001', '/__stats', '/health'], modes });
    const match = /^\/crm\/portfolios\/([^/]+)$/.exec(url.pathname);
    if (!match) return json(res, 404, { error: 'not_found', message: 'Use /crm/portfolios/P-9001.' });
    const selected = url.searchParams.get('mode') ?? mode;
    if (!modes.includes(selected)) throw badRequest(`mode must be one of: ${modes.join(', ')}`);
    const id = match[1];
    calls += 1;
    callsByPortfolio[id] = (callsByPortfolio[id] ?? 0) + 1;
    const behavior = selected === 'auto' ? (calls % 5 === 0 ? (calls % 10 === 0 ? 'timeout' : 'error') : 'ok') : selected;
    console.log(`CRM call ${calls}: ${id} (${behavior})`);
    if (behavior === 'error') return json(res, 503, { error: 'legacy_unavailable', message: 'Simulated CRM outage.' });
    if (behavior === 'timeout') {
      await delay(10000, res);
      return json(res, 504, { error: 'legacy_timeout', message: 'CRM took 10 seconds. Your backend should time out sooner.' });
    }
    const portfolio = seed.portfolios.find(p => p.portfolioId === id);
    if (!portfolio) return json(res, 404, { error: 'unknown_account', message: 'No CRM account has this reference.' });
    const client = seed.clients.find(c => c.clientId === portfolio.clientId);
    // Return the client's other accounts too; callers must select by acct_ref.
    const accounts = seed.portfolios.filter(p => p.clientId === client.clientId).map(p => {
      const value = metadata[p.portfolioId];
      return {
        acct_ref: p.portfolioId, acct_nickname: p.label,
        curr_val: { amt: value.amt, ccy: p.currency },
        chg_1d: { amt: value.change, pct: value.pct }, since_inception_pct: value.inception,
      };
    });
    const record = { client_id: client.clientId, full_name: client.name, accounts };
    if (behavior === 'missing') {
      const account = accounts.find(a => a.acct_ref === id);
      account.curr_val.amt = null;
      delete account.acct_nickname;
    }
    const payload = {
      client_record: record,
      meta: { retrieved_at: new Date().toISOString(), source: 'legacy-crm-v2' },
    };
    // Explicit alternative fixture for the documented inconsistent nesting.
    if (behavior === 'nested') {
      delete record.accounts;
      record.relationships = { accounts };
    }
    return json(res, 200, payload);
  }, { name: 'Mock CRM', ...options });
}
