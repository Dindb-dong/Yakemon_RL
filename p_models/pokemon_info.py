from typing import List, Optional, Dict
from p_models.move_info import MoveInfo
from p_models.ability_info import AbilityInfo

class PokemonInfo:
    def __init__(
        self,
        name: str,
        types: List[str],
        base_stats: Dict[str, int],
        abilities: List[str],
        moves: Optional[List[MoveInfo]] = None,
        height: float = 0.0,
        weight: float = 0.0,
        catch_rate: int = 0,
        base_exp: int = 0,
        growth_rate: str = 'medium',
        egg_groups: List[str] = None,
        gender_ratio: float = 0.5,
        hatch_steps: int = 0,
        color: str = 'unknown',
        shape: str = 'unknown',
        habitat: str = 'unknown',
        generation: int = 1
    ):
        self.name = name
        self.types = types
        self.base_stats = base_stats
        self.abilities = abilities
        self.moves = moves or []
        self.height = height
        self.weight = weight
        self.catch_rate = catch_rate
        self.base_exp = base_exp
        self.growth_rate = growth_rate
        self.egg_groups = egg_groups or []
        self.gender_ratio = gender_ratio
        self.hatch_steps = hatch_steps
        self.color = color
        self.shape = shape
        self.habitat = habitat
        self.generation = generation