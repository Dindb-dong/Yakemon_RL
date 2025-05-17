#%% [markdown]
# Yakemon 강화학습 에이전트 학습
# 각 알고리즘을 독립적으로 테스트하기 위한 스크립트

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

# 모델 관련 import

# 유틸리티 관련 import
from utils.battle_logics.create_battle_pokemon import create_battle_pokemon

# 에이전트 관련 import
from agent.dddqn_agent import DDDQNAgent

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
    "learning_rate": 0.0005,
    "gamma": 0.95,
    "epsilon_start": 1.0,
    "epsilon_end": 0.01,
    "epsilon_decay": 0.997,
    "batch_size": 128,
    "memory_size": 50000,
    "target_update": 20,
    "num_episodes": 50000,
    "save_interval": 50,
    "test_episodes": 50,
    "state_dim": 126,  # get_state_vector의 출력 차원
    "action_dim": 6   # 4개의 기술 + 2개의 교체
}

#%% [markdown]
# 학습 함수 정의
async def train_agent(
    env: YakemonEnv,
    agent: DDDQNAgent,
    num_episodes: int,
    save_path: str = 'models',
    agent_name: str = 'ddqn'
) -> tuple:
    """
    에이전트 학습 함수
    """
    rewards_history = []
    losses_history = []
    best_reward = float('-inf')
    
    # 모델 저장 디렉토리 생성
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
        total_loss = 0
        steps = 0
        
        # 3. 배틀 루프
        while True:
            # 현재 상태 벡터 생성
            state_dict = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env.__dict__,
                my_env=env.my_env.__dict__,
                enemy_env=env.enemy_env.__dict__,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 정해진 순서로 상태 벡터 생성
            state_keys = sorted(state_dict.keys())
            state_vector = [state_dict[key] for key in state_keys]
            
            # 행동 선택 (기술 4개 + 교체 가능한 포켓몬 수)
            action = agent.select_action(state_vector, env.battle_store, env.duration_store)
            
            # 행동 실행
            next_state, reward, done, _ = await env.step(action)
            
            # 다음 상태 벡터 생성
            next_state_dict = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env.__dict__,
                my_env=env.my_env.__dict__,
                enemy_env=env.enemy_env.__dict__,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            next_state_vector = [next_state_dict[key] for key in state_keys]
            
            # 보상 계산
            reward = calculate_reward(
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env.__dict__,
                my_env=env.my_env.__dict__,
                enemy_env=env.enemy_env.__dict__,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects,
                action=action,
                done=done,
                battle_store=env.battle_store,
                duration_store=env.duration_store
            )
            
            # 경험 저장
            agent.store_transition(state_vector, action, reward, next_state_vector, done)
            
            # 학습
            if len(agent.memory) > agent.batch_size:
                loss = agent.update()
                total_loss += loss
            
            state_vector = next_state_vector
            total_reward += reward
            steps += 1
        
            
            # 배틀이 끝났는지 확인
            if done:
                break
        
        # 에피소드 결과 저장
        avg_reward = total_reward / steps
        avg_loss = total_loss / steps if total_loss > 0 else 0
        rewards_history.append(avg_reward)
        losses_history.append(avg_loss)
        
        # 최고 성능 모델 저장
        if avg_reward > best_reward:
            best_reward = avg_reward
            agent.save(os.path.join(save_path, f'{agent_name}_best.pth'))
        
        # 주기적으로 모델 저장
        if (episode + 1) % HYPERPARAMS["save_interval"] == 0:
            agent.save(os.path.join(save_path, f'{agent_name}_episode_{episode+1}.pth'))
        
        # 학습 진행 상황 출력
        print(f'Episode {episode+1}/{num_episodes}')
        print(f'Average Reward: {avg_reward:.2f}')
        print(f'Average Loss: {avg_loss:.4f}')
        print(f'Epsilon: {agent.epsilon:.4f}')
        print(f'Steps: {steps}')
        print('-' * 50)
    
    return rewards_history, losses_history

