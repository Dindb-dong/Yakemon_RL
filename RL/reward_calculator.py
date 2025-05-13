from utils.type_relation import calculate_type_effectiveness
from p_models.status import StatusManager
from p_models.battle_pokemon import BattlePokemon

def calculate_reward(
    my_team: list[BattlePokemon],
    enemy_team: list[BattlePokemon],
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
    battle_store=None,
    duration_store=None,
) -> float:
    """
    전략적 요소를 고려한 보상 계산
    Args:
        my_team: 내 팀 (BattlePokemon 리스트)
        enemy_team: 상대 팀 (BattlePokemon 리스트)
        active_my: 내 활성 포켓몬 인덱스
        active_enemy: 상대 활성 포켓몬 인덱스
        public_env: 공개 환경 정보
        my_env: 내 환경 정보
        enemy_env: 상대 환경 정보
        turn: 현재 턴
        my_effects: 내 효과 리스트
        enemy_effects: 상대 효과 리스트
        action: 수행한 행동 (int)
        done: 종료 여부
        battle_store: (옵션) 배틀 스토어
        duration_store: (옵션) 지속 효과 스토어
    Returns:
        float: 계산된 보상
    """
    reward = 0.0
    
    # 현재 활성화된 포켓몬
    current_pokemon = my_team[active_my]
    target_pokemon = enemy_team[active_enemy]
    
    # 1. HP 변화에 따른 보상
    current_hp = current_pokemon.current_hp / current_pokemon.base.hp
    next_hp = target_pokemon.current_hp / target_pokemon.base.hp
    hp_change = next_hp - current_hp
    reward += hp_change * 0.1  # HP 변화에 대한 보상
    
    # 2. 타입 상성에 따른 보상
    if action < 4:  # 기술 사용
        move = current_pokemon.base.moves[action]
        type_effectiveness = calculate_type_effectiveness(move.type, target_pokemon.base.types)
        reward += type_effectiveness * 0.2  # 타입 상성에 대한 보상
        
        # 기술의 위력과 카테고리 고려
        if move.category != '변화':
            reward += move.power * 0.001  # 기술 위력에 대한 보상
            
            # 효과가 없는 기술 사용에 대한 패널티
            if type_effectiveness == 0:
                reward -= 0.3  # 효과가 없는 기술 사용 패널티
                
            # 특성으로 인한 역효과에 대한 패널티
            if target_pokemon.base.ability:
                ability_name = target_pokemon.base.ability.name
                if (ability_name == "타오르는 불꽃" and move.type == "불꽃") or \
                   (ability_name == "저수" and move.type == "물"):
                    reward -= 0.5  # 특성으로 인한 역효과 패널티
    
    # 3. 상태 이상에 따른 보상
    current_status = current_pokemon.status
    next_status = target_pokemon.status
    if len(next_status) < len(current_status):
        reward += 0.3  # 상태 이상 해제에 대한 보상
    elif len(next_status) > len(current_status):
        reward -= 0.3  # 상태 이상 획득에 대한 패널티
    
    # 4. 교체 전략에 따른 보상
    if action >= 4:  # 교체
        switch_index = action - 4
        if 0 <= switch_index < len(my_team):
            next_pokemon = my_team[switch_index]
            if next_pokemon.current_hp > current_pokemon.current_hp:
                reward += 0.2  # 더 높은 HP를 가진 포켓몬으로 교체
            if any(t in next_pokemon.base.types for t in target_pokemon.base.types):
                reward += 0.3  # 유리한 타입으로 교체
    
    # # 5. 환경 효과에 따른 보상
    # if public_env['weather'] and public_env['weather'] in current_pokemon.weather_boost:
    #     reward += 0.2  # 날씨 효과 활용
    # if public_env['field'] and public_env['field'] in current_pokemon.field_boost:
    #     reward += 0.2  # 필드 효과 활용
    
    # 6. 승리/패배에 따른 보상
    if done:
        if next_hp > 0:
            reward += 1.0  # 승리 보상
        else:
            reward -= 1.0  # 패배 패널티
    
    return reward 