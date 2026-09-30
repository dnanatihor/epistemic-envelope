# Release

Pushing a tag `v*` runs `.github/workflows/release.yml`. The workflow builds
the wheel, publishes it to TestPyPI, then publishes the same build to PyPI.
Both publishes use GitHub trusted publishing (`id-token: write`). Create
`testpypi` and `pypi` environments in the repository before the first tag.

The wheel includes `schema/envelope.v0.1.json` and
`schema/labelled-object.v0.1.json` under `epienv/data/`. `load_schema`
reads the checkout when `pyproject.toml` is nearby, and the packaged files
otherwise.

This repository has not been published yet. The workflow is the release
path; running it needs the trusted-publishing environments above.
