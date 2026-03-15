"""ОРД (Оператор Рекламных Данных) client — stub for future integration.

After registering a legal entity, this module will:
1. Register creatives with the ОРД API
2. Obtain ERID tokens for advertising posts
3. Submit reporting data

Currently returns mock data for development/testing.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("aizavod.ord_client")


@dataclass
class ORDCreative:
    """Represents a registered creative in ОРД."""
    creative_id: str
    erid_token: str
    status: str  # "pending", "registered", "rejected"


class ORDClient:
    """Stub client for ОРД API integration."""

    def __init__(self, api_url: str = "", api_token: str = ""):
        self._api_url = api_url
        self._api_token = api_token
        self._enabled = bool(api_url and api_token)

    @property
    def is_configured(self) -> bool:
        return self._enabled

    async def register_creative(
        self,
        advertiser_inn: str,
        campaign_name: str,
        platform: str,
        content_url: Optional[str] = None,
    ) -> ORDCreative:
        """Register a creative with ОРД and get ERID token.

        TODO: Implement real API call after legal entity registration.
        """
        if not self._enabled:
            logger.info("ОРД not configured — returning stub creative")
            return ORDCreative(
                creative_id="stub-creative-id",
                erid_token="stub-erid-token",
                status="pending",
            )

        # Future: real API call
        raise NotImplementedError("Real ОРД API integration not yet implemented")

    async def submit_report(
        self,
        creative_id: str,
        impressions: int,
        clicks: int,
        spend_rub: float,
    ) -> bool:
        """Submit advertising statistics to ОРД.

        TODO: Implement after registration.
        """
        if not self._enabled:
            logger.info("ОРД not configured — skipping report submission")
            return True

        raise NotImplementedError("Real ОРД API integration not yet implemented")


_instance: Optional[ORDClient] = None


def get_ord_client() -> ORDClient:
    global _instance
    if _instance is None:
        import os
        _instance = ORDClient(
            api_url=os.getenv("ORD_API_URL", ""),
            api_token=os.getenv("ORD_API_TOKEN", ""),
        )
    return _instance
