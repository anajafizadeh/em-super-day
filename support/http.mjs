import { createServer } from 'node:http';

export function json(res, status, body) {
  if (res.destroyed || res.writableEnded) return;
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(body, null, 2));
}

export function serve(handler, { port, host = '127.0.0.1', name }) {
  const server = createServer(async (req, res) => {
    // These services contain fictional data and are for local development only.
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.setHeader('Cache-Control', 'no-store');
    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
    try {
      const url = new URL(req.url, 'http://localhost');
      if (req.method === 'GET' && url.pathname === '/health') {
        json(res, 200, { status: 'ok', service: name });
        return;
      }
      await handler(req, res, url);
    } catch (error) {
      json(res, error.status ?? 500, {
        error: error.status === 400 ? 'bad_request' : 'mock_error',
        message: error.status === 400 ? error.message : 'The mock could not handle this request.',
      });
      if (!error.status) console.error(error);
    }
  });
  server.on('error', error => {
    console.error(error.code === 'EADDRINUSE'
      ? `Port ${port} is busy. Stop the other service, or run this command with --port=${Number(port) + 1}.`
      : error.message);
    process.exitCode = 1;
  });
  server.listen(port, host, () => console.log(`${name}: http://${host}:${server.address().port} (Ctrl+C to stop)`));
  return server;
}

export function options(defaultPort) {
  const args = Object.fromEntries(process.argv.slice(2).map(arg => arg.replace(/^--/, '').split('=')));
  for (const key of Object.keys(args)) {
    if (!['port', 'host'].includes(key)) throw new Error(`Unknown option: ${key}. Use --port=4000 or --host=0.0.0.0.`);
  }
  const port = Number(args.port ?? defaultPort);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Port must be a number from 1 to 65535.');
  return { port, host: args.host ?? '127.0.0.1' };
}

export function badRequest(message) {
  return Object.assign(new Error(message), { status: 400 });
}

export async function readJson(req) {
  let body = '';
  for await (const chunk of req) {
    body += chunk;
    if (body.length > 4096) throw badRequest('Request body is too large.');
  }
  try { return JSON.parse(body); }
  catch { throw badRequest('Send a valid JSON body.'); }
}

export async function delay(ms, res) {
  if (res.destroyed) return;
  await new Promise(resolve => {
    const finish = () => { clearTimeout(timer); res.off('close', finish); resolve(); };
    const timer = setTimeout(finish, ms);
    res.once('close', finish);
  });
}
