from typing import Optional, List, Dict, Callable
from move_info import MoveInfo
from pokemon_info import PokemonInfo

class BattlePokemon:
    def __init__(
        self,
        base: PokemonInfo,  # 기본 정보 (나중에 PokemonInfo 클래스 따로 정의해야 함)
        current_hp: int,
        pp: Dict[str, int],
        rank: Dict[str, int],
        status: List[str],
        position: Optional[str] = None,  # '땅', '하늘', '바다', '공허' 중 하나
        is_active: bool = False,
        locked_move: Optional[MoveInfo] = None,
        locked_move_turn: Optional[int] = None,
        is_protecting: bool = False,
        used_move: Optional[MoveInfo] = None,
        had_missed: bool = False,
        had_rank_up: bool = False,
        is_charging: bool = False,
        charging_move: Optional[MoveInfo] = None,
        received_damage: Optional[int] = None,
        is_first_turn: bool = False,
        cannot_move: bool = False,
        form_num: Optional[int] = None,
        form_condition: Optional[Callable[['BattlePokemon'], bool]] = None,
        un_usable_move: Optional[MoveInfo] = None,
        lost_type: bool = False,
        temp_type: Optional[List[str]] = None,
        substitute: Optional['BattlePokemon'] = None,
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
        self.is_first_turn = is_first_turn
        self.cannot_move = cannot_move
        self.form_num = form_num
        self.form_condition = form_condition
        self.un_usable_move = un_usable_move
        self.lost_type = lost_type
        self.temp_type = temp_type
        self.substitute = substitute