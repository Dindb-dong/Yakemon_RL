from typing import List, Dict, Optional, Literal, Union
from p_models.battle_pokemon import BattlePokemon
from p_models.types import FieldType, WeatherType
from p_models.status import StatusState
from p_models.rank_state import RankStat

# 타입 정의
ScreenType = Optional[Literal['빛의장막', '리플렉터', '오로라베일']]

class StatChange:
    def __init__(self, target: Literal['opponent', 'self'], stat: RankStat, change: int):
        self.target = target
        self.stat = stat
        self.change = change  # -6 ~ +6  # -6 ~ +6 범위

class MoveEffect:
    def __init__(
        self,
        id: int,
        chance: float,
        status: Optional[StatusState] = None,
        recoil: Optional[float] = None,
        fail: Optional[float] = None,
        lost_type: Optional[str] = None,
        heal: Optional[float] = None,
        stat_change: Optional[List[StatChange]] = None,
        multi_hit: bool = False,
        double_hit: bool = False,
        triple_hit: bool = False,
        break_screen: bool = False,
        rank_nullification: bool = False,
        type_change: Optional[str] = None
    ):
        self.id = id
        self.chance = chance
        self.status = status
        self.recoil = recoil
        self.fail = fail
        self.lost_type = lost_type
        self.heal = heal
        self.stat_change = stat_change or []
        self.multi_hit = multi_hit
        self.double_hit = double_hit
        self.triple_hit = triple_hit
        self.break_screen = break_screen
        self.rank_nullification = rank_nullification
        self.type_change = type_change

class MoveInfo:
    def __init__(
        self,
        id: int,
        name: str,
        type: str,
        category: Literal['물리', '특수', '변화'],
        power: int,
        pp: int,
        is_touch: bool,
        affiliation: Optional[Literal['펀치', '폭탄', '바람', '가루', '소리', '파동', '물기', '베기']] = None,
        accuracy: int = 100,
        critical_rate: int = 0,
        demerit_effects: Optional[List[MoveEffect]] = None,
        effects: Optional[List[MoveEffect]] = None,
        priority: Optional[int] = 0,
        trap: Optional[str] = None,
        field: Optional[FieldType] = None,
        room: Optional[str] = None,
        weather: Optional[WeatherType] = None,
        u_turn: bool = False,
        exile: bool = False,
        protect: bool = False,
        counter: bool = False,
        revenge: bool = False,
        boost_on_missed_prev: bool = False,
        charge_turn: bool = False,
        position: Optional[Literal['땅', '하늘', '바다', '공허']] = None,
        one_hit_ko: bool = False,
        first_turn_only: bool = False,
        self_kill: bool = False,
        screen: ScreenType = None,
        pass_substitute: bool = False,
        cannot_move: bool = False,
        locked_move: bool = False,
        target: Literal['self', 'opponent', 'none'] = 'opponent',
    ):
        self.id = id
        self.name = name
        self.type = type
        self.category = category
        self.power = power
        self.pp = pp
        self.is_touch = is_touch
        self.affiliation = affiliation
        self.accuracy = accuracy
        self.critical_rate = critical_rate
        self.demerit_effects = demerit_effects or []
        self.effects = effects or []
        self.priority = priority
        self.trap = trap
        self.field = field
        self.room = room
        self.weather = weather
        self.u_turn = u_turn
        self.exile = exile
        self.protect = protect
        self.counter = counter
        self.revenge = revenge
        self.boost_on_missed_prev = boost_on_missed_prev
        self.charge_turn = charge_turn
        self.position = position
        self.one_hit_ko = one_hit_ko
        self.first_turn_only = first_turn_only
        self.self_kill = self_kill
        self.screen = screen
        self.pass_substitute = pass_substitute
        self.cannot_move = cannot_move
        self.locked_move = locked_move
        self.target = target
        
    def get_power(self, team: List[BattlePokemon], side: str, base_power: Optional[int] = None) -> int:
        if base_power is not None:
            return base_power
        return self.power

    def get_accuracy(self, env: Dict, side: str, base_accuracy: Optional[int] = None) -> int:
        if base_accuracy is not None:
            return base_accuracy
        return self.accuracy
    
    def copy(self) -> 'MoveInfo':
        return MoveInfo(
            id=self.id,
            name=self.name,
            type=self.type,
            category=self.category,
            power=self.power,
            pp=self.pp,
            is_touch=self.is_touch,
            affiliation=self.affiliation,
            accuracy=self.accuracy,
            critical_rate=self.critical_rate,
            demerit_effects=self.demerit_effects,
            effects=self.effects,
            priority=self.priority,
            trap=self.trap,
            field=self.field,
            room=self.room,
            weather=self.weather,
            u_turn=self.u_turn,
            exile=self.exile,
            protect=self.protect,
            counter=self.counter,
            revenge=self.revenge,
            boost_on_missed_prev=self.boost_on_missed_prev,
            charge_turn=self.charge_turn,
            position=self.position,
            one_hit_ko=self.one_hit_ko,
            first_turn_only=self.first_turn_only,
            self_kill=self.self_kill,
            screen=self.screen,
            pass_substitute=self.pass_substitute,
            cannot_move=self.cannot_move,
            locked_move=self.locked_move,
            target=self.target
        )