"""Chooses which recommender the backend uses.

The AI engineer: when a trained model exists, load it here (once, at startup) and
return it instead. Always fall back to RuleBasedRecommender if loading fails
(requirement ML-N3: a model failure never blocks the main result).
"""

from __future__ import annotations

from .interface import Recommender
from .rule_based import RuleBasedRecommender

_recommender: Recommender | None = None


def get_recommender() -> Recommender:
    global _recommender
    if _recommender is None:
        _recommender = RuleBasedRecommender()
    return _recommender
