from typing import List, Optional
from p_models.move_info import MoveInfo
from p_models.ability_info import AbilityInfo

class PokemonInfo:
    def __init__(
        self,
        id: int,
        name: str,
        types: List[str],
        moves: List[MoveInfo],
        sex: Optional[str],
        ability: Optional[AbilityInfo],
        hp: int,
        attack: int,
        sp_attack: int,
        defense: int,
        sp_defense: int,
        speed: int,
        level: int,
        original_types: Optional[List[str]] = None,
        original_ability: Optional[AbilityInfo] = None,
        has_form_change: bool = False,
        form_change: Optional['PokemonInfo'] = None,
        memorized_base: Optional['PokemonInfo'] = None
    ):
        self.id = id
        self.name = name
        self.types = types
        self.original_types = original_types
        self.moves = moves
        self.sex = sex
        self.ability = ability
        self.original_ability = original_ability
        self.hp = hp
        self.attack = attack
        self.sp_attack = sp_attack
        self.defense = defense
        self.sp_defense = sp_defense
        self.speed = speed
        self.level = level
        self.has_form_change = has_form_change
        self.form_change = form_change
        self.memorized_base = memorized_base