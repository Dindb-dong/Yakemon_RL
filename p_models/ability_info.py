from typing import List, Optional, Literal

AppearanceAbility = Literal[
    'rank_change', 'field_change', 'aura_change', 'weather_change',
    'heal', 'ability_change', 'disaster', 'form_change'
]

OffensiveBeforeAbility = Literal[
    'damage_buff', 'demerit', 'ability_nullification', 'type_nullification',
    'type_change', 'rank_buff', 'crack'
]

OffensiveAfterAbility = Literal[
    'status_change', 'rank_change', 'remove_demerit', 'item'
]

DefensiveBeforeAbility = Literal[
    'type_nullification', 'damage_nullification', 'damage_reduction', 'critical_nullification'
]

DefensiveAfterAbility = Literal[
    'status_change', 'damade_reflection', 'rank_change', 'ability_change',
    'heal', 'weather_change', 'field_change'
]

UtilAbility = Literal[
    'hp_low_trigger', 'change_trigger', 'rank_nullification', 'rank_buff', 'rank_change',
    'type_change', 'form_change', 'tickDamage_nullification', 'statusMove_nullification',
    'status_nullification', 'ability_nullification', 'weather_nullification',
    'intimidate_nullification', 'heal', 'damage', 'restrict_enemy',
    'certainly', 'demerit', 'etc'
]

class AbilityInfo:
    def __init__(
        self,
        id: int,
        name: str,
        appear: Optional[List[AppearanceAbility]] = None,
        offensive: Optional[List[OffensiveBeforeAbility | OffensiveAfterAbility]] = None,
        defensive: Optional[List[DefensiveBeforeAbility | DefensiveAfterAbility]] = None,
        util: Optional[List[UtilAbility]] = None,
        un_touchable: bool = False
    ):
        self.id = id
        self.name = name
        self.appear = appear
        self.offensive = offensive
        self.defensive = defensive
        self.util = util
        self.un_touchable = un_touchable