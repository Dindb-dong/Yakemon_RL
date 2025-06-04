#%% [markdown]
# Yakemon 랜덤 에이전트 테스트
# 랜덤 액션 선택을 통한 테스트 스크립트

#%% [markdown]
# 필요한 라이브러리 임포트
import asyncio
import nest_asyncio
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
import random

# 환경 관련 import
from env.battle_env import YakemonEnv

# 유틸리티 관련 import
from utils.battle_logics.create_battle_pokemon import create_battle_pokemon

# RL 관련 import
from RL.reward_calculator import calculate_reward
from RL.get_state_vector import get_state

# 데이터 관련 import
from p_data.move_data import move_data
from p_data.ability_data import ability_data
from p_data.mock_pokemon import create_mock_pokemon_list

# 컨텍스트 관련 import
from context.battle_store import store
from context.duration_store import duration_store


# 전역 변수 초기화
battle_store = store
duration_store = duration_store


# 하이퍼파라미터 설정
HYPERPARAMS = {
    "num_episodes": 1000,
    "save_interval": 100,
    "test_episodes": 100,
    "state_dim": 1165,  # get_state_vector의 출력 차원
    "action_dim": 6,   # 4개의 기술 + 2개의 교체
}

#%% [markdown]
# 랜덤 에이전트 실행 함수 정의
async def run_random_agent(
    env: YakemonEnv,
    num_episodes: int,
    save_path: str = 'results',
    agent_name: str = 'random'
) -> tuple:
    """
    랜덤 에이전트 실행 함수
    """
    rewards_history = []
    
    # 결과 저장 디렉토리 생성
    os.makedirs(save_path, exist_ok=True)
    
    # 하이퍼파라미터 저장
    with open(os.path.join(save_path, f'{agent_name}_hyperparams.json'), 'w') as f:
        json.dump(HYPERPARAMS, f, indent=4)
    
    for episode in range(num_episodes):
        # 1. 팀 생성 단계
        all_pokemon = create_mock_pokemon_list()
        
        # 불, 물, 풀 타입의 포켓몬들을 각각 분류
        fire_pokemon = [p for p in all_pokemon if '불' in p.types]
        water_pokemon = [p for p in all_pokemon if '물' in p.types]
        grass_pokemon = [p for p in all_pokemon if '풀' in p.types]
        
        # 각 타입에서 랜덤하게 3마리씩 선택
        my_team = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        
        # 상대 팀도 동일하게 구성
        enemy_team = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        
        # PokemonInfo를 BattlePokemon으로 변환
        my_team = [create_battle_pokemon(poke) for poke in my_team]
        enemy_team = [create_battle_pokemon(poke) for poke in enemy_team]
        
        # 팀 정보 출력 (딕셔너리 형식)
        print(f"[Episode {episode+1}] My Team (BattlePokemon):")
        for p in my_team:
            print(vars(p))
        print(f"[Episode {episode+1}] My Team (PokemonInfo):")
        for p in my_team:
            print(vars(p.base))
        print(f"[Episode {episode+1}] Enemy Team (BattlePokemon):")
        for p in enemy_team:
            print(vars(p))
        print(f"[Episode {episode+1}] Enemy Team (PokemonInfo):")
        for p in enemy_team:
            print(vars(p.base))
        
        # 2. 배틀 환경 초기화
        state = env.reset(my_team=my_team, enemy_team=enemy_team)
        my_team = env.my_team  # BattlePokemon 객체 리스트로 업데이트
        enemy_team = env.enemy_team  # BattlePokemon 객체 리스트로 업데이트
        store = env.battle_store
        store.set_active_my(0)
        store.set_active_enemy(0)
        total_reward = 0
        steps = 0
        
        # 3. 배틀 루프
        while True:
            # 현재 상태 벡터 생성
            state_vector = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 랜덤 액션 선택
            action = random.randint(0, HYPERPARAMS["action_dim"] - 1)
            
            # 행동 실행
            next_state, reward, done, _ = await env.step(action)
            
            # 다음 상태 벡터 생성
            next_state_vector = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 보상 계산
            reward = calculate_reward(
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects,
                action=action,
                done=done,
                battle_store=env.battle_store,
                duration_store=env.duration_store
            )
            
            state_vector = next_state_vector
            total_reward += reward
            steps += 1
            
            # 배틀이 끝났는지 확인
            if done:
                break
        
        # 에피소드 결과 저장
        avg_reward = total_reward / steps
        rewards_history.append(avg_reward)
        
        # 학습 진행 상황 출력
        print(f'Episode {episode+1}/{num_episodes}')
        print(f'Average Reward: {avg_reward:.2f}')
        print(f'Steps: {steps}')
        print('-' * 50)
    
    return rewards_history

