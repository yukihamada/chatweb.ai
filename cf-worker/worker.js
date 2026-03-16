// chatweb.ai Site Hosting Worker
// Serves XXXXX.chatweb.ai — static HTML from KV + dynamic API from D1

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const host = url.hostname; // e.g. my-app.chatweb.ai
    const parts = host.split('.');
    if (parts.length < 3) return new Response('Not found', { status: 404 });
    const subdomain = parts[0];

    // ── Health check ──────────────────────────────────────────────────────
    if (url.pathname === '/_health') {
      return Response.json({ ok: true, subdomain, ts: Date.now() });
    }

    // ── Site API (dynamic endpoints) ──────────────────────────────────────
    if (url.pathname.startsWith('/api/')) {
      return handleApi(req, env, subdomain, url);
    }

    // ── Static asset from KV ──────────────────────────────────────────────
    // Key: "asset:{subdomain}:{path}" (e.g. asset:myapp:/style.css)
    // Fallback: "site:{subdomain}" for index.html
    const path = url.pathname === '/' ? '' : url.pathname;
    const assetKey = path ? `asset:${subdomain}:${path}` : null;

    if (assetKey) {
      const asset = await env.SITES.getWithMetadata(assetKey);
      if (asset.value !== null) {
        const ct = asset.metadata?.contentType || guessMimeType(path);
        return new Response(asset.value, {
          headers: { 'content-type': ct, 'cache-control': 'public, max-age=3600' },
        });
      }
    }

    // Serve index.html
    const html = await env.SITES.get(`site:${subdomain}`);
    if (!html) {
      return new Response(notFoundPage(subdomain), {
        status: 404,
        headers: { 'content-type': 'text/html;charset=UTF-8' },
      });
    }

    // Increment view counter async
    env.SITES.get(`meta:${subdomain}`).then(async (raw) => {
      const meta = raw ? JSON.parse(raw) : {};
      meta.views = (meta.views || 0) + 1;
      meta.last_viewed = new Date().toISOString();
      await env.SITES.put(`meta:${subdomain}`, JSON.stringify(meta));
    }).catch(() => {});

    return new Response(html, {
      headers: {
        'content-type': 'text/html;charset=UTF-8',
        'cache-control': 'public, max-age=60',
        'x-powered-by': 'chatweb.ai',
      },
    });
  },
};

// ── Dynamic API handler ────────────────────────────────────────────────────
async function handleApi(req, env, subdomain, url) {
  const cors = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  };

  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: cors });
  }

  const endpoint = url.pathname.replace('/api/', '').replace(/^\//, '');

  try {
    // Each subdomain gets its own table in D1: {subdomain}_{collection}
    const body = req.method !== 'GET' ? await req.json().catch(() => ({})) : {};

    switch (endpoint) {
      // ── Key-Value store: GET /api/kv/:key, POST /api/kv/:key ──────────
      case endpoint.match(/^kv\//)?.input: {
        const key = endpoint.replace('kv/', '');
        const tableKey = `${subdomain}__kv`;
        if (req.method === 'GET') {
          const row = await env.DB.prepare(
            `SELECT value FROM kv_store WHERE site=? AND key=?`
          ).bind(subdomain, key).first();
          return Response.json({ key, value: row?.value ?? null }, { headers: cors });
        } else {
          await ensureKvTable(env.DB);
          await env.DB.prepare(
            `INSERT OR REPLACE INTO kv_store (site, key, value, updated_at) VALUES (?,?,?,datetime('now'))`
          ).bind(subdomain, key, JSON.stringify(body.value)).run();
          return Response.json({ ok: true }, { headers: cors });
        }
      }

      // ── Collection CRUD: GET /api/items, POST /api/items ──────────────
      default: {
        const collection = endpoint.split('/')[0] || 'items';
        const id = endpoint.split('/')[1];
        const tableName = `${subdomain}_${collection}`.replace(/[^a-z0-9_]/g, '_').slice(0, 50);

        await ensureCollectionTable(env.DB, tableName);

        if (req.method === 'GET' && !id) {
          const { results } = await env.DB.prepare(
            `SELECT * FROM "${tableName}" ORDER BY created_at DESC LIMIT 100`
          ).all();
          return Response.json({ items: results }, { headers: cors });
        }
        if (req.method === 'GET' && id) {
          const row = await env.DB.prepare(
            `SELECT * FROM "${tableName}" WHERE id=?`
          ).bind(id).first();
          return Response.json(row ?? null, { headers: cors });
        }
        if (req.method === 'POST') {
          const newId = crypto.randomUUID();
          const data = JSON.stringify(body);
          await env.DB.prepare(
            `INSERT INTO "${tableName}" (id, data, created_at) VALUES (?,?,datetime('now'))`
          ).bind(newId, data).run();
          return Response.json({ ok: true, id: newId }, { headers: cors });
        }
        if (req.method === 'PUT' && id) {
          const data = JSON.stringify(body);
          await env.DB.prepare(
            `UPDATE "${tableName}" SET data=?, updated_at=datetime('now') WHERE id=?`
          ).bind(data, id).run();
          return Response.json({ ok: true }, { headers: cors });
        }
        if (req.method === 'DELETE' && id) {
          await env.DB.prepare(`DELETE FROM "${tableName}" WHERE id=?`).bind(id).run();
          return Response.json({ ok: true }, { headers: cors });
        }
        return Response.json({ error: 'Not found' }, { status: 404, headers: cors });
      }
    }
  } catch (e) {
    return Response.json({ error: e.message }, { status: 500, headers: cors });
  }
}

async function ensureCollectionTable(db, tableName) {
  await db.prepare(`CREATE TABLE IF NOT EXISTS "${tableName}" (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT
  )`).run();
}

async function ensureKvTable(db) {
  await db.prepare(`CREATE TABLE IF NOT EXISTS kv_store (
    site TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    updated_at TEXT,
    PRIMARY KEY (site, key)
  )`).run();
}

function guessMimeType(path) {
  const ext = path.split('.').pop()?.toLowerCase();
  const map = {
    js: 'application/javascript', css: 'text/css', json: 'application/json',
    png: 'image/png', jpg: 'image/jpeg', svg: 'image/svg+xml',
    woff2: 'font/woff2', ico: 'image/x-icon', txt: 'text/plain',
  };
  return map[ext] || 'application/octet-stream';
}

function notFoundPage(subdomain) {
  return `<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8">
<title>${subdomain}.chatweb.ai — Not Found</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui,sans-serif;background:#0f0f1a;color:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;flex-direction:column;gap:20px;text-align:center;padding:20px}
h1{font-size:72px;background:linear-gradient(135deg,#7c6aff,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
p{color:#888;font-size:16px}a{color:#7c6aff;text-decoration:none;padding:12px 24px;border:1px solid #7c6aff;border-radius:8px;margin-top:8px;display:inline-block;transition:all .2s}a:hover{background:#7c6aff;color:#fff}</style>
</head><body>
<h1>404</h1>
<p><strong>${subdomain}.chatweb.ai</strong> は存在しないか削除されました。</p>
<a href="https://chatweb.ai">chatweb.ai でシステムを作る →</a>
</body></html>`;
}
