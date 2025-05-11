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
    
    # 교체 가능한 포켓몬들의 점수 계산
    scores = []
    for i, pokemon in enumerate(my_team):
        if i == active_my or pokemon.current_hp <= 0:
            scores.append(float('-inf'))
            continue
        
        # HP 비율에 따른 점수
        hp_score = pokemon.current_hp / pokemon.base.hp
        
        # 타입 상성에 따른 점수
        type_score = 0
        for enemy_type in enemy_team[active_enemy].base.types:
            for my_type in pokemon.base.types:
                type_score += calculate_type_effectiveness(my_type, enemy_type)
        
        # 상태이상에 따른 점수
        status_score = -len(pokemon.status) * 0.2
        
        # 최종 점수 계산
        total_score = hp_score + type_score + status_score
        scores.append(total_score)
    
    # 가장 높은 점수를 가진 포켓몬의 인덱스 반환
    return scores.index(max(scores))