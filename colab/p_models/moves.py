"""포켓몬 기술 관련 클래스를 정의하는 모듈"""

class Move:
    """Pokémon move class"""
    def __init__(self, name, type_id, category, power, accuracy, pp, effects=None):
        self.name = name
        self.type = type_id
        self.category = category  # 'Physical', 'Special', or 'Status'
        self.power = power
        self.accuracy = accuracy
        self.pp = pp
        self.max_pp = pp
        self.effects = effects if effects else {}
        self.battle_effects = {}  # 배틀 중 발생하는 효과 (치명타 등)

def get_move_priority(move):
    """기술의 우선 순위 값 반환"""
    if not hasattr(move, 'effects') or not move.effects:
        return 0
    return move.effects.get('priority', 0) 