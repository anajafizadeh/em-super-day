import { serve, json, delay } from './http.mjs';
import { scenarios, portfolioData, holdingDetail } from './portfolio-data.mjs';

export function startPortfolioApi(options) {
  return serve(async (req, res, url) => {
    if (req.method !== 'GET') return json(res, 405, { error: 'method_not_allowed', message: 'Use GET.' });
    const scenario = url.searchParams.get('scenario') ?? 'default';
    if (!scenarios.includes(scenario)) return json(res, 400, { error: 'invalid_scenario', message: 'Use a scenario from /scenarios.' });
    const delayMs = Number(url.searchParams.get('delayMs') ?? 0);
    if (!Number.isInteger(delayMs) || delayMs < 0 || delayMs > 10000) return json(res, 400, { error: 'invalid_delay', message: 'delayMs must be 0–10000.' });
    await delay(delayMs, res);
    if (url.searchParams.get('fail') === 'true') return json(res, 503, { error: 'unavailable', message: 'Simulated network failure. Remove fail=true to recover.' });
    const ids = scenario === 'single-account' ? ['P-9001'] : ['P-9001', 'P-9002'];
    const now = new Date();
    if (url.pathname === '/' || url.pathname === '/scenarios') return json(res, 200, {
      scenarios, routes: ['/health', '/accounts', '/portfolios/P-9001', '/holdings/AAPL/detail', '/exchange-rate', '/notification'],
    });
    if (url.pathname === '/accounts') return json(res, 200, ids.map(id => {
      const { portfolio } = portfolioData(id, scenario, now);
      return { accountId: id, label: portfolio.label, totalMarketValue: portfolio.totalMarketValue };
    }));
    if (url.pathname === '/exchange-rate') return json(res, 200, { CADtoUSD: 0.73 });
    if (url.pathname === '/notification') return json(res, 200, {
      title: 'Portfolio Alert', body: 'Your portfolio has been updated',
      data: { portfolioId: 'P-9002', type: 'portfolio_alert' },
    });
    const portfolioMatch = /^\/portfolios\/([^/]+)$/.exec(url.pathname);
    if (portfolioMatch && ids.includes(portfolioMatch[1])) return json(res, 200, portfolioData(portfolioMatch[1], scenario, now));
    const detailMatch = /^\/holdings\/([^/]+)\/detail$/.exec(url.pathname);
    if (detailMatch) {
      const detail = holdingDetail(detailMatch[1], scenario, now);
      if (detail) return json(res, 200, detail);
    }
    return json(res, 404, { error: 'not_found', message: 'Unknown route, portfolio or holding. Open / to see available routes.' });
  }, options);
}
