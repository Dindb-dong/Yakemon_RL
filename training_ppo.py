# Yakemon 강화학습 에이전트 학습 (PPO)
# 각 알고리즘을 독립적으로 테스트하기 위한 스크립트

# 필요한 라이브러리 임포트
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
import random
import gymnasium as gym
import torch.nn as nn

# 환경 관련 import
from env.battle_env import YakemonEnv

# 모델 관련 import
from stable_baselines3 import PPO
from sb3_contrib import MaskablePPO
from stable_baselines3.common.callbacks import BaseCallback

# 유틸리티 관련 import
from utils.battle_logics.create_battle_pokemon import create_battle_pokemon
from utils.visualization import plot_training_results

# RL 관련 import
from RL.get_state_vector import get_state

# 데이터 관련 import
from p_data.move_data import move_data
from p_data.ability_data import ability_data
from p_data.mock_pokemon import create_mock_pokemon_list

# PPO용 하이퍼파라미터 설정
HYPERPARAMS_PPO = {
    "policy": "MlpPolicy",
    "learning_rate": 3e-4,
    "n_steps": 2048, # 각 업데이트 전에 실행할 스텝 수
    "batch_size": 64, # PPO 미니배치 크기
    "n_epochs": 10, # 각 데이터 수집 후 최적화 에폭 수
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    "total_timesteps": 1000000, # 총 학습 타임스텝
    "save_freq": 100000, # 타임스텝 기준 저장 빈도
    "test_episodes": 300,
    "state_dim": 1165,  # get_state_vector의 출력 차원
    "action_dim": 6   # 4개의 기술 + 2개의 교체 (YakemonEnv.action_space와 일치해야 함)
}

# 주기적 저장을 위한 콜백 정의
class SaveOnBestTrainingRewardCallback(BaseCallback):
    def __init__(self, save_freq: int, save_path: str, agent_name: str = 'ppo', verbose: int = 0):
        super(SaveOnBestTrainingRewardCallback, self).__init__(verbose)
        self.save_freq = save_freq
        self.save_path = save_path
        self.agent_name = agent_name
        os.makedirs(self.save_path, exist_ok=True)

    def _on_step(self) -> bool:
        if self.n_calls % self.save_freq == 0:
            model_path = os.path.join(self.save_path, f'{self.agent_name}_step_{self.num_timesteps}.zip')
            self.model.save(model_path)
            if self.verbose > 0:
                print(f"Saving model to {model_path}")
        return True

# 학습 함수 정의
def train_ppo_agent(
    env: YakemonEnv,  # YakemonEnv가 Gym 환경 인터페이스를 따르도록 수정 필요
    agent: MaskablePPO,
    total_timesteps: int,
    save_path: str = 'models',
    agent_name: str = 'ppo',
    save_freq: int = 50000
) -> tuple:
    """
    PPO 에이전트 학습 함수

    Args:
        env: 학습 환경 (YakemonEnv 인스턴스)
        agent: 학습할 PPO 에이전트
        total_timesteps: 총 학습 타임스텝
        save_path: 모델 저장 경로
        agent_name: 에이전트 이름
        save_freq: 모델 저장 빈도 (타임스텝 기준)

    Returns:
        tuple: (empty_rewards_history, empty_losses_history, empty_victories_history)
               PPO는 학습 중 상세 로그를 콜백이나 TensorBoard를 통해 관리
    """
    # 모델 저장 디렉토리 생성
    os.makedirs(save_path, exist_ok=True)

    # 하이퍼파라미터 저장
    with open(os.path.join(save_path, f'{agent_name}_hyperparams.json'), 'w') as f:
        serializable_hyperparams = {k: str(v) if callable(v) or isinstance(v, type) else v for k, v in HYPERPARAMS_PPO.items()}
        json.dump(serializable_hyperparams, f, indent=4)

    # 콜백 설정
    save_callback = SaveOnBestTrainingRewardCallback(save_freq=save_freq, save_path=save_path, agent_name=agent_name)

    print(f"Starting PPO training for {total_timesteps} timesteps using YakemonEnv...")
    agent.learn(total_timesteps=total_timesteps, callback=save_callback)

    print("PPO training finished.")

    return [], [], []  # 빈 리스트 반환

