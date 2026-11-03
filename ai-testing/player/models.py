import os
"""The model calls. The Jev key is read at run time from Tom's .env, kept only in memory, never logged."""
import asyncio, json, os, time
import httpx

ENV = os.environ.get('OSZ_ENV_FILE', '.env')  # a file holding TYPESAFE_API_KEY=..., or set the variable itself
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jev_usage.jsonl')
USD_PER_TOKEN = 0.042 / 1_000_000      # docs.typesafe.ai/models: per input token; output is free
CAP_USD = 3.0


def jev_key():
    for line in open(ENV):
        if line.startswith('TYPESAFE_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"\'')
    raise RuntimeError('no key')


def spent_usd():
    try:
        return sum(json.loads(l)['usd'] for l in open(LEDGER))
    except FileNotFoundError:
        return 0.0


class Jev:
    def __init__(self, tag, model='jev-latest'):
        self.tag, self.model = tag, model
        self.c = httpx.AsyncClient(timeout=3.0, headers={'Authorization': 'Bearer ' + jev_key()}, limits=httpx.Limits(max_connections=2, max_keepalive_connections=2))
        self.base_spent = spent_usd(); self.spent = 0.0; self.ledger = open(LEDGER, 'a', buffering=1)
        self.calls = 0; self.tokens = 0; self.version = None

    @property
    def over_cap(self):
        return self.base_spent + self.spent >= CAP_USD

    async def ask(self, state, questions):
        t0 = time.perf_counter()
        r = await self.c.post('https://api.typesafe.ai/v1/systemone', json={'model': self.model, 'state': state, 'questions': questions})
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code != 200:
            raise RuntimeError(f'http {r.status_code}: {r.text[:200]}')
        d = r.json(); u = d.get('usage', {}); tk = u.get('input_tokens', 0)
        self.calls += 1; self.tokens += tk; usd = tk * USD_PER_TOKEN; self.spent += usd; self.version = d.get('model')
        self.ledger.write(json.dumps({'t': round(time.time(), 2), 'tag': self.tag, 'in': tk, 'out': u.get('output_tokens', 0), 'usd': usd, 'ms': round(ms, 1)}) + '\n')
        return d['answers'], ms, tk


async def claude(prompt, model, system='You answer with exactly what is asked and nothing else.', timeout=120):
    """The logged-in Claude CLI. Returns raw text, milliseconds, and the CLI's own cost estimate."""
    os.makedirs('/tmp/oszplan', exist_ok=True)
    t0 = time.perf_counter()
    p = await asyncio.create_subprocess_exec('claude', '-p', '--model', model, '--output-format', 'json', '--tools', '', '--strict-mcp-config',
                                             '--no-session-persistence', '--setting-sources', '', '--system-prompt', system, prompt,
                                             stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd='/tmp/oszplan')
    try:
        out, err = await asyncio.wait_for(p.communicate(), timeout)
    except asyncio.TimeoutError:
        p.kill(); return None, (time.perf_counter() - t0) * 1000, 0.0, 'timeout'
    ms = (time.perf_counter() - t0) * 1000
    try:
        d = json.loads(out)
        return d.get('result'), ms, d.get('total_cost_usd', 0.0), None if not d.get('is_error') else str(d.get('result'))[:200]
    except Exception:
        return None, ms, 0.0, (out[:200] + err[:200]).decode(errors='replace')
