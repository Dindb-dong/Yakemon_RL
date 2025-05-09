from typing import List
from p_models.ability_info import AbilityInfo

def has_ability(ability: AbilityInfo, targets: List[str]) -> bool:
    return ability.name in targets