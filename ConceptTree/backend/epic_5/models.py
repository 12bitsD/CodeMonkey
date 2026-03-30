from pydantic import BaseModel
from typing import List


class StatsOverview(BaseModel):
    activePlans: int
    completedPlans: int
    masteredKnowledgeCount: int
    notesCount: int
    weeklyActivity: int


class DomainDistribution(BaseModel):
    domain: str
    learned: int
    total: int
    percentage: float


class StatsDistribution(BaseModel):
    distributions: List[DomainDistribution]
