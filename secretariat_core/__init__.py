"""UI-independent services shared by SecretariatPro's API, desktop shell and overlay."""

from .paths import AppPaths
from .state_store import StateStore
from .settings_store import AccountSettingsStore, SettingsStore
from .ocr_store import OCRConfigStore, ScoreFileStore
from .subscription_store import SubscriptionAccessStore, evaluate_subscription

__all__ = [
    "AppPaths",
    "StateStore",
    "SettingsStore",
    "AccountSettingsStore",
    "OCRConfigStore",
    "ScoreFileStore",
    "SubscriptionAccessStore",
    "evaluate_subscription",
]
