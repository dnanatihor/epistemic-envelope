"""Ask a chat model for a description and a sensitivity classification.

The model is injected in tests. ``langchain`` is an optional extra and is
imported only when no chat model was supplied.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast

from epienv.models import Inference

_PROMPT = """You are labelling one data column for an epistemic envelope.
Reply with a JSON object and no other text:
{{"description": "...", "classification": "...", "basis": ["observation-id"]}}
The description is one sentence. The classification says how sensitive the column is.
basis must list only observation ids you actually used, from this list: {ids}

Column: {asset_id}
Profile: {profile}
Data-quality results: {dq}
"""


@dataclass(frozen=True, slots=True)
class _Reply:
    description: str
    classification: str
    basis: tuple[str, ...]


class ChatModel(Protocol):
    """The small part of a LangChain chat model this provider calls."""

    def invoke(self, prompt: str) -> object: ...


class LLMInferenceProvider:
    """Generate a description and a classification. Basis comes from the model's reply."""

    def __init__(self, model: str = "provider/model-id", chat: ChatModel | None = None) -> None:
        self._model = model
        self._chat = chat

    def infer(
        self,
        asset_id: str,
        observation_ids: list[str],
        profile: object | None = None,
        dq: object | None = None,
    ) -> list[Inference]:
        prompt = _PROMPT.format(
            ids=", ".join(observation_ids) or "(none)",
            asset_id=asset_id,
            profile=profile,
            dq=dq,
        )
        text = _content(self._model_client().invoke(prompt))
        payload = _parse(text)
        basis = [item for item in payload.basis if item in observation_ids]
        description = payload.description
        classification = payload.classification
        generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        produced: list[Inference] = []
        if description:
            produced.append(
                Inference(
                    id="ai-1",
                    kind="description",
                    statement=description,
                    model=self._model,
                    generated_at=generated_at,
                    basis=basis,
                    review_status="unreviewed",
                )
            )
        if classification:
            produced.append(
                Inference(
                    id="ai-2" if description else "ai-1",
                    kind="classification",
                    statement=classification,
                    model=self._model,
                    generated_at=generated_at,
                    basis=basis,
                    review_status="unreviewed",
                )
            )
        return produced

    def _model_client(self) -> ChatModel:
        if self._chat is not None:
            return self._chat
        import importlib

        module = importlib.import_module("langchain.chat_models")
        created = module.init_chat_model(self._model)
        if not hasattr(created, "invoke"):
            message = "init_chat_model did not return a chat model"
            raise TypeError(message)
        chat = cast(ChatModel, created)
        self._chat = chat
        return chat


def _content(message: object) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    return str(content)


def _parse(text: str) -> _Reply:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return _Reply("", "", ())
    loaded = json.loads(text[start : end + 1])
    if not isinstance(loaded, dict):
        return _Reply("", "", ())
    basis = loaded.get("basis", [])
    kept = tuple(item for item in basis if isinstance(item, str)) if isinstance(basis, list) else ()
    description = loaded.get("description", "")
    classification = loaded.get("classification", "")
    return _Reply(
        description.strip() if isinstance(description, str) else "",
        classification.strip() if isinstance(classification, str) else "",
        kept,
    )
