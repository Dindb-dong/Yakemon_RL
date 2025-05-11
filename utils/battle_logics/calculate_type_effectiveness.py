from typing import List, Dict
from p_models.pokemon_info import PokemonInfo
from p_models.move_info import MoveInfo
from .helpers import has_ability
from utils.type_relation import calculate_type_effectiveness as base_type_effect

# 타입 무효 특성을 무시하는 특성 목록
IGNORE_IMMUNITY_ABILITIES = ['배짱', '심안']

def is_type_immune(target_type: str, move_type: str) -> bool:
    immunity_map: Dict[str, List[str]] = {
        '노말': ['고스트'],
        '격투': ['고스트'],
        '독': ['강철'],
        '전기': ['땅'],
        '땅': ['비행'],
        '고스트': ['노말'],
        '드래곤': ['페어리'],
    }
    return target_type in immunity_map.get(move_type, [])

def calculate_type_effectiveness_with_ability(
    attacker: PokemonInfo,
    defender: PokemonInfo,
    move: MoveInfo
) -> float:
    move_type = move.type
    defender_types = defender.types[:]

    if attacker.ability and has_ability(attacker.ability, IGNORE_IMMUNITY_ABILITIES):
        defender_types = [t for t in defender_types if not is_type_immune(t, move_type)]

    return base_type_effect(move_type, defender_types)