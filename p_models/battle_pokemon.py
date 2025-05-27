from typing import Optional, List, Dict, Callable, TYPE_CHECKING
from p_models.pokemon_info import PokemonInfo
from p_models.rank_state import RankState
if TYPE_CHECKING:
    from p_models.move_info import MoveInfo

class BattlePokemon:
    def __init__(
        self,
        base: PokemonInfo,  
        current_hp: int,
        pp: Dict[str, int],
        rank: RankState,
        status: List[str],
        position: Optional[str] = None,  # '땅', '하늘', '바다', '공허' 중 하나
        is_active: bool = False,
        locked_move: Optional['MoveInfo'] = None, # vector로 표현할 때에는, moves.id 로 표현
        locked_move_turn: Optional[int] = None,
        is_protecting: bool = False,
        used_move: Optional['MoveInfo'] = None, # vector로 표현할 때에는, moves.id 로 표현
        had_missed: bool = False,
        had_rank_up: bool = False,
        is_charging: bool = False,
        charging_move: Optional['MoveInfo'] = None, # vector로 표현할 때에는, moves.id 로 표현
        received_damage: Optional[int] = None,
        dealt_damage: Optional[int] = None,
        is_first_turn: bool = False,
        cannot_move: bool = False,
        form_num: Optional[int] = None, # 이거는 생략
        form_condition: Optional[Callable[['BattlePokemon'], bool]] = None, # 이거는 생략
        un_usable_move: Optional['MoveInfo'] = None, # vector로 표현할 때에는, moves.id 로 표현
        lost_type: bool = False, # 이거는 생략
        temp_type: Optional[List[str]] = None, # vector로 표현할 때에는, 타입 정규화한 방식처럼 표현.
        substitute: Optional['BattlePokemon'] = None, # 이거는 vector로 표현할 때 생략.
    ):
        self.base = base
        self.current_hp = current_hp
        self.pp = pp
        self.rank = rank
        self.status = status
        self.position = position
        self.is_active = is_active
        self.locked_move = locked_move
        self.locked_move_turn = locked_move_turn
        self.is_protecting = is_protecting
        self.used_move = used_move
        self.had_missed = had_missed
        self.had_rank_up = had_rank_up
        self.is_charging = is_charging
        self.charging_move = charging_move
        self.received_damage = received_damage
        self.dealt_damage = dealt_damage
        self.is_first_turn = is_first_turn
        self.cannot_move = cannot_move
        self.form_num = form_num
        self.form_condition = form_condition
        self.un_usable_move = un_usable_move
        self.lost_type = lost_type
        self.temp_type = temp_type
        self.substitute = substitute
        
    def copy_with(self, **overrides) -> 'BattlePokemon':
        return BattlePokemon(
            base=overrides.get("base", self.base),
            current_hp=overrides.get("current_hp", self.current_hp),
            pp=overrides.get("pp", self.pp.copy()),
            rank=overrides.get("rank", self.rank.copy()),
            status=overrides.get("status", self.status.copy()),
            position=overrides.get("position", self.position),
            is_active=overrides.get("is_active", self.is_active),
            locked_move=overrides.get("locked_move", self.locked_move),
            locked_move_turn=overrides.get("locked_move_turn", self.locked_move_turn),
            is_protecting=overrides.get("is_protecting", self.is_protecting),
            used_move=overrides.get("used_move", self.used_move),
            had_missed=overrides.get("had_missed", self.had_missed),
            had_rank_up=overrides.get("had_rank_up", self.had_rank_up),
            is_charging=overrides.get("is_charging", self.is_charging),
            charging_move=overrides.get("charging_move", self.charging_move),
            received_damage=overrides.get("received_damage", self.received_damage),
            dealt_damage=overrides.get("dealt_damage", self.dealt_damage),
            is_first_turn=overrides.get("is_first_turn", self.is_first_turn),
            cannot_move=overrides.get("cannot_move", self.cannot_move),
            form_num=overrides.get("form_num", self.form_num),
            form_condition=overrides.get("form_condition", self.form_condition),
            un_usable_move=overrides.get("un_usable_move", self.un_usable_move),
            lost_type=overrides.get("lost_type", self.lost_type),
            temp_type=overrides.get("temp_type", self.temp_type.copy() if self.temp_type else None),
            substitute=overrides.get("substitute", self.substitute),
        )