#%% [markdown]
# 시각화 함수 정의
def plot_results(
    rewards_history: list,
    agent_name: str,
    save_path: str = 'results'
) -> None:
    """
    결과 시각화
    
    Args:
        rewards_history: 에피소드별 평균 보상 기록
        agent_name: 에이전트 이름
        save_path: 결과 저장 경로
    """
    os.makedirs(save_path, exist_ok=True)
    
    # 1. 보상 그래프
    plt.figure(figsize=(12, 6))
    plt.plot(rewards_history, label='Average Reward', color='blue', alpha=0.6)
    
    # 이동 평균 추가 (100 에피소드)
    window_size = min(100, len(rewards_history))
    if window_size > 0:
        moving_avg = np.convolve(rewards_history, np.ones(window_size)/window_size, mode='valid')
        plt.plot(range(window_size-1, len(rewards_history)), moving_avg, 
                label=f'{window_size}-Episode Moving Average', color='red', linewidth=2)
    
    plt.title(f'{agent_name} Rewards')
    plt.xlabel('Episode')
    plt.ylabel('Average Reward')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(save_path, f'{agent_name}_rewards.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. 보상 분포 히스토그램
    plt.figure(figsize=(12, 6))
    plt.hist(rewards_history, bins=50, alpha=0.7, color='blue')
    plt.title(f'{agent_name} Reward Distribution')
    plt.xlabel('Average Reward')
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(save_path, f'{agent_name}_reward_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. 학습 통계 저장
    stats = {
        'mean_reward': np.mean(rewards_history),
        'std_reward': np.std(rewards_history),
        'max_reward': np.max(rewards_history),
        'min_reward': np.min(rewards_history),
        'total_episodes': len(rewards_history)
    }
    
    # 통계를 JSON 파일로 저장
    with open(os.path.join(save_path, f'{agent_name}_stats.json'), 'w') as f:
        json.dump(stats, f, indent=4)
    
    # 통계를 텍스트 파일로도 저장
    with open(os.path.join(save_path, f'{agent_name}_stats.txt'), 'w') as f:
        f.write(f"{agent_name} Statistics\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total Episodes: {stats['total_episodes']}\n\n")
        f.write("Reward Statistics:\n")
        f.write(f"  Mean: {stats['mean_reward']:.4f}\n")
        f.write(f"  Std:  {stats['std_reward']:.4f}\n")
        f.write(f"  Max:  {stats['max_reward']:.4f}\n")
        f.write(f"  Min:  {stats['min_reward']:.4f}\n")

#%% [markdown]
# 테스트 함수 정의
async def test_agent(
    env,
    num_episodes: int = 10
) -> tuple:
    """
    랜덤 에이전트 테스트
    """
    rewards = []
    steps_list = []
    victories = 0  # 승리 횟수 추적
    
    for episode in range(num_episodes):
        # 1. 팀 생성 단계
        all_pokemon = create_mock_pokemon_list()
        
        # 불, 물, 풀 타입의 포켓몬들을 각각 분류
        fire_pokemon = [p for p in all_pokemon if '불' in p.types]
        water_pokemon = [p for p in all_pokemon if '물' in p.types]
        grass_pokemon = [p for p in all_pokemon if '풀' in p.types]
        
        # 각 타입에서 랜덤하게 3마리씩 선택
        my_team = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        
        # 상대 팀도 동일하게 구성
        enemy_team = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        
        # PokemonInfo를 BattlePokemon으로 변환
        my_team = [create_battle_pokemon(poke) for poke in my_team]
        enemy_team = [create_battle_pokemon(poke) for poke in enemy_team]
        
        # 2. 배틀 환경 초기화
        state = env.reset(my_team=my_team, enemy_team=enemy_team)
        my_team = env.my_team  # BattlePokemon 객체 리스트로 업데이트
        enemy_team = env.enemy_team  # BattlePokemon 객체 리스트로 업데이트
        
        total_reward = 0
        steps = 0
        
        # 3. 배틀 루프
        while True:
            # 현재 상태 벡터 생성
            state_vector = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 랜덤 액션 선택
            action = random.randint(0, HYPERPARAMS["action_dim"] - 1)
            
            # 행동 실행
            next_state, reward, done, _ = await env.step(action)
            
            # 다음 상태 벡터 생성
            next_state_vector = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 보상 계산
            reward = calculate_reward(
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects,
                action=action,
                done=done,
                battle_store=env.battle_store,
                duration_store=env.duration_store
            )
            
            state_vector = next_state_vector
            total_reward += reward
            steps += 1
            
            # 배틀이 끝났는지 확인
            if done:
                # 승리 여부 확인
                my_team_alive = any(pokemon.current_hp > 0 for pokemon in my_team)
                enemy_team_alive = any(pokemon.current_hp > 0 for pokemon in enemy_team)
                if my_team_alive and not enemy_team_alive:
                    victories += 1
                break
        
        rewards.append(total_reward)
        steps_list.append(steps)
        
        print(f'Test Episode {episode+1}/{num_episodes}')
        print(f'Total Reward: {total_reward:.2f}')
        print(f'Steps: {steps}')
        print('-' * 50)
    
    avg_reward = np.mean(rewards)
    std_reward = np.std(rewards)
    avg_steps = np.mean(steps_list)
    win_rate = (victories / num_episodes) * 100
    
    print(f'\nTest Results:')
    print(f'Average Reward: {avg_reward:.2f} ± {std_reward:.2f}')
    print(f'Average Steps: {avg_steps:.2f}')
    print(f'Victories: {victories}/{num_episodes} (Win Rate: {win_rate:.1f}%)')
    
    return avg_reward, std_reward, avg_steps, victories, win_rate

#%% [markdown]
# 메인 실행 코드
if __name__ == "__main__":
    # Jupyter에서 중첩된 이벤트 루프 허용
    nest_asyncio.apply()
    
    # 결과 저장 디렉토리 설정
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join('results', f'random_{timestamp}')
    
    # 환경 초기화
    env = YakemonEnv()  # 실제 게임 환경
    
    print("Starting Random Agent...")
    print(f"Results will be saved in: {results_dir}")
    print("\nHyperparameters:")
    for key, value in HYPERPARAMS.items():
        print(f"  {key}: {value}")
    print("\n" + "="*50 + "\n")
    
    # 랜덤 에이전트 실행
    rewards = asyncio.run(run_random_agent(
        env=env,
        num_episodes=HYPERPARAMS["num_episodes"],
        save_path=results_dir,
        agent_name='random'
    ))
    
    # 결과 시각화
    plot_results(
        rewards_history=rewards,
        agent_name='Random',
        save_path=results_dir
    )
    
    print("\nRandom agent execution completed!")
    print(f"Results saved in: {results_dir}")
    
    # 랜덤 에이전트 테스트
    print("\nStarting test phase...")
    test_results = asyncio.run(test_agent(
        env=env,
        num_episodes=HYPERPARAMS["test_episodes"]
    ))
    
    # 테스트 결과 저장
    test_stats = {
        'avg_reward': test_results[0],
        'std_reward': test_results[1],
        'avg_steps': test_results[2],
        'victories': test_results[3],
        'win_rate': test_results[4]
    }
    
    with open(os.path.join(results_dir, 'test_results.json'), 'w') as f:
        json.dump(test_stats, f, indent=4)
    
    with open(os.path.join(results_dir, 'test_results.txt'), 'w') as f:
        f.write("Test Results\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Average Reward: {test_stats['avg_reward']:.4f} ± {test_stats['std_reward']:.4f}\n")
        f.write(f"Average Steps: {test_stats['avg_steps']:.2f}\n")
        f.write(f"Victories: {test_stats['victories']}/{HYPERPARAMS['test_episodes']} (Win Rate: {test_stats['win_rate']:.1f}%)\n")
    
    print("\nTest completed!")
    print(f"Test results saved in: {results_dir}")

