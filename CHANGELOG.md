# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Repository created from SPEC.md.
- Normative standard v0.1, JSON Schemas, and the conformance suite.
- Pydantic envelope models and `validate()` for Level 1 and Level 2.
- Envelope builder, inference policy enforcement, and deterministic LLM rendering.
- FastMCP decorator and middleware that map tool results into envelopes.
- Reference catalog server over fixture data, with static inferences.
- Optional OpenMetadata backend, checked against server 1.13.4, and an LLM inference provider with stubbed tests.
- Release workflow that publishes a tag to TestPyPI and then PyPI.
- MkDocs site and a Phase 5 README with fixture output.
- Package baseline with ruff, mypy, pytest, pre-commit, and CI.
