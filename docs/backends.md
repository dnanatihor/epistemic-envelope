# Optional backends

## OpenMetadata

`OpenMetadataBackend` is installed with `epistemic-envelope[openmetadata]`.
It reads tables, data-quality test cases, and column profiles over REST.

The official Docker quickstart is heavy and optional. For 1.13.4:

```bash
mkdir openmetadata-docker && cd openmetadata-docker
curl -fsSL -o docker-compose.yml \
  https://github.com/open-metadata/OpenMetadata/releases/download/1.13.4-release/docker-compose.yml
docker compose up -d
```

That starts MySQL, Elasticsearch, and the server on port 8585. The default
login is `admin@open-metadata.org` / `admin`. Paths were checked against
that version: see `docs/adr/0003-openmetadata-endpoints.md`. Tests replay
`tests/fixtures/openmetadata/` and do not call a live server.

## LLM inferences

`LLMInferenceProvider` asks a chat model for a description, a sensitivity
classification, and the observation ids it used. Those ids are kept only
when they appear in the column's observations. Tests inject a fake `invoke` method, so `langchain` is not required to run
the suite. Install the `[llm]` extra before pointing the provider at a
real chat model. The prompt asks for a JSON object with `description`,
`classification`, and `basis`. Pass a profile and the data-quality
results into `infer`; the reference server already does that.
