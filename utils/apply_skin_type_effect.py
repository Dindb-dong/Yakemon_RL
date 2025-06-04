from typing import Dict, Literal
from p_models.move_info import MoveInfo


SkinType = Literal['프리즈스킨', '스카이스킨', '페어리스킨', '일렉트릭스킨', '노말스킨']

skin_type_map: Dict[SkinType, str] = {
    '프리즈스킨': '얼음',
    '스카이스킨': '비행',
    '페어리스킨': '페어리',
    '일렉트릭스킨': '전기',
    '노말스킨': '노말',
}

def apply_skin_type_effect(move: MoveInfo, ability_name: str | None) -> MoveInfo:
    skin_abilities: list[SkinType] = ['프리즈스킨', '스카이스킨', '페어리스킨', '일렉트릭스킨', '노말스킨']

    if ability_name not in skin_abilities:
        return move

    skin_type = skin_type_map[ability_name]

    new_move = move

    if ability_name == '노말스킨':
        new_move = new_move.copy(type='노말')
        new_move = new_move.copy(power=int(new_move.power * 1.2))
    elif move.type == '노말':
        new_move = new_move.copy(type=skin_type)
        new_move = new_move.copy(power=int(new_move.power * 1.2))

    return new_move