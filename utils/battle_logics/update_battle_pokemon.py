import numpy as np
from typing import Optional, List
from copy import deepcopy
from p_models.battle_pokemon import BattlePokemon
from p_models.ability_info import AbilityInfo
from p_models.move_info import MoveInfo
from p_models.rank_state import RankManager
from p_models.status import StatusManager, StatusState
from context.battle_store import store
from context.duration_store import duration_store
unmain_status_with_duration: list[str] = [
    "도발", "트집", "사슬묶기", "회복봉인", "앵콜",
    "소리기술사용불가", "하품", "혼란", "교체불가",
    "조이기", "멸망의노래", "풀죽음"
]

# 체력 변화
def change_hp(pokemon: BattlePokemon, amount: int) -> BattlePokemon:
    add_log = store.add_log
    if amount > 0 and pokemon.current_hp >= pokemon.base.hp:
        print(f"{pokemon.base.name}은(는) 이미 최대 체력이다!")
        return pokemon
        
    new_hp = max(0, round(pokemon.current_hp + amount))
    new_hp = min(pokemon.base.hp, new_hp)
    print(f"{pokemon.base.name}의 체력이 {pokemon.current_hp}에서 {new_hp}로 변경되었습니다.")
    pokemon.current_hp = new_hp
    if pokemon.current_hp <= 0:
        add_log(f"😭 {pokemon.base.name}은/는 쓰러졌다!")
    return pokemon


# 랭크 변경
def change_rank(pokemon: BattlePokemon, stat: str, amount: int) -> BattlePokemon:
    manager = RankManager(deepcopy(pokemon.rank))

    if pokemon.base.ability and pokemon.base.ability.name in ['하얀연기', '클리어바디', '메탈프로텍트']:
        return pokemon

    if pokemon.base.ability and pokemon.base.ability.name == '심술꾸러기':
        if amount > 0:
            manager.decrease_state(stat, amount)
        else:
            manager.increase_state(stat, abs(amount))
    elif pokemon.base.ability and pokemon.base.ability.name == '오기':
        if amount > 0:
            manager.increase_state(stat, amount)
        else:
            manager.increase_state('attack', 2)
            manager.decrease_state(stat, abs(amount))
    elif pokemon.base.ability and pokemon.base.ability.name == '승기':
        if amount > 0:
            manager.increase_state(stat, amount)
        else:
            manager.increase_state('sp_attack', 2)
            manager.decrease_state(stat, abs(amount))
    else:
        if amount > 0:
            manager.increase_state(stat, amount)
        else:
            manager.decrease_state(stat, abs(amount))

    pokemon.rank = manager.get_state()
    print(f"{pokemon.base.name}의 {stat}이(가) {pokemon.rank[stat]}랭크로 변경되었다!")
    return pokemon


# 랭크 초기화
def reset_rank(pokemon: BattlePokemon) -> BattlePokemon:
    manager = RankManager(deepcopy(pokemon.rank))
    manager.reset_state()
    pokemon.rank = manager.get_state()
    return pokemon


# 상태이상 추가
DURATION_MAP = {
    "도발": 3,
    "트집": 3,
    "풀죽음": 1,
    "사슬묶기": 4,
    "회복봉인": 5,
    "앵콜": 3,
    "소리기술사용불가": 2,
    "하품": 2,
    "혼란": int(np.floor(np.random.random() * 3) + 2), # 랜덤 2~4은 일단 기본 3으로 단순화
    "교체불가": 4,
    "조이기": 4,
    "멸망의노래": 3,
    "잠듦": 3,
}

def is_duration_status(status: StatusState) -> bool:
    return status in unmain_status_with_duration or status == "잠듦"


def add_status(pokemon: BattlePokemon, status: StatusState, side: str, nullification: bool = False) -> BattlePokemon:
    opponent_side = "enemy" if side == "my" else "my"
    team = store.get_team(side)
    opponent_team = store.get_team(opponent_side)
    active_index = store.get_active_index(side)
    opponent_active_index = store.get_active_index(opponent_side)
    active_pokemon = team[active_index]
    opponent_pokemon = opponent_team[opponent_active_index]
    add_effect = duration_store.add_effect
    add_log = store.add_log

    mental_statuses = ["도발", "트집", "사슬묶기", "회복봉인", "헤롱헤롱", "앵콜"]

    # 면역 체크
    if (status in ['독', '맹독']) and not nullification and (
        (pokemon.base.ability and pokemon.base.ability.name == '면역') or
        ('독' in pokemon.base.types) or
        ('강철' in pokemon.base.types)
    ):
        return pokemon

    if status == '교체불가' and '고스트' in pokemon.base.types:
        return pokemon
    if (status in ['도발', '헤롱헤롱']) and pokemon.base.ability and pokemon.base.ability.name == '둔감':
        return pokemon
    if status == '마비' and ((pokemon.base.ability and pokemon.base.ability.name == '유연') or ('전기' in pokemon.base.types)):
        return pokemon
    if status == '화상' and ((pokemon.base.ability and pokemon.base.ability.name in ['수의베일', '수포']) or ('불' in pokemon.base.types)):
        return pokemon
    if status == '잠듦' and (pokemon.base.ability and pokemon.base.ability.name in ['불면', '의기양양', '스위트베일']):
        return pokemon
    if status == '얼음' and (pokemon.base.ability and pokemon.base.ability.name == '마그마의무장') or ('얼음' in pokemon.base.types):
        return pokemon
    if status in mental_statuses and (pokemon.base.ability and pokemon.base.ability.name == '아로마베일'):
        return pokemon

    # duration 효과
    if is_duration_status(status):
        if status in pokemon.status:
            add_log("기술은 실패했다...")
            return pokemon

        add_effect(side, {
            "name": status,
            "remainingTurn": DURATION_MAP.get(status, 3),
            "ownerIndex": active_index,
        })

        if status == "사슬묶기" and active_pokemon.used_move:
            pokemon.un_usable_move = active_pokemon.used_move

    # 실제 부여
    manager = StatusManager(pokemon.status)
    manager.add_status(status)
    pokemon.status = manager.get_status()
    store.update_pokemon(side, active_index, lambda p: p)

    # 싱크로
    if pokemon.base.ability and pokemon.base.ability.name == '싱크로':
        if not (opponent_pokemon.base.ability and opponent_pokemon.base.ability.name == '싱크로'):
            add_status(opponent_pokemon, status, opponent_side)

    return pokemon


