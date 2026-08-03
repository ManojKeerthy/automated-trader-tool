"""Research Graveyard Manager for M3B Strategy Rejections.

Persists rejected strategy configurations, failure evidence, and explicit reason codes
to prevent repeated testing of previously failed hypotheses.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from tradecraft.core.db_models import ResearchGraveyardModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GraveyardEntry:
    strategy_id: str
    strategy_family: str
    strategy_version: str
    configuration_hash: str
    parameters: dict[str, Any]
    rejection_reason_code: str
    rejection_details: dict[str, Any]
    stage_failed: str
    git_commit_hash: str | None = None


def compute_configuration_hash(strategy_id: str, parameters: dict[str, Any]) -> str:
    """Computes deterministic SHA256 hash for a strategy parameter configuration."""
    clean_params = {k: v for k, v in sorted(parameters.items())}
    raw = f"{strategy_id}:{json.dumps(clean_params, sort_keys=True)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class ResearchGraveyardManager:
    """Manages rejection persistence in the research graveyard."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def record_rejection(
        self,
        strategy_id: str,
        strategy_family: str,
        strategy_version: str,
        parameters: dict[str, Any],
        rejection_reason_code: str,
        rejection_details: dict[str, Any],
        stage_failed: str,
        git_commit_hash: str | None = None,
    ) -> ResearchGraveyardModel:
        """Persists a rejected strategy configuration to the research graveyard."""
        config_hash = compute_configuration_hash(strategy_id, parameters)

        # Check if already recorded
        existing = self.db.scalars(
            sa.select(ResearchGraveyardModel).where(
                sa.and_(
                    ResearchGraveyardModel.strategy_id == strategy_id,
                    ResearchGraveyardModel.configuration_hash == config_hash,
                )
            )
        ).first()

        if existing:
            logger.info(f"Strategy {strategy_id} ({config_hash[:8]}) already in graveyard.")
            return existing

        entry = ResearchGraveyardModel(
            id=uuid.uuid4(),
            strategy_id=strategy_id,
            strategy_family=strategy_family,
            strategy_version=strategy_version,
            configuration_hash=config_hash,
            parameters_json=parameters,
            rejection_reason_code=rejection_reason_code,
            rejection_details=rejection_details,
            stage_failed=stage_failed,
            git_commit_hash=git_commit_hash,
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        logger.info(
            f"Recorded rejection in graveyard: {strategy_id} ({config_hash[:8]}) - Reason: {rejection_reason_code}"
        )
        return entry

    def is_rejected(self, strategy_id: str, parameters: dict[str, Any]) -> bool:
        """Check if a strategy configuration was previously rejected."""
        config_hash = compute_configuration_hash(strategy_id, parameters)
        count = self.db.scalar(
            sa.select(sa.func.count(ResearchGraveyardModel.id)).where(
                sa.and_(
                    ResearchGraveyardModel.strategy_id == strategy_id,
                    ResearchGraveyardModel.configuration_hash == config_hash,
                )
            )
        )
        return bool(count and count > 0)

    def get_all_rejections(self) -> list[ResearchGraveyardModel]:
        """Fetch all graveyard entries."""
        return list(
            self.db.scalars(
                sa.select(ResearchGraveyardModel).order_by(ResearchGraveyardModel.created_at.desc())
            ).all()
        )
