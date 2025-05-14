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
                reward -= 3  # 효과가 없는 기술 사용 패널티
                
            # 특성으로 인한 역효과에 대한 패널티
            if target_pokemon.base.ability:
                ability_name = target_pokemon.base.ability.name
                # 물 타입 무효화 특성
                if ability_name in ["저수", "마중물", "건조피부", "증기기관"] and move.type == "물":
                    reward -= 0.5  # 특성으로 인한 역효과 패널티
                # 불 타입 무효화 특성
                elif ability_name in ["타오르는불꽃", "증기기관"] and move.type == "불":
                    reward -= 0.5  # 특성으로 인한 역효과 패널티
                # 땅 타입 무효화 특성
                elif ability_name in ["흙먹기", "부유"] and move.type == "땅":
                    reward -= 0.5  # 특성으로 인한 역효과 패널티
                # 풀 타입 무효화 특성
                elif ability_name == "초식" and move.type == "풀":
                    reward -= 0.5  # 특성으로 인한 역효과 패널티
                # 전기 타입 무효화 특성
                elif ability_name in ["피뢰침", "전기엔진"] and move.type == "전기":
                    reward -= 0.5  # 특성으로 인한 역효과 패널티
                # 특정 계열 기술 무효화 특성
                elif (ability_name == "방진" and move.affiliation == "가루") or \
                     (ability_name == "방탄" and move.affiliation == "폭탄") or \
                     (ability_name == "여왕의위엄" and move.priority > 0) or \
                     (ability_name == "방음" and move.affiliation == "소리"):
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
                reward += 0.1  # 더 높은 HP를 가진 포켓몬으로 교체
            if any(t in next_pokemon.base.types for t in target_pokemon.base.types):
                reward += 0.3  # 유리한 타입으로 교체
    
    # 5. 랭크업/다운에 따른 보상
    if action < 4:  # 기술 사용
        move = current_pokemon.base.moves[action]
        
        # 스피드 비교
        my_speed = current_pokemon.base.speed
        enemy_speed = target_pokemon.base.speed
        
        # 모든 효과에 대해 랭크업/다운 확인
        for effect in move.effects:
            if effect.stat_change and effect.chance >= 0.5:
                for stat_change in effect.stat_change:
                    # 자신의 스탯 변화
                    if stat_change.target == 'self':
                        # 랭크업
                        if stat_change.change > 0:
                            # 스피드 랭크업
                            if stat_change.stat == 'speed':
                                if my_speed < enemy_speed:
                                    reward += 0.5  # 상대보다 느린 상태에서 스피드 랭크업
                                else:
                                    reward += 0.2  # 일반적인 스피드 랭크업
                            
                            # 공격/특수공격 랭크업
                            elif stat_change.stat in ['attack', 'sp_attack']:
                                if my_speed > enemy_speed:
                                    reward += 0.4  # 상대보다 빠른 상태에서 공격력 랭크업
                                else:
                                    reward += 0.2  # 일반적인 공격력 랭크업
                            
                            # 방어/특수방어 랭크업
                            elif stat_change.stat in ['defense', 'sp_defense']:
                                reward += 0.2  # 방어력 랭크업
                        
                        # 랭크다운 (자신의 랭크가 깎일 때)
                        elif stat_change.change < 0:
                            reward -= 0.3  # 자신의 랭크 다운에 대한 패널티
                    
                    # 상대의 스탯 변화
                    elif stat_change.target == 'opponent':
                        # 랭크다운
                        if stat_change.change < 0:
                            # 스피드 랭크다운
                            if stat_change.stat == 'speed':
                                if my_speed < enemy_speed:
                                    reward += 0.5  # 상대보다 느린 상태에서 상대 스피드 다운
                                else:
                                    reward += 0.2  # 일반적인 상대 스피드 다운
                            
                            # 공격/특수공격 랭크다운
                            elif stat_change.stat in ['attack', 'sp_attack']:
                                reward += 0.3  # 상대 공격력 다운
                            
                            # 방어/특수방어 랭크다운
                            elif stat_change.stat in ['defense', 'sp_defense']:
                                reward += 0.2  # 상대 방어력 다운
    
    # 5-2. 랭크 다운에 대한 일반적인 패널티 (기술과 관계없이)
    for stat in ['attack', 'defense', 'sp_attack', 'sp_defense', 'speed']:
        if current_pokemon.rank.get(stat, 0) < 0:
            reward -= 0.3  # 랭크 다운에 대한 패널티
    
    # 6. 승리/패배에 따른 보상
    if done:
        if next_hp > 0:
            reward += 100.0  # 승리 보상
        else:
            reward -= 100.0  # 패배 패널티
    
    return reward 