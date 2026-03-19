"""Feature Flags — Redis-based per-tenant feature toggles.

P0 4.7: Canary release / Feature flags.
ГОСТ РВ 0015-002-2020: управление конфигурацией.
DO-178C: Configuration Management & Baselines.

Usage:
    from services.feature_flags import get_flags
    flags = get_flags()
    if flags.is_enabled("new_qa_pipeline", tenant_id="tenant_123"):
        # new code path
    else:
        # old code path
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger("aizavod.feature_flags")


# Default flags — enabled for all tenants
DEFAULT_FLAGS: dict[str, dict] = {
    "qa_mandatory_gate": {
        "enabled": True,
        "description": "QA-AGENT is mandatory in pipeline (V&V gate, DO-178C)",
        "rollout_pct": 100,
    },
    "parallel_dispatch": {
        "enabled": False,
        "description": "Parallel execution of independent agents in orchestration",
        "rollout_pct": 0,
    },
    "progress_streaming": {
        "enabled": False,
        "description": "UX progress streaming to Telegram",
        "rollout_pct": 0,
    },
    "json_logging": {
        "enabled": True,
        "description": "JSON structured logging to file",
        "rollout_pct": 100,
    },
    "session_tracing": {
        "enabled": True,
        "description": "Full session tracing with correlation_id",
        "rollout_pct": 100,
    },
    "extended_thinking": {
        "enabled": False,
        "description": "Claude Extended Thinking for complex tasks",
        "rollout_pct": 0,
    },
}


class FeatureFlags:
    """Redis-based feature flag system with per-tenant overrides."""

    REDIS_PREFIX = "ff:"

    def __init__(self):
        self._redis = None
        self._local_cache: dict[str, dict] = dict(DEFAULT_FLAGS)

    def _get_redis(self):
        if self._redis is None:
            try:
                import redis
                self._redis = redis.from_url(
                    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                    socket_timeout=2,
                    decode_responses=True,
                )
                self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    def is_enabled(self, flag_name: str, tenant_id: str = "default") -> bool:
        """Check if a feature flag is enabled for a tenant."""
        # Check tenant-specific override first
        r = self._get_redis()
        if r:
            try:
                # Tenant override: ff:tenant_id:flag_name
                override = r.get(f"{self.REDIS_PREFIX}{tenant_id}:{flag_name}")
                if override is not None:
                    return override == "1"

                # Global flag from Redis
                global_val = r.get(f"{self.REDIS_PREFIX}global:{flag_name}")
                if global_val is not None:
                    return global_val == "1"
            except Exception:
                pass

        # Fallback to local defaults
        flag = self._local_cache.get(flag_name, {})
        return flag.get("enabled", False)

    def set_flag(self, flag_name: str, enabled: bool, tenant_id: str = "global") -> bool:
        """Set a feature flag value."""
        r = self._get_redis()
        if r:
            try:
                key = f"{self.REDIS_PREFIX}{tenant_id}:{flag_name}"
                r.set(key, "1" if enabled else "0")
                logger.info("FLAG SET: %s=%s (tenant=%s)", flag_name, enabled, tenant_id)
                return True
            except Exception as e:
                logger.warning("Failed to set flag %s: %s", flag_name, e)
        # Fallback: update local cache
        if flag_name in self._local_cache:
            self._local_cache[flag_name]["enabled"] = enabled
        return False

    def get_all_flags(self, tenant_id: str = "default") -> dict[str, bool]:
        """Get all flags with their current state for a tenant."""
        result = {}
        for name in DEFAULT_FLAGS:
            result[name] = self.is_enabled(name, tenant_id)
        return result

    def get_flag_info(self) -> list[dict]:
        """Get all flag definitions with descriptions."""
        return [
            {
                "name": name,
                "description": info.get("description", ""),
                "default_enabled": info.get("enabled", False),
                "rollout_pct": info.get("rollout_pct", 0),
            }
            for name, info in DEFAULT_FLAGS.items()
        ]


# Singleton
_flags: FeatureFlags | None = None


def get_flags() -> FeatureFlags:
    global _flags
    if _flags is None:
        _flags = FeatureFlags()
    return _flags
