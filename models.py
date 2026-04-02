from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ResourceContribution(BaseModel):
    metal: int = 0
    healers: int = 0
    leather: int = 0
    wood: int = 0
    weapon: int = 0


class ResourceConsumption(BaseModel):
    metal: int = 0
    magic: int = 0
    wood: int = 0


class ActivityCompletion(BaseModel):
    gathering: int = 0
    combat: int = 0
    crafting: int = 0


class ProfessionCompletion(BaseModel):
    healer: int = 0
    weapon_crafter: int = 0
    gatherer: int = 0


class Stats(BaseModel):
    resource_contribution: ResourceContribution = Field(default_factory=ResourceContribution)
    resource_consumption: ResourceConsumption = Field(default_factory=ResourceConsumption)
    activity_completion: ActivityCompletion = Field(default_factory=ActivityCompletion)
    profession_completion: ProfessionCompletion = Field(default_factory=ProfessionCompletion)


class UserData(BaseModel):
    user_id: str
    crafting_class: str
    combat_class: str
    has_started_gathering: bool = False
    has_started_crafting: bool = False
    has_started_combat: bool = False
    gathering_ended_at: Optional[datetime] = None
    crafting_ended_at: Optional[datetime] = None
    combat_ended_at: Optional[datetime] = None
    stats: Stats = Field(default_factory=Stats)
    xp: int = 0
    level: int = 0
    class_selected_at: Optional[datetime] = None


class Changes(BaseModel):
    model_config = {"extra": "allow"}

    def nonzero(self) -> dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if isinstance(v, (int, float)) and v != 0}


class GameResponse(BaseModel):
    user_data: UserData
    changes: Changes


class ErrorResponse(BaseModel):
    message: str
    code: int
