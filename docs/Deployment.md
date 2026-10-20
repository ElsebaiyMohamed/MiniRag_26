# Deployment and hardening

The Docker Compose stack is set up for easy local use. Before you expose it to other people or the internet, work through this checklist.

> **There is no authentication.** Any client that can reach the API can upload files, read indexed content, and spend your LLM provider credits. Do not expose the API publicly as-is. Put it behind a gateway, a VPN, or at minimum the Nginx basic auth shown below.

## Checklist

- [ ] Remove published ports for internal services ([Ports](#ports))
- [ ] Use strong, unique secrets and keep them out of git ([Secrets](#secrets))
- [ ] Add TLS and an upload limit to Nginx ([Nginx](#nginx))
- [ ] Add authentication in front of the API ([Authentication](#authentication))
- [ ] Choose a vector store that matches your worker count ([Workers](#workers-and-the-vector-store))
- [ ] Back up the database and the uploads volume ([Backups](#backups))
- [ ] Protect Grafana and Prometheus ([Monitoring access](#monitoring-access))

## Ports

`docker/docker-compose.yml` publishes every service to the host for convenience. In production, only Nginx should be reachable from outside. Remove the `ports:` entries for these services, because other containers reach them over the internal `bakend` network by service name:

| Service | Published today | Production |
|---|---|---|
| `nginx` | `80` | Keep (and add `443`) |
| `fastapi` | `8000` | Remove. Reach it through Nginx |
| `pgvector` | `5432` | Remove |
| `postgres-exporter` | `9187` | Remove |
| `node-exporter` | `9100` | Remove |
| `prometheus` | `9090` | Remove, or restrict to a private network |
| `grafana` | `3000` | Remove and serve through Nginx, or restrict to a private network |

If you must reach a service from the host, bind it to localhost only, for example `"127.0.0.1:5432:5432"`.

A published database port combined with a weak password is the most common way a stack like this gets compromised.

## Secrets

- Real env files (`docker/envv/.env.*`, `src/.env.app`) and both `alembic.ini` files are git-ignored. Keep it that way, and never commit them.
- Replace every placeholder password: Postgres, Grafana (`GF_SECURITY_ADMIN_PASSWORD`), and the postgres-exporter credentials.
- Use one database password in all four places listed in [Configuration](configuration.md#database-credentials-must-match-everywhere).
- Treat `COHERE_API_KEY` and `OPENAI_API_KEY` as money. Restrict them in the provider's dashboard where possible, and rotate them if they leak.
- For shared or production hosts, prefer Docker secrets or a secrets manager over plain env files.
- Keep `GF_USERS_ALLOW_SIGN_UP=false`.

## Nginx

The bundled config (`docker/nginx/default.conf`) proxies everything to `fastapi:8000` and nothing else. Two changes are needed for real use.

### Upload size

Nginx rejects request bodies above 1 MB by default, so uploads larger than that fail with `413` when sent through port 80. Set a limit at least as large as `FILE_MAX_SIZE_IN_MB`:

```nginx
server {
    listen 80;
    server_name localhost;

    client_max_body_size 10m;

    location / {
        proxy_pass http://fastapi:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Answers can take a while with slower models, so you may also want `proxy_read_timeout 120s;` inside `location /`.

### TLS

Terminate TLS at Nginx. A minimal example, assuming your certificate files are mounted into the container (for instance obtained with certbot):

```nginx
server {
    listen 80;
    server_name your.domain;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your.domain;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    client_max_body_size 10m;

    location / {
        proxy_pass http://fastapi:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Add `"443:443"` to the `nginx` ports and mount the certificates as a volume.

## Authentication

The API has no built-in auth yet (it is on the roadmap). Until it does, enforce access outside the app. The simplest option is HTTP basic auth in Nginx:

```bash
# create the password file (htpasswd comes from apache2-utils)
htpasswd -c docker/nginx/.htpasswd myuser
```

```nginx
location / {
    auth_basic "MiniRag_26";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://fastapi:8000;
    # ... proxy headers as above
}
```

Mount the file into the container, and add `docker/nginx/.htpasswd` to `.gitignore`. For anything beyond a small trusted group, use an API gateway or an identity-aware proxy instead.

## Workers and the vector store

The Docker image starts `uvicorn` with several workers (`--workers 4`). This matters for two things.

**Metrics.** Each worker keeps its own in-memory Prometheus counters, so a scrape of `/metrics` reflects whichever worker answered. See [Monitoring](monitoring.md#multiple-workers).

To change the worker count, edit the `CMD` in `docker/minirag/DockerFile` and rebuild.

## Backups

State lives in named Docker volumes. Back up the first two together, because uploaded files and database rows reference each other:

| Volume | Contents |
|---|---|
| `pgvector_data` | PostgreSQL: projects, assets, chunks, and (with pgvector) the vectors |
| `fast_api_data` | Uploaded files under `/app/assets` |
| `grafana_data`, `prometheus_data` | Dashboards and metrics history (optional) |

Logical database backup and restore:

```bash
# backup (run from docker/)
docker compose exec -T pgvector pg_dump -U postgres minirag26 > minirag26.sql

# restore into an empty database
docker compose exec -T pgvector psql -U postgres minirag26 < minirag26.sql
```

Vectors can always be rebuilt from chunks with `index/push` and `"do_reset": 1`, so the chunks and the uploaded files are the data that matters most.

## Upgrades and migrations

Database migrations run automatically on container start (`alembic upgrade head` in `entrypoint.sh`). To upgrade:

```bash
git pull
cd docker
docker compose up -d --build
```

Read `CHANGELOG.md` first. If a release changes the embedding setup, re-index your projects with `"do_reset": 1`.

## Monitoring access

Prometheus has no authentication, and Grafana is protected only by its login. Keep both on a private network, or serve Grafana through Nginx with TLS. The `/metrics` endpoint of the API is public through Nginx unless you restrict it, so consider blocking it at Nginx and letting Prometheus scrape `fastapi:8000` directly over the internal network:

```nginx
location = /metrics {
    return 404;
}
```

## Resource planning

- The API itself is light. Cost and latency come from the embedding and generation providers.
- Indexing a large project sends many embedding requests, so expect provider rate limits.
- Local models through Ollama need enough RAM or VRAM for both the generation and the embedding model.
- Postgres memory settings matter once collections grow. Keep the pgvector index threshold in mind. See [Configuration](configuration.md#vector-database).
