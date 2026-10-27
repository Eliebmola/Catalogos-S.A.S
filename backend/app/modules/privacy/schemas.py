from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConsentStatus(BaseModel):
    accepted: bool
    policy_version: str
    accepted_at: datetime | None = None


class ConsentAcceptance(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accepted: bool
