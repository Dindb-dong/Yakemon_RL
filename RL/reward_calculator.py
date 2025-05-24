from typing import Union
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
    result: dict[str, Union[bool, int]] = None,
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

    # 교체 후 타입 상성에 따른 보상 계산
    if action >= 4:  # 교체 행동인 경우 (action 4, 5는 교체)
        # damage_calculator.py에서 계산된 was_effective와 was_null 값 사용
        was_effective = result.get('was_effective', 0)
        was_null = result.get('was_null', False)
        print(f"was_effective: {was_effective}")
        if was_null:
            reward += 0.2  # 효과 없는 공격에 대한 보상
            print(f"Good switch: Immune to attack! Reward: {reward}")
        elif was_effective == 2:  # 4배 이상 데미지
            reward -= 0.1  # 매우 큰 페널티
            print(f"Warning: Switched into 4x weakness! Reward: {reward}")
        elif was_effective == 1:  # 2배 데미지
            reward -= 0.05  # 적당한 페널티
            print(f"Warning: Switched into 2x weakness! Reward: {reward}")
        elif was_effective == -1:  # 1/2 데미지
            reward += 0.05 # 적당한 보상
            print(f"Good switch: Resistant to 1/2 damage! Reward: {reward}")
        elif was_effective == -2:  # 1/4 데미지
            reward += 0.1  # 매우 큰 보상
            print(f"Good switch: Resistant to 1/4 damage! Reward: {reward}")

    # 승리/패배에 따른 보상 (가장 중요한 요소)
    if done:
        # 살아있는 포켓몬 수 우위에 대한 보상
        my_pokemon_alive = sum(1 for p in my_team if p.current_hp > 0)
        enemy_pokemon_alive = sum(1 for p in enemy_team if p.current_hp > 0)
        pokemon_count_difference = my_pokemon_alive - enemy_pokemon_alive
        
        # 포켓몬 수 차이에 따른 보상 계산 (이 값은 그대로 유지 - 승리/패배가 가장 중요)
        if pokemon_count_difference <= -3:
            reward -= 5.0  # 상대가 3마리 이상 많음
        elif pokemon_count_difference == -2:
            reward -= 2.0  # 상대가 2마리 많음
        elif pokemon_count_difference == -1:
            reward -= 0.5  # 상대가 1마리 많음
        elif pokemon_count_difference == 1:
            reward += 1.0  # 내가 1마리 많음
        elif pokemon_count_difference == 2:
            reward += 2.0  # 내가 2마리 많음
        elif pokemon_count_difference >= 3:
            reward += 5.0  # 내가 3마리 이상 많음
    
    return reward