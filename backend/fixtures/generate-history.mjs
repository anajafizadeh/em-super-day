// Optional sample-data generator. It does not filter or serve candidate endpoints.
import { writeFileSync } from 'node:fs';
const today = new Date();
const end = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
const fixtures = {};
for (const [id, count, value] of [['P-9001', 401, 48930], ['P-9002', 60, 500], ['P-EMPTY', 0, 0], ['P-SINGLE', 60, 2275]]) {
  fixtures[id] = Array.from({ length: count }, (_, i) => {
    const date = new Date(end);
    date.setUTCDate(date.getUTCDate() - count + 1 + i);
    return { date: date.toISOString().slice(0, 10), marketValue: Math.round(value * (0.9 + 0.1 * (i + 1) / count) * 100) / 100 };
  });
}
writeFileSync(new URL('./performance-history.json', import.meta.url), JSON.stringify(fixtures, null, 2) + '\n');
console.log('Created backend/fixtures/performance-history.json with dates ending today.');