# 테스트 함수 정의
def test_ppo_agent(
    env: YakemonEnv, # YakemonEnv가 Gym 환경 인터페이스를 따르도록 수정 필요
    agent: MaskablePPO,
    num_episodes: int = 10
) -> tuple:
    """
    학습된 PPO 에이전트 테스트
    """
    rewards = []
    steps_list = []
    victories = 0

    for episode in range(num_episodes):
        # 1. 팀 생성 단계 (기존 로직 유지)
        all_pokemon = create_mock_pokemon_list()
        fire_pokemon = [p for p in all_pokemon if '불' in p.types]
        water_pokemon = [p for p in all_pokemon if '물' in p.types]
        grass_pokemon = [p for p in all_pokemon if '풀' in p.types]
        
        my_team_info = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        enemy_team_info = (
            random.sample(fire_pokemon, 1) +
            random.sample(water_pokemon, 1) +
            random.sample(grass_pokemon, 1)
        )
        
        my_team_bp = [create_battle_pokemon(poke) for poke in my_team_info]
        enemy_team_bp = [create_battle_pokemon(poke) for poke in enemy_team_info]

        # 2. 배틀 환경 초기화
        obs_dict = env.reset()
        current_my_team = env.my_team
        current_enemy_team = env.enemy_team
        
        # get_state를 사용하여 SB3 PPO가 이해할 수 있는 상태 벡터로 변환
        state_vector = get_state(
            store=env.battle_store,
            my_team=current_my_team,
            enemy_team=current_enemy_team,
            active_my=env.battle_store.get_active_index("my"),
            active_enemy=env.battle_store.get_active_index("enemy"),
            public_env=env.public_env,
            my_env=env.my_env,
            enemy_env=env.enemy_env,
            turn=env.turn,
            my_effects=env.duration_store.my_effects,
            enemy_effects=env.duration_store.enemy_effects
        ).astype(np.float32)
        
        total_reward = 0
        steps = 0
        done = False
        truncated = False # Gymnasium 스타일
        
        # 3. 배틀 루프
        while not (done or truncated):
            # 행동 선택
            action, _states = agent.predict(state_vector, deterministic=True, action_masks=env.action_masks())
            
            # 행동 실행 (env.step은 (obs, reward, terminated, truncated, info)를 반환해야 함)
            next_obs_dict, reward, terminated, truncated, info = env.step(action)
            done = terminated

            current_my_team = env.my_team # 매 스텝마다 팀 상태 업데이트
            current_enemy_team = env.enemy_team

            # 다음 상태 벡터 생성
            next_state_vector = get_state(
                store=env.battle_store,
                my_team=current_my_team,
                enemy_team=current_enemy_team,
                active_my=env.battle_store.get_active_index("my"),
                active_enemy=env.battle_store.get_active_index("enemy"),
                public_env=env.public_env,
                my_env=env.my_env,
                enemy_env=env.enemy_env,
                turn=env.turn,
                my_effects=env.duration_store.my_effects,
                enemy_effects=env.duration_store.enemy_effects
            ).astype(np.float32)
            
            state_vector = next_state_vector
            total_reward += reward
            steps += 1
            
            if done or truncated:
                # 승리 여부 확인
                my_team_alive = any(pokemon.current_hp > 0 for pokemon in current_my_team)
                enemy_team_alive = any(pokemon.current_hp > 0 for pokemon in current_enemy_team)
                if my_team_alive and not enemy_team_alive:
                    victories += 1
                break
        
        rewards.append(total_reward)
        steps_list.append(steps)
        
        print(f'Test Episode {episode+1}/{num_episodes}')
        print(f'Total Reward: {total_reward:.2f}')
        print(f'Steps: {steps}')
        print('-' * 50)
    
    avg_reward = np.mean(rewards) if rewards else 0
    std_reward = np.std(rewards) if rewards else 0
    avg_steps = np.mean(steps_list) if steps_list else 0
    win_rate = (victories / num_episodes) * 100 if num_episodes > 0 else 0
    
    print(f'Test Results:')
    print(f'Average Reward: {avg_reward:.2f} ± {std_reward:.2f}')
    print(f'Average Steps: {avg_steps:.2f}')
    print(f'Victories: {victories}/{num_episodes} (Win Rate: {win_rate:.1f}%)')
    
    return avg_reward, std_reward, avg_steps, victories, win_rate

