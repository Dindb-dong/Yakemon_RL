from utils.type_relation import calculate_type_effectiveness
from p_models.status import StatusManager

def calculate_reward(
    my_team: list,
    enemy_team: list,
    active_my: int,
    active_enemy: int,
    public_env: dict,
    my_env: dict,
    enemy_env: dict,
    turn: int,
    my_effects: list,
    enemy_effects: list,
    action: int,
    done: bool,
    battle_store: 'BattleStore',
    duration_store: 'DurationStore'
) -> float:
    """
    전략적 요소를 고려한 보상 계산
    """
    reward = 0.0
    
    # 현재 활성화된 포켓몬
    current_pokemon = my_team[active_my]
    target_pokemon = enemy_team[active_enemy]
    
    # 1. HP 변화에 따른 보상
    current_hp = current_pokemon['currentHp'] / current_pokemon['base']['hp']
    next_hp = target_pokemon['currentHp'] / target_pokemon['base']['hp']
    hp_change = next_hp - current_hp
    reward += hp_change * 0.1  # HP 변화에 대한 보상
    
    # 2. 타입 상성에 따른 보상
    if action < 4:  # 기술 사용
        move = current_pokemon['base']['moves'][action]
        type_effectiveness = calculate_type_effectiveness(move.type, target_pokemon['base']['types'])
        reward += type_effectiveness * 0.2  # 타입 상성에 대한 보상
        
        # 기술의 위력과 카테고리 고려
        if move.category != '변화':
            reward += move.power * 0.001  # 기술 위력에 대한 보상
    
    # 3. 상태 이상에 따른 보상
    current_status = current_pokemon['status']
    next_status = target_pokemon['status']
    if len(next_status) < len(current_status):
        reward += 0.3  # 상태 이상 해제에 대한 보상
    elif len(next_status) > len(current_status):
        reward -= 0.3  # 상태 이상 획득에 대한 패널티
    
    # 4. 교체 전략에 따른 보상
    if action >= 4:  # 교체
        next_pokemon = my_team[action - 4]
        if next_pokemon['currentHp'] > current_pokemon['currentHp']:
            reward += 0.2  # 더 높은 HP를 가진 포켓몬으로 교체
        if any(t in next_pokemon['base']['types'] for t in target_pokemon['base']['types']):
            reward += 0.3  # 유리한 타입으로 교체
    
    # 5. 환경 효과에 따른 보상
    if public_env['weather'] and public_env['weather'] in current_pokemon.get('weather_boost', []):
        reward += 0.2  # 날씨 효과 활용
    if public_env['field'] and public_env['field'] in current_pokemon.get('field_boost', []):
        reward += 0.2  # 필드 효과 활용
    
    # 6. 승리/패배에 따른 보상
    if done:
        if next_hp > 0:
            reward += 1.0  # 승리 보상
        else:
            reward -= 1.0  # 패배 패널티
    
    return reward 