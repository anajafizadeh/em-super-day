import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { readFileSync } from 'node:fs';
import { startPortfolioApi } from './portfolio-api.mjs';
import { startCrm } from '../backend/crm-service.mjs';
import { scenarios } from './portfolio-data.mjs';

async function service(t, start) {
  const server = start({ port: 0, name: 'Test mock' });
  t.after(() => new Promise(resolve => {
    server.close(resolve);
    server.closeAllConnections();
  }));
  await once(server, 'listening');
  const base = `http://127.0.0.1:${server.address().port}`;
  return {
    fetch: (path, options) => fetch(base + path, options),
    get: async path => {
      const response = await fetch(base + path);
      assert.equal(response.status, 200, path);
      return response.json();
    },
  };
}
const closeTo = (actual, expected) => assert.ok(Math.abs(actual - expected) < 0.02, `${actual} ≈ ${expected}`);

test('UI mock: every scenario has consistent accounts, totals, allocation and holding details', async t => {
  const api = await service(t, startPortfolioApi);
  for (const scenario of scenarios) {
    const query = `?scenario=${scenario}`;
    const accounts = await api.get('/accounts' + query);
    assert.equal(accounts.length, scenario === 'single-account' ? 1 : 2);
    for (const account of accounts) {
      const data = await api.get(`/portfolios/${account.accountId}${query}`);
      assert.equal(data.portfolio.totalMarketValue, account.totalMarketValue);
      closeTo(data.holdings.reduce((n, h) => n + h.marketValue, 0), account.totalMarketValue);
      closeTo(data.allocation.reduce((n, a) => n + a.value, 0), account.totalMarketValue);
      assert.ok(Number.isFinite(data.portfolio.dayChangePercent));
      assert.equal(data.performanceHistory.at(-1).date, new Date().toISOString().slice(0, 10));
      closeTo(data.performanceHistory.at(-1).marketValue, account.totalMarketValue);
      for (let i = 1; i < data.performanceHistory.length; i++) {
        assert.ok(data.performanceHistory[i - 1].date < data.performanceHistory[i].date);
      }
      for (const holding of data.holdings) {
        const detail = await api.get(`/holdings/${holding.ticker}/detail${query}`);
        assert.equal(detail.ticker, holding.ticker);
        assert.equal(detail.price, holding.price);
        closeTo(holding.quantity * holding.price, holding.marketValue);
      }
    }
  }
});

test('UI mock: advertised edge datasets and percentage units', async t => {
  const api = await service(t, startPortfolioApi);
  const data = await api.get('/portfolios/P-9001');
  assert.equal(data.portfolio.totalMarketValue, 65680);
  assert.equal(data.portfolio.dayChangeAmount, 397.25);
  assert.equal(data.portfolio.dayChangePercent, 0.61);
  assert.equal((await api.get('/portfolios/P-9001?scenario=empty')).holdings.length, 0);
  assert.equal((await api.get('/portfolios/P-9001?scenario=large')).holdings.length, 60);
  assert.equal((await api.get('/portfolios/P-9001?scenario=few-holdings')).holdings.length, 2);
  assert.equal((await api.get('/portfolios/P-9001?scenario=zero')).portfolio.dayChangeAmount, 0);
  assert.ok((await api.get('/portfolios/P-9001?scenario=negative')).portfolio.totalReturnSinceInception < 0);
  for (const [scenario, points] of [['one-point', 1], ['two-points', 2], ['short-history', 60]]) {
    assert.equal((await api.get(`/portfolios/P-9001?scenario=${scenario}`)).performanceHistory.length, points);
  }
  const gaps = (await api.get('/portfolios/P-9001?scenario=gaps')).performanceHistory;
  assert.ok(gaps.some((p, i) => i > 0 && new Date(p.date) - new Date(gaps[i - 1].date) > 86400000));
  for (const scenario of ['all-gainers', 'all-losers']) {
    const { holdings } = await api.get(`/portfolios/P-9001?scenario=${scenario}`);
    assert.ok(holdings.every(h => scenario === 'all-gainers' ? h.dayChangePercent > 0 : h.dayChangePercent < 0));
  }
  assert.equal((await api.get('/portfolios/P-9001?scenario=single-class')).allocation.length, 1);
  const tiny = await api.get('/portfolios/P-9002?scenario=tiny-allocation');
  assert.ok(tiny.allocation.find(a => a.assetClass === 'Equity').value / tiny.portfolio.totalMarketValue < 0.01);
  assert.equal((await api.get('/holdings/TSLA/detail')).dividendYield, null);
  assert.deepEqual((await api.get('/holdings/CASH/detail')).priceHistory, []);
  assert.equal((await api.get('/exchange-rate')).CADtoUSD, 0.73);
  const notification = await api.get('/notification');
  assert.equal((await api.get(`/portfolios/${notification.data.portfolioId}`)).portfolio.portfolioId, 'P-9002');
});

