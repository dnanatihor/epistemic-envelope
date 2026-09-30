"""Epistemic envelope: separate certified, observed, and inferred claims."""

from epienv.builder import DEFAULT_NOTICE, EnvelopeBuilder, EnvelopeError
from epienv.enforce import InferencePolicy, enforce, enforce_labelled
from epienv.models import (
    CertifiedFinding,
    CuratedStatement,
    Envelope,
    Inference,
    Observation,
    Subject,
)
from epienv.render import to_llm_context
from epienv.validate import Violation, validate

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_NOTICE",
    "CertifiedFinding",
    "CuratedStatement",
    "Envelope",
    "EnvelopeBuilder",
    "EnvelopeError",
    "Inference",
    "InferencePolicy",
    "Observation",
    "Subject",
    "Violation",
    "__version__",
    "enforce",
    "enforce_labelled",
    "to_llm_context",
    "validate",
]
