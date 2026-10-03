// Fictional UI fixtures. This is not an implementation of the backend track.
export const scenarios = [
  'default', 'empty', 'large', 'zero', 'negative', 'large-value',
  'single-account', 'single-class', 'tiny-allocation', 'few-holdings',
  'all-gainers', 'all-losers', 'one-point', 'two-points', 'gaps', 'short-history',
];
const round = value => Math.round((value + Number.EPSILON) * 100) / 100;
const templates = [
  ['AAPL', 'Apple Inc.', 'Equity', 120, 227.50, 200, 222.17, 'Technology'],
  ['BND', 'Vanguard Total Bond ETF', 'Fixed Income', 300, 72.10, 74, 72.54, 'Bonds'],
  ['CASH', 'Canadian Dollar Cash', 'Cash', 8000, 1, 1, 1, 'Cash'],
  ['ALT', 'Example Alternative Fund', 'Alternatives', 25, 200, 180, 198, 'Diversified'],
  ['TSLA', 'Tesla Inc.', 'Equity', 15, 250, 270, 260.69, 'Automotive'],
];

export function history(value, scenario, now = new Date()) {
  const end = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  const count = scenario === 'one-point' ? 1 : scenario === 'two-points' ? 2 : scenario === 'short-history' ? 60 : 401;
  return Array.from({ length: count }, (_, i) => {
    const date = new Date(end);
    date.setUTCDate(date.getUTCDate() - (count - 1 - i));
    return { date: date.toISOString().slice(0, 10), marketValue: round(value * (0.85 + 0.15 * (i + 1) / count + (i === count - 1 ? 0 : Math.sin(i / 12) * 0.02))) };
  }).filter((_, i) => scenario !== 'gaps' || i % 7 < 4 || i === count - 1);
}

export function portfolioData(id, scenario = 'default', now = new Date()) {
  const second = id === 'P-9002';
  let rows = templates.map(row => [...row]);
  if (second) rows = [rows[0], rows[1]].map(row => { row[3] = row[3] / 2; return row; });
  if (scenario === 'empty') rows = [];
  if (scenario === 'few-holdings') rows = rows.slice(0, 2);
  if (scenario === 'single-class') rows = rows.filter(row => row[2] === 'Equity');
  if (scenario === 'tiny-allocation') rows.filter(row => row[2] === 'Equity').forEach(row => { row[3] = 0.01; });
  if (scenario === 'large-value') rows.forEach(row => { row[3] *= 1000000; });
  if (scenario === 'large') rows = Array.from({ length: 60 }, (_, i) => {
    const row = [...templates[i % templates.length]];
    row[0] = `DEMO${String(i + 1).padStart(2, '0')}`;
    row[1] = `Example Security ${i + 1}`;
    return row;
  });
  const holdings = rows.map(([ticker, name, assetClass, quantity, price, costBasisPerShare, previousClosePrice, sector]) => {
    if (scenario === 'zero') previousClosePrice = price;
    if (scenario === 'all-gainers') previousClosePrice = price / 1.02;
    if (scenario === 'negative' || scenario === 'all-losers') previousClosePrice = price / 0.98;
    return {
      ticker, name, assetClass, sector, quantity, price, costBasisPerShare,
      marketValue: round(quantity * price), gainLoss: round(quantity * (price - costBasisPerShare)),
      dayChangeAmount: round(quantity * (price - previousClosePrice)),
      dayChangePercent: round((price / previousClosePrice - 1) * 100),
    };
  });
  const totalMarketValue = round(holdings.reduce((sum, h) => sum + h.marketValue, 0));
  const dayChangeAmount = round(holdings.reduce((sum, h) => sum + h.dayChangeAmount, 0));
  holdings.forEach(h => { h.weightPercent = totalMarketValue ? round(h.marketValue / totalMarketValue * 100) : 0; });
  const allocation = Object.entries(holdings.reduce((groups, h) => {
    groups[h.assetClass] = (groups[h.assetClass] ?? 0) + h.marketValue;
    return groups;
  }, {})).map(([assetClass, value]) => ({ assetClass, value: round(value) }));
  return {
    asOf: now.toISOString(),
    portfolio: {
      portfolioId: id, accountId: id, clientId: 'abc123',
      label: second ? 'Retirement Account' : 'Taxable Brokerage', currency: 'CAD',
      totalMarketValue, dayChangeAmount,
      dayChangePercent: totalMarketValue - dayChangeAmount ? round(dayChangeAmount / (totalMarketValue - dayChangeAmount) * 100) : 0,
      totalReturnSinceInception: scenario === 'negative' ? -0.087 : scenario === 'zero' || scenario === 'empty' ? 0 : 0.187,
    },
    holdings, allocation, performanceHistory: history(totalMarketValue, scenario, now),
  };
}

export function holdingDetail(ticker, scenario, now) {
  const holding = portfolioData('P-9001', scenario, now).holdings.find(h => h.ticker === ticker);
  if (!holding) return null;
  const noHistory = holding.assetClass === 'Cash';
  return {
    ticker: holding.ticker, name: holding.name, sector: holding.sector,
    assetClass: holding.assetClass, price: holding.price, costBasisPerShare: holding.costBasisPerShare,
    purchaseDate: '2022-03-14',
    dividendYield: ['TSLA', 'CASH'].includes(ticker) || ticker.startsWith('DEMO') ? null : 0.005,
    fiftyTwoWeekLow: round(holding.price * 0.8), fiftyTwoWeekHigh: round(holding.price * 1.1),
    priceHistory: noHistory ? [] : history(holding.price, scenario, now).map(({ date, marketValue }) => ({ date, price: marketValue })),
  };
}
