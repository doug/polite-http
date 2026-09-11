# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.3] - 2026-09-10

### Fixed

- Automatic fallback decompression for gzip-compressed responses whose
  `Content-Encoding: gzip` header was stripped or omitted by intermediate proxies
  when accessing `HttpResponse.text` or `HttpResponse.json()`.
- Relaxed rate limiter concurrency assertion in tests to accommodate timer resolution
  and scheduler variance on Windows CI runners.

## [0.1.2] - 2026-09-04

### Changed

- No functional changes. Re-release of 0.1.1 after the repository history
  was rewritten, so the PyPI provenance attestation references a commit
  that exists in the repository.

## [0.1.1] - 2026-09-03

### Fixed

- Rate limiter no longer sleeps while holding the cross-process file lock.
  The lock file now stores a reservation for the next request slot, so
  processes backing off after a 429 (or `X-Throttling-Control`) sleep
  concurrently instead of queueing behind one another and stacking their
  delays end to end. A back-off still pauses other processes for the same
  host until it elapses.

## [0.1.0] - 2026-06-16

### Added

- Initial release of `polite-http`.
- `HttpClient` with per-host cross-process rate limiting, automatic retries on
  HTTP 429/5xx and network errors, exponential backoff with jitter,
  `Retry-After` support, and `X-Throttling-Control` proactive backpressure.
- `fetch`, `fetch_json`, `fetch_bytes`, `fetch_text`, `stream_lines`, and
  `stream_bytes` request helpers.
- `HttpError` and `HttpResponse` result types.
- Cross-platform cross-process locking: `fcntl` on POSIX, `msvcrt` on Windows,
  with a best-effort in-process timer fallback where neither is available.
- Configurable lock directory via `POLITE_HTTP_LOCK_DIR`.

Derived from the `http_client.py` module in
[google-deepmind/science-skills](https://github.com/google-deepmind/science-skills)
(Apache License 2.0). See [`NOTICE`](NOTICE).

[Unreleased]: https://github.com/doug/polite-http/compare/v0.1.3...HEAD
[0.1.3]: https://github.com/doug/polite-http/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/doug/polite-http/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/doug/polite-http/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/doug/polite-http/releases/tag/v0.1.0
