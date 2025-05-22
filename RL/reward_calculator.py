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
    전략적 요소를 고려한 최적화된 보상 계산
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
    
    # 학습 단계에 따른 가중치 계산
    episode = battle_store.episode if hasattr(battle_store, 'episode') else 0
    if not hasattr(battle_store, 'total_episodes'):
        raise ValueError("total_episodes not set in battle_store. Please set battle_store.total_episodes before training.")
    total_episodes = battle_store.total_episodes
    learning_stage = min(float(episode) / float(total_episodes), 1.0)  # 전체 에피소드 수에 따른 점진적 증가
    print(f"total_episodes: {total_episodes}")
    print(f"learning_stage: {learning_stage}")

    if learning_stage < 0.7:
        # 1. HP 변화에 따른 보상 (가중치 증가 및 상대적 차이 고려)
        my_hp_ratio = current_pokemon.current_hp / current_pokemon.base.hp
        enemy_hp_ratio = target_pokemon.current_hp / target_pokemon.base.hp
        hp_advantage = my_hp_ratio - enemy_hp_ratio
        reward += hp_advantage * 0.1  # HP 상대적 우위에 작은 가중치 부여 (3.0 -> 0.1)
        
        # HP 변화에 대한 추가 보상/패널티
        hp_change = my_hp_ratio - enemy_hp_ratio  # 내 HP 변화를 기준으로 계산
        reward += hp_change * 0.05  # 내 HP가 증가하면 작은 보상 (0.2 -> 0.05)
        
        # 2. 전체 팀 HP 상태 평가
        my_team_hp_total = sum(p.current_hp for p in my_team if p.current_hp > 0)
        my_team_hp_max = sum(p.base.hp for p in my_team if p.current_hp > 0)
        enemy_team_hp_total = sum(p.current_hp for p in enemy_team if p.current_hp > 0)
        enemy_team_hp_max = sum(p.base.hp for p in enemy_team if p.current_hp > 0)
        
        # 팀 HP 비율 계산 (0으로 나누기 방지)
        my_team_hp_ratio = my_team_hp_total / my_team_hp_max if my_team_hp_max > 0 else 0.0
        enemy_team_hp_ratio = enemy_team_hp_total / enemy_team_hp_max if enemy_team_hp_max > 0 else 0.0
        team_hp_ratio_advantage = my_team_hp_ratio - enemy_team_hp_ratio
        reward += team_hp_ratio_advantage * 0.1  # 전체 팀 HP 우위에 작은 가중치 부여 (2.0 -> 0.1)
    
    
    # 3. 타입 상성 및 기술 선택에 따른 보상
    if learning_stage < 0.5:
        if action < 4:  # 기술 사용
            move = current_pokemon.base.moves[action]
            type_effectiveness = calculate_type_effectiveness(move.type, target_pokemon.base.types)
            
            # 타입 상성에 대한 보상 (차등적 가중치)
            if type_effectiveness >= 2.0:  # 효과가 굉장함
                reward += 0.2  # 5.0 -> 0.2
            elif type_effectiveness >= 1.0:  # 보통 이상
                reward += 0.05  # 1.0 -> 0.05
            elif type_effectiveness > 0.0 and type_effectiveness < 1.0:  # 효과가 별로인 경우
                reward -= 0.05  # -1.0 -> -0.05
            elif type_effectiveness == 0.0:  # 효과가 없음
                reward -= 0.2  # -5.0 -> -0.2
            
            # 기술 카테고리 및 효과 고려
            if move.category != '변화':  # 공격 기술
                # 위력 기반 보상
                power_reward = min(move.power * 0.001, 0.1)  # 위력에 비례하지만 상한선 설정 (0.02 -> 0.001)
                reward += power_reward
                
                # 상대방 HP가 낮을 때 마무리 공격에 대한 보너스
                if enemy_hp_ratio < 0.3 and move.power > 50:
                    reward += 0.15  # 3.0 -> 0.15
            else:  # 변화 기술
                # 상태이상 부여 능력 있는 변화 기술에 보너스
                if hasattr(move, 'status_effect') and move.status_effect:
                    if not target_status:  # 상태이상이 없는 경우
                        if enemy_hp_ratio > 0.5:  # 상대 HP가 높을 때 상태이상 부여는 더 가치있음
                            reward += 0.1  # 2.0 -> 0.1
                        else:
                            reward += 0.05  # 1.0 -> 0.05
                    else:
                        # 이미 상태이상인데 또 같은 상태이상 기술 사용 시 패널티
                        if move.status_effect in target_status:
                            reward -= 0.2  # -4.0 -> -0.2
                
                # 자신 강화 기술에 보너스
                if hasattr(move, 'boost_self') and move.boost_self:
                    if my_hp_ratio > 0.7:  # HP가 높을 때 강화는 더 가치있음
                        reward += 0.075  # 1.5 -> 0.075
                    else:
                        reward += 0.025  # 0.5 -> 0.025
            
            # 우선도 기술 전략적 사용
            if move.priority > 0 and enemy_hp_ratio < 0.2:
                reward += 0.15  # 3.0 -> 0.15
            
            # 특성 상호작용 고려 (특성으로 인한 역효과 패널티 강화)
            if target_pokemon.base.ability:
                ability_name = target_pokemon.base.ability.name
                
                # 다양한 특성 무효화 확인
                immunity_conditions = [
                    # 타입 무효화 특성
                    (ability_name in ["저수", "마중물", "건조피부", "증기기관"] and move.type == "물"),
                    (ability_name in ["타오르는불꽃", "증기기관"] and move.type == "불"),
                    (ability_name in ["흙먹기", "부유"] and move.type == "땅"),
                    (ability_name == "초식" and move.type == "풀"),
                    (ability_name in ["피뢰침", "전기엔진"] and move.type == "전기"),
                    
                    # 계열 무효화 특성
                    (ability_name == "방진" and move.affiliation == "가루"),
                    (ability_name == "방탄" and move.affiliation == "폭탄"),
                    (ability_name == "여왕의위엄" and move.priority > 0),
                    (ability_name == "방음" and move.affiliation == "소리")
                ]
                
                if any(immunity_conditions):
                    reward -= 0.2  # 특성으로 인한 무효화에 대한 큰 패널티
            
            # 4. 랭크업/다운에 따른 보상
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
                                        reward += 0.02  # 상대보다 느린 상태에서 스피드 랭크업
                                    else:
                                        reward += 0.01  # 일반적인 스피드 랭크업
                                
                                # 공격/특수공격 랭크업
                                elif stat_change.stat in ['attack', 'sp_attack']:
                                    if my_speed > enemy_speed:
                                        reward += 0.02  # 상대보다 빠른 상태에서 공격력 랭크업
                                    else:
                                        reward += 0.01  # 일반적인 공격력 랭크업
                                
                                # 방어/특수방어 랭크업
                                elif stat_change.stat in ['defense', 'sp_defense']:
                                    reward += 0.01  # 방어력 랭크업
                            
                            # 랭크다운 (자신의 랭크가 깎일 때)
                            elif stat_change.change < 0:
                                reward -= 0.01  # 자신의 랭크 다운에 대한 패널티
                        
                        # 상대의 스탯 변화
                        elif stat_change.target == 'opponent':
                            # 랭크다운
                            if stat_change.change < 0:
                                # 스피드 랭크다운
                                if stat_change.stat == 'speed':
                                    if my_speed < enemy_speed:
                                        reward += 0.02  # 상대보다 느린 상태에서 상대 스피드 다운
                                    else:
                                        reward += 0.01  # 일반적인 상대 스피드 다운
                                
                                # 공격/특수공격 랭크다운
                                elif stat_change.stat in ['attack', 'sp_attack']:
                                    reward += 0.01  # 상대 공격력 다운
                                
                                # 방어/특수방어 랭크다운
                                elif stat_change.stat in ['defense', 'sp_defense']:
                                    reward += 0.01  # 상대 방어력 다운
    
    # 4-2. 랭크 다운에 대한 일반적인 패널티 (기술과 관계없이)
    if learning_stage < 0.5:
        for stat in ['attack', 'defense', 'sp_attack', 'sp_defense', 'speed']:
            if current_pokemon.rank.get(stat, 0) < 0:
                reward -= 0.015  # -0.3 -> -0.015
    
    # 5. 교체 전략에 따른 보상 (교체 인센티브 강화)
    if learning_stage < 0.3:
        if action >= 4:  # 교체
            switch_index = action - 4
            if 0 <= switch_index < len(my_team):
                next_pokemon = my_team[switch_index]
                
                # 타입 상성 고려한 교체 보상
                next_pokemon_types = next_pokemon.base.types
                enemy_types = target_pokemon.base.types
                
                # 교체 후 타입 상성 계산
                type_advantage = 0
                for my_type in next_pokemon_types:
                    for enemy_type in enemy_types:
                        effectiveness = calculate_type_effectiveness(my_type, [enemy_type])
                        type_advantage += effectiveness - 1.0  # 기준점(1.0)으로부터의 편차
                
                # 타입 우위에 따른 보상
                if type_advantage > 0:
                    reward += type_advantage * 0.075  # 1.5 -> 0.075
    
    # 6. 상태이상 관리에 따른 보상
    if learning_stage < 0.3:
        current_status = current_pokemon.status
        target_status = target_pokemon.status
        
        # 자신의 상태이상 제거 시 보상
        if current_status and (action >= 4 or (action < 4 and hasattr(move, 'heal_status') and move.heal_status)):
            reward += 0.125  # 2.5 -> 0.125
    
    # 10. 승리/패배에 따른 보상 (가장 중요한 요소)
    if done:
        # 살아있는 포켓몬 수 우위에 대한 보상
        my_pokemon_alive = sum(1 for p in my_team if p.current_hp > 0)
        enemy_pokemon_alive = sum(1 for p in enemy_team if p.current_hp > 0)
        pokemon_count_difference = my_pokemon_alive - enemy_pokemon_alive
        
        # 포켓몬 수 차이에 따른 보상 계산 (이 값은 그대로 유지 - 승리/패배가 가장 중요)
        if pokemon_count_difference <= -3:
            reward -= 3.0  # 상대가 3마리 이상 많음
        elif pokemon_count_difference == -2:
            reward -= 2.0  # 상대가 2마리 많음
        elif pokemon_count_difference == -1:
            reward -= 1.0  # 상대가 1마리 많음
        elif pokemon_count_difference == 1:
            reward += 1.0  # 내가 1마리 많음
        elif pokemon_count_difference == 2:
            reward += 2.0  # 내가 2마리 많음
        elif pokemon_count_difference >= 3:
            reward += 3.0  # 내가 3마리 이상 많음
    
    return reward