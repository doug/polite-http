# Contributing to polite-http

Thanks for your interest in improving polite-http! Contributions of all kinds
are welcome.

## Development setup

This project uses [uv](https://docs.astral.sh/uv/) for environment and
dependency management.

```bash
git clone https://github.com/doug/polite-http.git
cd polite-http
uv venv
uv pip install -e ".[dev]"
```

## Running the checks

The CI runs the same commands; please make sure they pass before opening a PR.

```bash
uv run pytest              # tests (fully offline — no network needed)
uv run ruff check .        # lint
uv run ruff format .       # auto-format
uv run mypy                # type-check
```

## Guidelines

- Keep the library **dependency-free** — it targets the standard library only.
  (Test/lint/type tooling lives in the `dev` optional dependency group.)
- Add tests for new behaviour. The suite uses a tiny in-process HTTP server, so
  tests should not reach the network.
- Update `CHANGELOG.md` under the `Unreleased` heading.
- Follow the existing code style (enforced by `ruff format`).

## Releasing (maintainers)

1. Bump `version` in `pyproject.toml` and `__version__` in
   `src/polite_http/__init__.py`.
2. Move the `Unreleased` changelog entries under a new version heading.
3. Tag and create a GitHub Release (e.g. `v0.1.0`). The
   [`publish`](.github/workflows/publish.yml) workflow builds the
   distributions and uploads them to PyPI via Trusted Publishing.

## License

By contributing, you agree that your contributions will be licensed under the
[Apache License 2.0](LICENSE).
