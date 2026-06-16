# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-16

### Added

- Initial release of `polite-http`.
- `HttpClient` with per-host cross-process rate limiting, automatic retries on
  HTTP 429/5xx and network errors, exponential backoff with jitter,
  `Retry-After` support, and `X-Throttling-Control` proactive backpressure.
- `fetch`, `fetch_json`, `fetch_bytes`, `fetch_text`, `stream_lines`, and
  `stream_bytes` request helpers.
- `HttpError` and `HttpResponse` result types.
- Optional `fcntl` so the package imports and runs on platforms without it.
- Configurable lock directory via `POLITE_HTTP_LOCK_DIR`.

Derived from the `http_client.py` module in
[google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
(Apache License 2.0). See [`NOTICE`](NOTICE).

[Unreleased]: https://github.com/doug/polite-http/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/doug/polite-http/releases/tag/v0.1.0