#%% [markdown]
# 시각화 함수 정의
def plot_training_results(
    rewards_history: list,
    losses_history: list,
    agent_name: str,
    save_path: str = 'results'
) -> None:
    """
    학습 결과 시각화
    
    Args:
        rewards_history: 에피소드별 평균 보상 기록
        losses_history: 에피소드별 평균 손실 기록
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
    
    plt.title(f'{agent_name} Training Rewards')
    plt.xlabel('Episode')
    plt.ylabel('Average Reward')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(save_path, f'{agent_name}_rewards.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. 손실 그래프
    plt.figure(figsize=(12, 6))
    plt.plot(losses_history, label='Average Loss', color='green', alpha=0.6)
    
    # 이동 평균 추가 (100 에피소드)
    if window_size > 0:
        moving_avg = np.convolve(losses_history, np.ones(window_size)/window_size, mode='valid')
        plt.plot(range(window_size-1, len(losses_history)), moving_avg, 
                label=f'{window_size}-Episode Moving Average', color='red', linewidth=2)
    
    plt.title(f'{agent_name} Training Losses')
    plt.xlabel('Episode')
    plt.ylabel('Average Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(save_path, f'{agent_name}_losses.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. 보상 분포 히스토그램
    plt.figure(figsize=(12, 6))
    plt.hist(rewards_history, bins=50, alpha=0.7, color='blue')
    plt.title(f'{agent_name} Reward Distribution')
    plt.xlabel('Average Reward')
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    plt.savefig(os.path.join(save_path, f'{agent_name}_reward_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. 학습 통계 저장
    stats = {
        'mean_reward': float(np.mean(rewards_history)),
        'std_reward': float(np.std(rewards_history)),
        'max_reward': float(np.max(rewards_history)),
        'min_reward': float(np.min(rewards_history)),
        'mean_loss': float(np.mean(losses_history)),
        'std_loss': float(np.std(losses_history)),
        'max_loss': float(np.max(losses_history)),
        'min_loss': float(np.min(losses_history)),
        'total_episodes': int(len(rewards_history))
    }
    
    # 통계를 JSON 파일로 저장
    with open(os.path.join(save_path, f'{agent_name}_stats.json'), 'w') as f:
        json.dump(stats, f, indent=4)
    
    # 통계를 텍스트 파일로도 저장
    with open(os.path.join(save_path, f'{agent_name}_stats.txt'), 'w') as f:
        f.write(f"{agent_name} Training Statistics\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total Episodes: {stats['total_episodes']}\n\n")
        f.write("Reward Statistics:\n")
        f.write(f"  Mean: {stats['mean_reward']:.4f}\n")
        f.write(f"  Std:  {stats['std_reward']:.4f}\n")
        f.write(f"  Max:  {stats['max_reward']:.4f}\n")
        f.write(f"  Min:  {stats['min_reward']:.4f}\n\n")
        f.write("Loss Statistics:\n")
        f.write(f"  Mean: {stats['mean_loss']:.4f}\n")
        f.write(f"  Std:  {stats['std_loss']:.4f}\n")
        f.write(f"  Max:  {stats['max_loss']:.4f}\n")
        f.write(f"  Min:  {stats['min_loss']:.4f}\n")

#%% [markdown]
# 테스트 함수 정의
async def test_agent(
    env,
    agent: DDDQNAgent,
    num_episodes: int = 10
) -> tuple:
    """
    학습된 에이전트 테스트
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
            state_dict = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env.__dict__,
                my_env=env.my_env.__dict__,
                enemy_env=env.enemy_env.__dict__,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            
            # 정해진 순서로 상태 벡터 생성
            state_keys = sorted(state_dict.keys())
            state_vector = [state_dict[key] for key in state_keys]
            
            # 행동 선택 (기술 4개 + 교체 가능한 포켓몬 수)
            action = agent.select_action(state_vector, env.battle_store, env.duration_store)
            
            # 행동 실행
            next_state, reward, done, _ = await env.step(action)
            
            # 다음 상태 벡터 생성
            next_state_dict = get_state(
                store=env.battle_store,
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env.__dict__,
                my_env=env.my_env.__dict__,
                enemy_env=env.enemy_env.__dict__,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            )
            next_state_vector = [next_state_dict[key] for key in state_keys]
            
            # 보상 계산
            reward = calculate_reward(
                my_team=my_team,
                enemy_team=enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env.__dict__,
                my_env=env.my_env.__dict__,
                enemy_env=env.enemy_env.__dict__,
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
    results_dir = os.path.join('results', f'training_{timestamp}')
    models_dir = os.path.join('models', f'training_{timestamp}')
    
    # 환경 초기화
    env = YakemonEnv()  # 실제 게임 환경
    state_dim = HYPERPARAMS["state_dim"]
    action_dim = HYPERPARAMS["action_dim"]
    
    # DDDQN 에이전트 생성
    ddqn_agent = DDDQNAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        learning_rate=HYPERPARAMS["learning_rate"],
        gamma=HYPERPARAMS["gamma"],
        epsilon_start=HYPERPARAMS["epsilon_start"],
        epsilon_end=HYPERPARAMS["epsilon_end"],
        epsilon_decay=HYPERPARAMS["epsilon_decay"],
        target_update=HYPERPARAMS["target_update"],
        memory_size=HYPERPARAMS["memory_size"],
        batch_size=HYPERPARAMS["batch_size"]
    )
    
    print("Starting DDDQN training...")
    print(f"Results will be saved in: {results_dir}")
    print(f"Models will be saved in: {models_dir}")
    print("\nHyperparameters:")
    for key, value in HYPERPARAMS.items():
        print(f"  {key}: {value}")
    print("\n" + "="*50 + "\n")
    
    # DDDQN 에이전트 학습
    ddqn_rewards, ddqn_losses = asyncio.run(train_agent(
        env=env,
        agent=ddqn_agent,
        num_episodes=HYPERPARAMS["num_episodes"],
        save_path=models_dir,
        agent_name='ddqn'
    ))
    
    # 학습 결과 시각화
    plot_training_results(
        rewards_history=ddqn_rewards,
        losses_history=ddqn_losses,
        agent_name='DDDQN',
        save_path=results_dir
    )
    
    print("\nTraining completed!")
    print(f"Results saved in: {results_dir}")
    print(f"Models saved in: {models_dir}")
    
    # 학습된 에이전트 테스트
    print("\nStarting test phase...")
    test_results = asyncio.run(test_agent(
        env=env,
        agent=ddqn_agent,
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

