# Private Firecrawl for LobbyStack

## Authorized rollout
1. Measure VPS capacity, pin official stable source and preserve license.
2. Build a dedicated backend (API harness, Playwright, Redis, RabbitMQ, NuQ PostgreSQL); no FoundationDB. Constrain builder to 4 GiB and 2 CPUs.
3. Expose only bearer gateway to a dedicated integration network containing LobbyStack worker. No public ports, domains, proxy changes or cloud keys.
4. Runtime secrets in Coolify only; git-backed own-account fork and webhook.
5. Verify negative auth/SSRF checks, actual asynchronous dadakaev.com crawl, worker config, public HTTPS and unchanged onboarding.

## Version and license
Official release v2.11.0, source ef12eb36b2f3382838dfe0a0c1a5add3d5df7fe5.
Upstream Firecrawl/Mendable copyright, README, LICENSE and source remain intact. GNU AGPLv3: retain notices and license; offer corresponding running source to network users when required by section 13, including deployment modifications. Source: https://github.com/dadakaev10-sketch/firecrawl/tree/private-lobbystack . Firecrawl remains a separate API process, not copied into LobbyStack. This is not a legal opinion; commercial product counsel should review network-use obligations.

## Security and limits
- Dedicated backend network: databases and browser never join shared proxy network.
- Only gateway and LobbyStack worker join lobby-firecrawl-integration.
- USE_DB_AUTHENTICATION=false is the upstream selfhost baseline, NOT bearer enforcement. Gateway performs constant-time authentication with a centrally configured runtime secret.
- Gateway permits only POST /v1/crawl and GET /v1/crawl/<uuid>; excludes extraction, search, batch, webhook and admin routes.
- Rejects nonpublic DNS results, non-HTTP URLs, credentials and nonstandard ports. Upstream ALLOW_LOCAL_WEBHOOKS=false preserves socket-address checks for fetch and per-request/redirect checks for Playwright.
- No paid AI keys, commercial proxies, signup or cloud scraping engines.
- One browser page and one actual `NUQ_WORKER_COUNT=1` scraper worker; the legacy concurrency variables in upstream Compose are not relied on. At most 25 pages (full imports are clamped from LobbyStack 50), depth 2, 30-second per-page timeout. LobbyStack default crawl polling deadline remains 5 minutes.
- NuQ uses the `postgres` database required by the image's `cron.database_name`; readiness verifies its queue schema, not only a listening socket. WAL command overrides cap max/min at 1 GiB/128 MiB instead of upstream cloud-scale defaults. A fresh disposable database was exercised and removed.
- Memory caps: API 3 GiB, browser 1 GiB, PostgreSQL 512 MiB, RabbitMQ 512 MiB, Redis 256 MiB, gateway 128 MiB; no extra swap permitted. Redis noeviction and AOF, named PostgreSQL/RabbitMQ volumes, rotated logs and unless-stopped policies.
- Existing tenant authorization and bounded onboarding page limits stay unchanged. No claims that embeddings are configured.

## Operations
Runtime variables: FIRECRAWL_POSTGRES_PASSWORD, FIRECRAWL_BULL_AUTH_KEY, FIRECRAWL_GATEWAY_TOKEN; LobbyStack FIRECRAWL_API_KEY must equal gateway token, FIRECRAWL_BASE_URL=http://lobby-firecrawl-private:8080.
Build uses secret-free docker-compose.build.yml. Deploy uses docker-compose.coolify.yml. Do not run a second manual Compose deployment or restart Caddy.

Rollback: restore LobbyStack compose to c3e592390b7c46e4b33934563d87c6e5fe3eb0c7 and redeploy that resource only; stop the private Firecrawl application in Coolify, preserve volumes. Missing Firecrawl remains an explicit import configuration error.
