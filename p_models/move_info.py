from typing import List, Dict, Optional, Literal, Union, TYPE_CHECKING
from p_models.status import StatusState


if TYPE_CHECKING:
    from p_models.battle_pokemon import BattlePokemon

# 타입 정의
ScreenType = Optional[Literal['빛의장막', '리플렉터', '오로라베일']]
AffiliationType = Optional[Literal['소리', '펀치', '물기', '폭탄', '가루']]
TrapType = Optional[Literal['독압정', '스텔스록', '압정뿌리기', '압정뿌리기2', '압정뿌리기3', '끈적끈적네트']]
PositionType = Optional[Literal['땅', '하늘', '바다', '공허']]

class StatChange:
    def __init__(self, target: str, stat: str, change: int):
        self.target = target
        self.stat = stat
        self.change = change

class MoveEffect:
    def __init__(
        self,
        id: Optional[int] = None,
        chance: Optional[float] = None,
        stat_change: Optional[List[StatChange]] = None,
        status: Optional[StatusState] = None,
        recoil: Optional[float] = None,
        multi_hit: Optional[tuple] = None,
        heal: Optional[float] = None,
        rank_nullification: Optional[bool] = None,
        triple_hit: Optional[bool] = None,
        double_hit: Optional[bool] = None,
        break_screen: Optional[bool] = None,
        type_change: Optional[str] = None,
        lost_type: Optional[str] = None,
        fail: Optional[float] = None
    ):
        self.id = id
        self.chance = chance
        self.stat_change = stat_change or []
        self.status = status
        self.recoil = recoil
        self.multi_hit = multi_hit
        self.heal = heal
        self.rank_nullification = rank_nullification
        self.triple_hit = triple_hit
        self.double_hit = double_hit
        self.break_screen = break_screen
        self.type_change = type_change
        self.lost_type = lost_type
        self.fail = fail

class MoveInfo:
    def __init__(
        self,
        id: int,
        name: str,
        power: Optional[int],
        accuracy: Optional[int],
        pp: int,
        type: str,
        category: Literal['물리', '특수', '변화'],
        target: Literal['self', 'opponent', 'none'],
        effects: Optional[List[MoveEffect]] = None,
        demerit_effects: Optional[List[MoveEffect]] = None,
        is_touch: bool = False,
        affiliation: AffiliationType = None,
        priority: int = 0,
        critical_rate: int = 0,
        trap: TrapType = None,
        field: Optional[str] = None,
        room: Optional[str] = None,
        weather: Optional[str] = None,
        u_turn: bool = False,
        exile: bool = False,
        protect: bool = False,
        counter: bool = False,
        revenge: bool = False,
        boost_on_missed_prev: bool = False,
        charge_turn: bool = False,
        position: PositionType = None,
        one_hit_ko: bool = False,
        first_turn_only: bool = False,
        self_kill: bool = False,
        screen: ScreenType = None,
        pass_substitute: bool = False,
        cannot_move: bool = False,
        locked_move: bool = False,
        pp_max: Optional[int] = None,
    ):
        self.id = id
        self.name = name
        self.power = power
        self.accuracy = accuracy
        self.pp = pp
        self.pp_max = pp_max if pp_max is not None else pp
        self.type = type
        self.category = category
        self.target = target
        self.effects = effects or [MoveEffect()]
        self.demerit_effects = demerit_effects or []
        self.is_touch = is_touch
        self.affiliation = affiliation
        self.priority = priority
        self.critical_rate = critical_rate
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

    def get_power(self, team: List['BattlePokemon'], side: Literal['my', 'enemy'], base_power: Optional[int] = None) -> int:
        if base_power is not None:
            return base_power
        return self.power

    def get_accuracy(self, env: Dict, side: Literal['my', 'enemy'], base_accuracy: Optional[int] = None) -> int:
        if base_accuracy is not None:
            return base_accuracy
        return self.accuracy
    
    def copy(self, **overrides) -> 'MoveInfo':
        return MoveInfo(
            id=overrides.get('id', self.id),
            name=overrides.get('name', self.name),
            power=overrides.get('power', self.power),
            accuracy=overrides.get('accuracy', self.accuracy),
            pp=overrides.get('pp', self.pp),
            type=overrides.get('type', self.type),
            category=overrides.get('category', self.category),
            target=overrides.get('target', self.target),
            effects=overrides.get('effects', self.effects),
            demerit_effects=overrides.get('demerit_effects', self.demerit_effects),
            is_touch=overrides.get('is_touch', self.is_touch),
            affiliation=overrides.get('affiliation', self.affiliation),
            priority=overrides.get('priority', self.priority),
            critical_rate=overrides.get('critical_rate', self.critical_rate),
            trap=overrides.get('trap', self.trap),
            field=overrides.get('field', self.field),
            room=overrides.get('room', self.room),
            weather=overrides.get('weather', self.weather),
            u_turn=overrides.get('u_turn', self.u_turn),
            exile=overrides.get('exile', self.exile),
            protect=overrides.get('protect', self.protect),
            counter=overrides.get('counter', self.counter),
            revenge=overrides.get('revenge', self.revenge),
            boost_on_missed_prev=overrides.get('boost_on_missed_prev', self.boost_on_missed_prev),
            charge_turn=overrides.get('charge_turn', self.charge_turn),
            position=overrides.get('position', self.position),
            one_hit_ko=overrides.get('one_hit_ko', self.one_hit_ko),
            first_turn_only=overrides.get('first_turn_only', self.first_turn_only),
            self_kill=overrides.get('self_kill', self.self_kill),
            screen=overrides.get('screen', self.screen),
            pass_substitute=overrides.get('pass_substitute', self.pass_substitute),
            cannot_move=overrides.get('cannot_move', self.cannot_move),
            locked_move=overrides.get('locked_move', self.locked_move),
            pp_max=self.pp_max
        )