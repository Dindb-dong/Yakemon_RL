"""데미지 계산 관련 함수들을 정의하는 모듈"""

import random
from ..p_models.types import TYPE_EFFECTIVENESS, get_type_name, Terrain

def get_critical_chance(stage):
    """치명타 단계에 따른 확률 계산"""
    if stage <= 0:
        return 1/24  # 약 4.17%
    elif stage == 1:
        return 1/8   # 12.5%
    elif stage == 2:
        return 1/2   # 50%
    else:
        return 1     # 100%

def calculate_damage(move, attacker, defender, battle=None):
    """Damage calculation function"""
    # No damage for status moves
    if move.category == 'Status':
        return 0

    # Check accuracy
    if random.randint(1, 100) > move.accuracy:
        return 0  # Missed

    # Type effectiveness
    type_effectiveness = 1.0
    for def_type in defender.types:
        type_effectiveness *= TYPE_EFFECTIVENESS[move.type][def_type]

    # Same-Type Attack Bonus (STAB)
    stab = 1.5 if move.type in attacker.types else 1.0

    # Random factor (0.85-1.0)
    random_factor = random.uniform(0.85, 1.0)

    # 치명타 계산 (향상된 시스템)
    critical_stages = 0

    # 포켓몬의 치명타 단계
    critical_stages += attacker.critical_hit_stage

    # 기술의 치명타 속성
    if move.effects and 'critical_rate' in move.effects:
        critical_stages += move.effects['critical_rate']

    # 치명타 확률 계산
    critical_chance = get_critical_chance(critical_stages)

    # 치명타 여부
    is_critical = random.random() < critical_chance
    critical = 1.5 if is_critical else 1.0  # 치명타 데미지 수정자

    # 치명타 발생 시 battle_effects에 기록
    if is_critical:
        if not hasattr(move, 'battle_effects'):
            move.battle_effects = {}
        move.battle_effects['critical_hit'] = True

    # Determine attack/defense stats
    if move.category == 'Physical':
        attack_stat = attacker.calculate_stat('atk')
        defense_stat = defender.calculate_stat('def')
    else:  # Special
        attack_stat = attacker.calculate_stat('spa')
        defense_stat = defender.calculate_stat('spd')

    # Damage calculation formula
    damage = ((2 * attacker.level / 5 + 2) * move.power * attack_stat / defense_stat / 50 + 2)
    damage *= stab * type_effectiveness * critical * random_factor

    # 지형 효과 적용
    if battle and battle.terrain:
        terrain_type = battle.terrain['name']
        move_type_name = get_type_name(move.type)

        if terrain_type == Terrain.GRASSY and move_type_name == "풀":
            # 풀지형에서 풀타입 기술 위력 1.3배
            damage = int(damage * 1.3)
        elif terrain_type == Terrain.ELECTRIC and move_type_name == "전기":
            # 전기지형에서 전기타입 기술 위력 1.3배
            damage = int(damage * 1.3)
        elif terrain_type == Terrain.PSYCHIC and move_type_name == "에스퍼":
            # 에스퍼지형에서 에스퍼타입 기술 위력 1.3배
            damage = int(damage * 1.3)
        elif terrain_type == Terrain.MISTY and move_type_name == "드래곤":
            # 페어리지형에서 드래곤타입 기술 위력 0.5배
            damage = int(damage * 0.5)

    return max(1, int(damage))  # Minimum 1 damage 