# 메인 실행 코드
if __name__ == "__main__":
    # nest_asyncio는 더 이상 필요 없음
    
    # 결과 저장 디렉토리 설정
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = os.path.join('results', f'ppo_training_{timestamp}')
    models_dir = os.path.join('models', f'ppo_training_{timestamp}')
    
    # 환경 초기화
    env = YakemonEnv()

    # PPO 에이전트 생성
    ppo_agent = MaskablePPO(
        policy=HYPERPARAMS_PPO["policy"],
        env=env, # SB3는 env를 직접 받음
        learning_rate=HYPERPARAMS_PPO["learning_rate"],
        n_steps=HYPERPARAMS_PPO["n_steps"],
        batch_size=HYPERPARAMS_PPO["batch_size"],
        n_epochs=HYPERPARAMS_PPO["n_epochs"],
        gamma=HYPERPARAMS_PPO["gamma"],
        gae_lambda=HYPERPARAMS_PPO["gae_lambda"],
        clip_range=HYPERPARAMS_PPO["clip_range"],
        ent_coef=HYPERPARAMS_PPO["ent_coef"],
        vf_coef=HYPERPARAMS_PPO["vf_coef"],
        max_grad_norm=HYPERPARAMS_PPO["max_grad_norm"],
        verbose=1, # SB3 내부 로그 출력
        tensorboard_log=results_dir, # TensorBoard 로그 경로 지정
        policy_kwargs={
            'net_arch': dict(pi=[512, 256, 128, 64], vf=[512, 256, 128, 64]),  # MLP 정책의 네트워크 아키텍처
            'activation_fn': nn.ReLU  # 활성화 함수
        }
    )
    
    print("Starting PPO training...")
    print(f"Results will be saved in: {results_dir}")
    print(f"Models will be saved in: {models_dir}")
    print("PPO Hyperparameters:")
    for key, value in HYPERPARAMS_PPO.items():
        print(f"  {key}: {value}")
    print("" + "="*50 + "")
    
    # PPO 에이전트 학습
    ppo_rewards, ppo_losses, ppo_victories = train_ppo_agent(
        env=env,
        agent=ppo_agent,
        total_timesteps=HYPERPARAMS_PPO["total_timesteps"],
        save_path=models_dir,
        agent_name='ppo',
        save_freq=HYPERPARAMS_PPO["save_freq"]
    )
    
    # 학습 결과 시각화
    # PPO의 경우, rewards_history, losses_history가 비어있으므로,
    # plot_training_results 함수는 이들을 처리할 수 있도록 수정되거나,
    # TensorBoard 로그를 사용하여 시각화해야 함.
    # plot_training_results(
    #     rewards_history=ppo_rewards, # 비어 있음
    #     losses_history=ppo_losses,   # 비어 있음
    #     agent_name='PPO',
    #     save_path=results_dir,
    #     victories_history=ppo_victories # 비어 있음
    # )
    
    print("Training completed!")
    print(f"Results saved in: {results_dir}")
    print(f"Models saved in: {models_dir}")
    
    # 학습된 에이전트 테스트
    print("Starting PPO test phase...")
    test_results = test_ppo_agent(
        env=env, # 테스트에도 동일한 (또는 새로 생성된) Gym 호환 환경 사용
        agent=ppo_agent, # 학습된 PPO 에이전트
        num_episodes=HYPERPARAMS_PPO["test_episodes"]
    )
    
    # 테스트 결과 저장
    test_stats = {
        'avg_reward': test_results[0],
        'std_reward': test_results[1],
        'avg_steps': test_results[2],
        'victories': test_results[3],
        'win_rate': test_results[4]
    }
    
    with open(os.path.join(results_dir, 'test_results_ppo.json'), 'w') as f:
        json.dump(test_stats, f, indent=4)
    
    with open(os.path.join(results_dir, 'test_results_ppo.txt'), 'w') as f:
        f.write("PPO Test Results")
        f.write("=" * 50 + "")
        f.write(f"Average Reward: {test_stats['avg_reward']:.4f} ± {test_stats['std_reward']:.4f}")
        f.write(f"Average Steps: {test_stats['avg_steps']:.2f}")
        f.write(f"Victories: {test_stats['victories']}/{HYPERPARAMS_PPO['test_episodes']} (Win Rate: {test_stats['win_rate']:.1f}%)")
    
    print("PPO Test completed!")
    print(f"Test results saved in: {results_dir}")