test('UI mock: CORS, failure recovery, loading delay, invalid inputs and unknown IDs', async t => {
  const api = await service(t, startPortfolioApi);
  const preflight = await api.fetch('/portfolios/P-9001', { method: 'OPTIONS' });
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get('access-control-allow-origin'), '*');
  for (const [path, status] of [
    ['/portfolios/P-9001?fail=true', 503], ['/portfolios/UNKNOWN', 404],
    ['/holdings/UNKNOWN/detail', 404], ['/portfolios/P-9002?scenario=single-account', 404],
    ['/accounts?scenario=typo', 400], ['/accounts?delayMs=-1', 400], ['/accounts?delayMs=oops', 400],
  ]) {
    const response = await api.fetch(path);
    assert.equal(response.status, status);
    const error = await response.json();
    assert.ok(error.error && error.message);
  }
  const start = Date.now();
  await api.get('/accounts?delayMs=100');
  assert.ok(Date.now() - start >= 90);
  assert.equal((await api.fetch('/accounts', { method: 'POST' })).status, 405);
  assert.equal((await api.get('/health')).status, 'ok');
  assert.ok((await api.get('/portfolios/P-9001')).holdings.length > 0);
});

test('CRM: legacy data matches seed holdings; null/missing and nested modes are isolated', async t => {
  const api = await service(t, startCrm);
  const seed = JSON.parse(readFileSync(new URL('../backend/fixtures/seed.json', import.meta.url), 'utf8'));
  for (const p of seed.portfolios) {
    const data = await api.get(`/crm/portfolios/${p.portfolioId}?mode=ok`);
    const account = data.client_record.accounts.find(a => a.acct_ref === p.portfolioId);
    closeTo(account.curr_val.amt, seed.holdings.filter(h => h.portfolioId === p.portfolioId).reduce((n, h) => n + h.quantity * h.price, 0));
    assert.equal(data.client_record.client_id, p.clientId);
  }
  const nested = await api.get('/crm/portfolios/P-9002?mode=nested');
  assert.ok(nested.client_record.relationships.accounts.some(a => a.acct_ref === 'P-9002'));
  assert.equal(nested.client_record.accounts, undefined);
  const missing = await api.get('/crm/portfolios/P-9001?mode=missing');
  const account = missing.client_record.accounts.find(a => a.acct_ref === 'P-9001');
  assert.equal(account.curr_val.amt, null);
  assert.equal(account.acct_nickname, undefined);
  const normal = await api.get('/crm/portfolios/P-9001?mode=ok');
  assert.equal(normal.client_record.accounts[0].curr_val.amt, 48930);
  assert.equal((await api.fetch('/crm/portfolios/UNKNOWN?mode=ok')).status, 404);
});

test('CRM: every fifth request fails; controls, counts, timeout cancellation and recovery work', async t => {
  const api = await service(t, startCrm);
  const control = mode => api.fetch('/__control', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode }) });
  for (let i = 1; i <= 9; i++) {
    assert.equal((await api.fetch('/crm/portfolios/P-9001')).status, i === 5 ? 503 : 200);
  }
  await assert.rejects(api.fetch('/crm/portfolios/P-9001', { signal: AbortSignal.timeout(100) }), { name: 'TimeoutError' });
  const stats = await api.get('/__stats');
  assert.equal(stats.calls, 10);
  assert.equal(stats.callsByPortfolio['P-9001'], 10);
  await control('error');
  assert.equal((await api.fetch('/crm/portfolios/P-9002')).status, 503);
  assert.equal((await api.fetch('/crm/portfolios/P-9002?mode=ok')).status, 200);
  await control('timeout');
  await assert.rejects(api.fetch('/crm/portfolios/P-9002', { signal: AbortSignal.timeout(100) }), { name: 'TimeoutError' });
  await control('ok');
  assert.equal((await api.fetch('/crm/portfolios/P-9002')).status, 200);
  assert.equal((await control('typo')).status, 400);
  assert.equal((await api.fetch('/__control', { method: 'POST', body: '{invalid' })).status, 400);
  assert.equal((await api.fetch('/crm/portfolios/P-9001?mode=typo')).status, 400);
  assert.equal((await api.get('/__stats')).mode, 'ok');
});
