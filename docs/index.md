# Epistemic Envelope

Python library and MCP reference server that keep certified findings,
profiling observations, and AI inferences in separate layers.

- Standard: the normative text is `spec/SPEC-ENVELOPE.md` in the repository.
- Decisions: [FastMCP integration](adr/0001-fastmcp-integration.md), [Level 1 rules](adr/0002-level-1-rule-mapping.md), [OpenMetadata paths](adr/0003-openmetadata-endpoints.md).
- Optional backends: [OpenMetadata and LLM](backends.md).

Build this site with `uv run mkdocs build`.
