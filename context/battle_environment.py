from typing import List, Optional, Literal
from p_models.move_info import ScreenType
from p_models.types import FieldType, WeatherType


class PublicBattleEnvironment:
    def __init__(
        self,
        weather: WeatherType = None,
        field: FieldType = None,
        aura: Optional[List[str]] = None,
        disaster: Optional[List[str]] = None,
        room: Optional[str] = None,
    ):
        self.weather = weather
        self.field = field
        self.aura = aura if aura is not None else []
        self.disaster = disaster
        self.room = room

class IndividualBattleEnvironment:
    def __init__(
        self,
        trap: Optional[List[str]] = None,
        screen: ScreenType = None,
        substitute: bool = False,
        disguise: bool = False,
    ):
        self.trap = trap if trap is not None else []
        self.screen = screen
        self.substitute = substitute
        self.disguise = disguise