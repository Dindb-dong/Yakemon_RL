from typing import List
from p_data.ability_data import AbilityData

def has_ability(ability: AbilityData, targets: List[str]) -> bool:
    return ability.name in targets