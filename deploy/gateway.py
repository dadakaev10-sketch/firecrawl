"""Private bearer gateway. No credentials in logs; only bounded v1 crawl API."""
import hmac
import ipaddress
import json
import os
import re
import socket
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN = os.environ.get('FIRECRAWL_GATEWAY_TOKEN', '')
UPSTREAM = 'http://api:3002'
MAX_BODY = 16384


def public_url(value):
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Public HTTP(S) URL required')
    if parsed.port not in (None, 80, 443):
        raise ValueError('Only standard web ports supported')
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('Private destinations are forbidden')
    return value


def crawl_body(data):
    # Deliberately reconstruct rather than forwarding arbitrary scraper options.
    if not isinstance(data, dict) or set(data) - {'url', 'limit', 'scrapeOptions'}:
        raise ValueError('Unsupported crawl options')
    limit = data.get('limit', 10)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ValueError('Page limit must be 1..1000')
    return {'url': public_url(data['url']), 'limit': min(limit, 25), 'maxDepth': 2,
            'allowExternalLinks': False, 'allowBackwardLinks': False,
            'scrapeOptions': {'formats': ['markdown'], 'timeout': 30000}}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def reply(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Link', '<https://github.com/dadakaev10-sketch/firecrawl/tree/private-lobbystack>; rel="source"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.handle_api()

    def do_POST(self):
        self.handle_api()

    def handle_api(self):
        self.connection.settimeout(35)
        if self.path == '/health' and self.command == 'GET':
            return self.reply(200, {'ready': bool(TOKEN)})
        if not TOKEN or not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            return self.reply(401, {'error': 'Unauthorized'})
        parsed = urllib.parse.urlsplit(self.path)
        body = None
        try:
            if self.command == 'POST' and parsed.path == '/v1/crawl' and not parsed.query:
                if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise ValueError('JSON body required')
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= MAX_BODY:
                    return self.reply(413, {'error': 'Request too large'})
                body = json.dumps(crawl_body(json.loads(self.rfile.read(size)))).encode()
            elif self.command == 'GET' and re.fullmatch(r'/v1/crawl/[a-fA-F0-9-]{36}', parsed.path):
                params = urllib.parse.parse_qs(parsed.query)
                if set(params) - {'skip'} or any(not re.fullmatch(r'\d{1,6}', v) for values in params.values() for v in values):
                    raise ValueError('Invalid pagination')
            else:
                return self.reply(404, {'error': 'Not found'})
            request = urllib.request.Request(UPSTREAM + self.path, data=body,
                headers={'Content-Type': 'application/json'}, method=self.command)
            with urllib.request.urlopen(request, timeout=32) as response:
                payload = json.loads(response.read(16 * 1024 * 1024))
                if payload.get('next'):
                    next_url = urllib.parse.urlsplit(payload['next'])
                    payload['next'] = next_url.path + ('?' + next_url.query if next_url.query else '')
                self.reply(response.status, payload)
        except (ValueError, KeyError, TypeError, socket.gaierror):
            self.reply(400, {'error': 'Invalid crawl request or unsafe destination'})
        except urllib.error.HTTPError as error:
            self.reply(error.code, {'error': 'Upstream rejected request'})
        except Exception:
            self.reply(502, {'error': 'Crawl service unavailable'})


if __name__ == '__main__':
    if len(TOKEN) < 32:
        raise SystemExit('Runtime gateway token required')
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
