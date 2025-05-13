from typing import List, Optional, Dict, Union, Literal
from p_models.move_info import MoveInfo
from p_models.ability_info import AbilityInfo

class PokemonInfo:
    def __init__(
        self,
        id: int,
        name: str,
        types: List[str],
        moves: List[MoveInfo],
        sex: Optional[Literal['male', 'female']] = None,
        ability: Optional[AbilityInfo] = None,
        hp: int = 0,
        attack: int = 0,
        sp_attack: int = 0,
        defense: int = 0,
        sp_defense: int = 0,
        speed: int = 0,
        level: int = 1,
        original_types: Optional[List[str]] = None,
        original_ability: Optional[AbilityInfo] = None,
        has_form_change: bool = False,
        form_change: Optional['PokemonInfo'] = None,
        memorized_base: Optional['PokemonInfo'] = None
    ):
        self.id = id
        self.name = name
        self.types = types
        self.moves = moves
        self.sex = sex
        self.ability = ability
        self.hp = hp
        self.attack = attack
        self.sp_attack = sp_attack
        self.defense = defense
        self.sp_defense = sp_defense
        self.speed = speed
        self.level = level
        self.original_types = original_types
        self.original_ability = original_ability
        self.has_form_change = has_form_change
        self.form_change = form_change
        self.memorized_base = memorized_base