# 상태이상 제거
def remove_status(pokemon: BattlePokemon, status: StatusState) -> BattlePokemon:
    manager = StatusManager(pokemon.status)
    manager.remove_status(status)
    pokemon.status = manager.get_status()
    return pokemon


# 전체 상태이상 제거
def clear_all_status(pokemon: BattlePokemon) -> BattlePokemon:
    manager = StatusManager(pokemon.status)
    manager.clear_status()
    pokemon.status = manager.get_status()
    return pokemon


# 상태이상 보유 여부
def has_status(pokemon: BattlePokemon, status: StatusState) -> bool:
    manager = StatusManager(pokemon.status)
    return manager.has_status(status)


# PP 차감
def use_move_pp(pokemon: BattlePokemon, move_name: str, pressure: bool = False, is_multi_hit: bool = False) -> BattlePokemon:
    pp = deepcopy(pokemon.pp)
    if is_multi_hit: return pokemon
    if move_name in pp:
        pp[move_name] -= 2 if pressure else 1
        pp[move_name] = max(pp[move_name], 0)
    pokemon.pp = pp
    return pokemon


# 고정 기술 설정
def set_locked_move(pokemon: BattlePokemon, move: Optional[MoveInfo]) -> BattlePokemon:
    pokemon.locked_move = move
    return pokemon


# 위치 설정
def change_position(pokemon: BattlePokemon, position: Optional[str]) -> BattlePokemon:
    pokemon.position = position
    return pokemon


# 보호 상태 설정
def set_protecting(pokemon: BattlePokemon, is_protecting: bool) -> BattlePokemon:
    pokemon.is_protecting = is_protecting
    return pokemon


# 마지막 사용 기술
def set_used_move(pokemon: BattlePokemon, move: Optional[MoveInfo]) -> BattlePokemon:
    pokemon.used_move = move
    return pokemon


# 빗나감 여부
def set_had_missed(pokemon: BattlePokemon, had_missed: bool) -> BattlePokemon:
    pokemon.had_missed = had_missed
    return pokemon


# 랭크업 여부
def set_had_rank_up(pokemon: BattlePokemon, had_rank_up: bool) -> BattlePokemon:
    pokemon.had_rank_up = had_rank_up
    return pokemon


# 차징 상태
def set_charging(pokemon: BattlePokemon, is_charging: bool, move: Optional[MoveInfo] = None) -> BattlePokemon:
    pokemon.is_charging = is_charging
    pokemon.charging_move = move if is_charging else None
    return pokemon


# 받은 데미지 기록
def set_received_damage(pokemon: BattlePokemon, damage: int) -> BattlePokemon:
    pokemon.received_damage = damage
    return pokemon

# 준 데미지 기록
def set_dealt_damage(pokemon: BattlePokemon, dealt_damage: int) -> BattlePokemon:
    pokemon.dealt_damage = dealt_damage
    return pokemon

# 행동 불가
def set_cannot_move(pokemon: BattlePokemon, cannot_move: bool) -> BattlePokemon:
    pokemon.cannot_move = cannot_move
    return pokemon

# 전투 출전 여부
def set_active(pokemon: BattlePokemon, is_active: bool) -> BattlePokemon:
    pokemon.is_active = is_active
    return pokemon


# 특성 강제 설정
def set_ability(pokemon: BattlePokemon, ability: Optional[AbilityInfo]) -> BattlePokemon:
    pokemon.base.ability = ability
    return pokemon


# 타입 강제 변경
def set_types(pokemon: BattlePokemon, types: List[str]) -> BattlePokemon:
    pokemon.temp_type = pokemon.base.types
    pokemon.base.types = types
    return pokemon


# 타입 제거
def remove_types(pokemon: BattlePokemon, type_: str, is_normal: bool = False) -> BattlePokemon:
    if is_normal:
        pokemon.base.types = ['노말'] + [t for t in pokemon.base.types if t != type_]
    else:
        pokemon.base.types = [t for t in pokemon.base.types if t != type_]
    return pokemon


# 상태 초기화 (교체 시)
def reset_state(pokemon: BattlePokemon, is_switch: bool = False) -> BattlePokemon:
    pokemon.is_protecting = False
    pokemon.had_rank_up = False
    pokemon.is_first_turn = False

    if is_switch:
        pokemon.received_damage = 0
        pokemon.dealt_damage = 0
        pokemon.base.types = pokemon.temp_type if pokemon.temp_type else pokemon.base.types
        pokemon.used_move = None
        pokemon.un_usable_move = None
        pokemon.is_charging = False
        pokemon.charging_move = None
        pokemon.locked_move = None
        pokemon.had_missed = False
        pokemon.locked_move_turn = 0
        pokemon.temp_type = []

    return pokemon