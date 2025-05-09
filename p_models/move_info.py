from typing import List, Dict, Optional, Literal, Union
from p_models.types import FieldType, WeatherType
from p_models.status import StatusState
from p_models.rank_state import RankStat

# 타입 정의
ScreenType = Optional[Literal['빛의장막', '리플렉터', '오로라베일']]

class StatChange:
    def __init__(self, stat: str, stages: int):
        self.stat = stat
        self.stages = stages

class MoveEffect:
    def __init__(
        self,
        stat_changes: Optional[List[StatChange]] = None,
        status_effect: Optional[str] = None,
        weather: Optional[str] = None,
        field: Optional[str] = None,
        recoil: Optional[float] = None,
        drain: Optional[float] = None,
        flinch_chance: Optional[float] = None,
        multi_hit: Optional[tuple] = None,
        priority: int = 0
    ):
        self.stat_changes = stat_changes or []
        self.status_effect = status_effect
        self.weather = weather
        self.field = field
        self.recoil = recoil
        self.drain = drain
        self.flinch_chance = flinch_chance
        self.multi_hit = multi_hit
        self.priority = priority

class MoveInfo:
    def __init__(
        self,
        name: str,
        power: Optional[int],
        accuracy: Optional[int],
        pp: int,
        type: str,
        category: Literal['physical', 'special', 'status'],
        effect: Optional[MoveEffect] = None,
        target: str = 'single',
        contact: bool = False,
        sound: bool = False,
        punch: bool = False,
        bite: bool = False,
        bullet: bool = False,
        powder: bool = False,
        priority: int = 0
    ):
        self.name = name
        self.power = power
        self.accuracy = accuracy
        self.pp = pp
        self.type = type
        self.category = category
        self.effect = effect or MoveEffect()
        self.target = target
        self.contact = contact
        self.sound = sound
        self.punch = punch
        self.bite = bite
        self.bullet = bullet
        self.powder = powder
        self.priority = priority

    def get_power(self, team: List['BattlePokemon'], side: str, base_power: Optional[int] = None) -> int:
        if base_power is not None:
            return base_power
        return self.power

    def get_accuracy(self, env: Dict, side: str, base_accuracy: Optional[int] = None) -> int:
        if base_accuracy is not None:
            return base_accuracy
        return self.accuracy
    
    def copy(self) -> 'MoveInfo':
        return MoveInfo(
            name=self.name,
            power=self.power,
            accuracy=self.accuracy,
            pp=self.pp,
            type=self.type,
            category=self.category,
            effect=self.effect,
            target=self.target,
            contact=self.contact,
            sound=self.sound,
            punch=self.punch,
            bite=self.bite,
            bullet=self.bullet,
            powder=self.powder,
            priority=self.priority
        )