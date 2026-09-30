"""LLM inference provider with an injected chat model. No network."""

from __future__ import annotations

from examples.catalog_server.inference.llm import LLMInferenceProvider


class _StubChat:
    def __init__(self, text: str) -> None:
        self.text = text
        self.prompts: list[str] = []

    def invoke(self, prompt: str) -> object:
        self.prompts.append(prompt)
        return type("Message", (), {"content": self.text})()


def test_keeps_only_cited_observation_ids() -> None:
    chat = _StubChat(
        "{"
        '"description": "Holds contact emails", '
        '"classification": "personal", '
        '"basis": ["po-1", "po-missing"]'
        "}"
    )
    provider = LLMInferenceProvider(model="stub/model", chat=chat)
    produced = provider.infer("col_email", ["po-1"], profile={"null_pct": 0.02}, dq=[])
    assert chat.prompts[0].count("po-1") >= 1
    assert [item.kind for item in produced] == ["description", "classification"]
    assert produced[0].statement == "Holds contact emails"
    assert produced[1].statement == "personal"
    assert produced[0].basis == ["po-1"]
    assert produced[1].basis == ["po-1"]
    assert produced[0].model == "stub/model"
    assert produced[0].review_status == "unreviewed"


def test_empty_reply_emits_nothing() -> None:
    provider = LLMInferenceProvider(chat=_StubChat("not json"))
    assert provider.infer("col_email", ["po-1"]) == []
