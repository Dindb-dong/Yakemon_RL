# get_best_switch_index.py

from typing import List
from context.battle_store import battle_store_instance as store
from utils.type_relation import calculate_type_effectiveness


def get_max_effectiveness(attacker_types: List[str], defender_types: List[str]) -> float:
    return max(
        [calculate_type_effectiveness(atk_type, defender_types) for atk_type in attacker_types],
        default=1.0
    )


def get_best_switch_index(side: str) -> int:
    team = store.get_team(side)
    active_index = store.get_active_index(side)
    opponent = team[active_index]

    # 교체 가능한 포켓몬 필터링
    available_indexes = [
        (i, p) for i, p in enumerate(team)
        if i != active_index and p.current_hp > 0
    ]

    if len(available_indexes) == 0:
        return -1
    if len(available_indexes) == 1:
        return available_indexes[0][0]

    strong_counter = None
    neutral_option = None
    backup = None

    for index, pokemon in available_indexes:
        eff = get_max_effectiveness(pokemon.base.types, opponent.base.types)

        if eff > 1.5 and strong_counter is None:
            strong_counter = index
        elif eff <= 1.0 and neutral_option is None:
            neutral_option = index
        elif backup is None:
            backup = index

    return (
        strong_counter
        if strong_counter is not None else
        neutral_option
        if neutral_option is not None else
        backup
        if backup is not None else
        active_index
    )