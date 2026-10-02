# One-Time File Drop

A minimal FastAPI app that creates random, single-use download links. Each link expires after a configurable time-to-live; SQLite consumes a token atomically so concurrent requests cannot download the same entry twice.

## Quick start

```bash
python -m venv .venv
python -m pip install -e .
copy .env.example .env  # Windows PowerShell: Copy-Item .env.example .env
uvicorn one_time_drop.api:app --reload
```

Upload a file from `/docs` or use `curl -F "file=@report.pdf" http://127.0.0.1:8000/v1/drops`. The response contains a URL such as `/d/<random-token>`. Configure `DROP_TTL_SECONDS`, `DROP_MAX_BYTES`, and `DROP_DATA_DIR` before running.

## Security boundaries

This is a learning project, not a hardened public file-hosting service. Run it behind HTTPS, set upload limits appropriate to the host, and add authentication, malware scanning, rate limits, quotas, and a retention policy before exposing it to the internet. A token is consumed before the download response starts; failed client downloads do not restore it. Files are removed after response completion and expired entries are pruned on startup and upload.

## Learning notes

The project demonstrates secure random tokens, streaming uploads, SQLite transactions (`BEGIN IMMEDIATE`), expiration timestamps, and Starlette background cleanup.

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

## License

MIT. See [LICENSE](LICENSE).
