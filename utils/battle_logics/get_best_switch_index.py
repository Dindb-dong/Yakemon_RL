# get_best_switch_index.py

from typing import List
from context.battle_store import BattleStoreState, store
from utils.type_relation import calculate_type_effectiveness


def get_max_effectiveness(attacker_types: List[str], defender_types: List[str]) -> float:
    return max(
        [calculate_type_effectiveness(atk_type, defender_types) for atk_type in attacker_types],
        default=1.0
    )


def get_best_switch_index(side: str) -> int:
    """가장 좋은 교체 포켓몬의 인덱스를 반환"""
    state: BattleStoreState = store.get_state()
    my_team = state["my_team"] if side == "my" else state["enemy_team"]
    enemy_team = state["enemy_team"] if side == "my" else state["my_team"]
    active_my = state["active_my"] if side == "my" else state["active_enemy"]
    active_enemy = state["active_enemy"] if side == "my" else state["active_my"]
    
    # 교체 가능한 포켓몬만 필터링
    available_pokemon = [
        (i, pokemon) for i, pokemon in enumerate(my_team)
        if i != active_my and pokemon.current_hp > 0
    ]
    
    # 교체 가능한 포켓몬이 없는 경우
    if not available_pokemon:
        return -1
    
    # 각 포켓몬의 점수 계산
    scores = []
    for i, pokemon in available_pokemon:
        # HP 비율 (0.0 ~ 1.0)
        hp_score = pokemon.current_hp / pokemon.base.hp
        
        # 타입 상성 점수 (0.0 ~ 4.0)
        type_score = sum(
            calculate_type_effectiveness(my_type, enemy_type)
            for my_type in pokemon.base.types
            for enemy_type in enemy_team[active_enemy].base.types
        )
        
        # 상태이상 점수 (0.0 ~ -1.0)
        status_score = -len(pokemon.status) * 0.2
        
        # 최종 점수 계산 (HP 40%, 타입 상성 50%, 상태이상 10%)
        total_score = (hp_score * 0.4) + (type_score * 0.5) + (status_score * 0.1)
        scores.append((i, total_score))
    
    # 가장 높은 점수를 가진 포켓몬의 인덱스 반환
    return max(scores, key=lambda x: x[1])[0]