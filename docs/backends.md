# Optional backends

## OpenMetadata

`OpenMetadataBackend` is installed with `epistemic-envelope[openmetadata]`.
It reads tables, data-quality test cases, and column profiles over REST.
Paths come from the OpenMetadata v1.13 reference and were not verified
against a running server. See `docs/adr/0003-openmetadata-endpoints.md`.
The official Docker quickstart is the way to stand up a server; it is
heavy and optional. Tests replay `tests/fixtures/openmetadata/`.

## LLM inferences

`LLMInferenceProvider` asks a chat model for a description, a sensitivity
classification, and the observation ids it used. Those ids are kept only
when they appear in the column's observations. Tests inject a fake `invoke` method, so `langchain` is not required to run
the suite. Install the `[llm]` extra before pointing the provider at a
real chat model. The prompt asks for a JSON object with `description`,
`classification`, and `basis`. Pass a profile and the data-quality
results into `infer`; the reference server already does that.
