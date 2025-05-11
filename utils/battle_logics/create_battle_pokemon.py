from typing import Dict, Callable

from p_models.pokemon_info import PokemonInfo
from p_models.battle_pokemon import BattlePokemon
from p_models.rank_state import RankState

# 기본 랭크 상태
default_rank: RankState = {
    "attack": 0,
    "sp_attack": 0,
    "defense": 0,
    "sp_defense": 0,
    "speed": 0,
    "accuracy": 0,
    "dodge": 0,
    "critical": 0,
}

# 도감번호 → formCondition 매핑
def is_small_form(self: BattlePokemon) -> bool:
    return self.current_hp / self.base.hp < 0.25  # 예시: 약어리 (체력 25% 미만)

form_condition_map: Dict[int, Callable[[BattlePokemon], bool]] = {
    746: is_small_form,
    # 필요 시 더 추가
}

def create_battle_pokemon(base: PokemonInfo, exchange: bool = False) -> BattlePokemon:
    if not base or not base.moves:
        raise ValueError(f"create_battle_pokemon: 유효하지 않은 포켓몬 데이터: {base}")

    pp: Dict[str, int] = {move.name: move.pp if move.pp is not None else 10 for move in base.moves}

    if exchange: # 상대 포켓몬 가져올 때 인데... 시뮬레이터에서는 이거 쓰지 않음
        if base.memorized_base:
            effective_base = base.memorized_base
            effective_base.ability = base.memorized_base.ability or base.ability
            effective_base.types = base.memorized_base.types or base.types
        else:
            effective_base = base
            effective_base.ability = base.original_ability or base.ability
            effective_base.types = base.original_types or base.types
        current_hp = effective_base.hp
    else: # 기본적으로 여기에 해당 
        effective_base = PokemonInfo(
            id=base.id,
            name=base.name,
            types=base.types,
            moves=base.moves,
            sex=base.sex,
            ability=base.ability,
            hp=base.hp + 75,
            attack=base.attack + 20,
            sp_attack=base.sp_attack + 20,
            defense=base.defense + 20,
            sp_defense=base.sp_defense + 20,
            speed=base.speed + 20,
            level=base.level,
            original_types=base.types,
            original_ability=base.ability,
            has_form_change=base.has_form_change,
            form_change=base.form_change,
            memorized_base=base.memorized_base
        )
        current_hp = effective_base.hp

    return BattlePokemon(
        base=effective_base,
        current_hp=current_hp,
        pp=pp,
        rank=default_rank.copy(),
        status=[],
        position=None,
        is_active=False,
        locked_move=None,
        locked_move_turn=None,
        is_protecting=False,
        used_move=None,
        had_missed=False,
        had_rank_up=False,
        is_charging=False,
        charging_move=None,
        received_damage=None,
        is_first_turn=False,
        cannot_move=False,
        form_num=0,
        form_condition=form_condition_map.get(base.id),
        un_usable_move=None,
        lost_type=False,
        temp_type=None,
        substitute=None
    )