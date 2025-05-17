import os
import numpy as np
import matplotlib.pyplot as plt
import json

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
    
    # 1. 보상 및 승률 그래프
    plt.figure(figsize=(15, 8))
    
    # 보상 그래프
    plt.subplot(2, 1, 1)
    plt.plot(rewards_history, label='Average Reward', color='blue', alpha=0.6)
    
    # 이동 평균 추가 (100 에피소드)
    window_size = min(100, len(rewards_history))
    if window_size > 0:
        moving_avg = np.convolve(rewards_history, np.ones(window_size)/window_size, mode='valid')
        plt.plot(range(window_size-1, len(rewards_history)), moving_avg, 
                label=f'{window_size}-Episode Moving Average', color='red', linewidth=2)
    
    plt.title(f'{agent_name} Training Progress')
    plt.ylabel('Average Reward')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 손실 그래프
    plt.subplot(2, 1, 2)
    plt.plot(losses_history, label='Average Loss', color='green', alpha=0.6)
    
    if window_size > 0:
        moving_avg = np.convolve(losses_history, np.ones(window_size)/window_size, mode='valid')
        plt.plot(range(window_size-1, len(losses_history)), moving_avg, 
                label=f'{window_size}-Episode Moving Average', color='red', linewidth=2)
    
    plt.xlabel('Episode')
    plt.ylabel('Average Loss')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_path, f'{agent_name}_training_progress.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. 보상 분포 분석
    plt.figure(figsize=(15, 5))
    
    # 보상 분포 히스토그램
    plt.subplot(1, 2, 1)
    plt.hist(rewards_history, bins=50, alpha=0.7, color='blue')
    plt.title(f'{agent_name} Reward Distribution')
    plt.xlabel('Average Reward')
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    
    # 보상 누적 분포
    plt.subplot(1, 2, 2)
    sorted_rewards = np.sort(rewards_history)
    p = 1. * np.arange(len(sorted_rewards)) / (len(sorted_rewards) - 1)
    plt.plot(sorted_rewards, p, color='red')
    plt.title(f'{agent_name} Reward Cumulative Distribution')
    plt.xlabel('Average Reward')
    plt.ylabel('Cumulative Probability')
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(save_path, f'{agent_name}_reward_analysis.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. 학습 통계 저장
    stats = {
        'mean_reward': float(np.mean(rewards_history)),
        'std_reward': float(np.std(rewards_history)),
        'max_reward': float(np.max(rewards_history)),
        'min_reward': float(np.min(rewards_history)),
        'mean_loss': float(np.mean(losses_history)),
        'std_loss': float(np.std(losses_history)),
        'max_loss': float(np.max(losses_history)),
        'min_loss': float(np.min(losses_history)),
        'total_episodes': int(len(rewards_history)),
        'positive_reward_ratio': float(np.mean(np.array(rewards_history) > 0)),
        'reward_quartiles': {
            'q1': float(np.percentile(rewards_history, 25)),
            'q2': float(np.percentile(rewards_history, 50)),
            'q3': float(np.percentile(rewards_history, 75))
        }
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
        f.write(f"  Min:  {stats['min_reward']:.4f}\n")
        f.write(f"  Positive Reward Ratio: {stats['positive_reward_ratio']:.2%}\n")
        f.write(f"  Quartiles:\n")
        f.write(f"    Q1 (25%): {stats['reward_quartiles']['q1']:.4f}\n")
        f.write(f"    Q2 (50%): {stats['reward_quartiles']['q2']:.4f}\n")
        f.write(f"    Q3 (75%): {stats['reward_quartiles']['q3']:.4f}\n\n")
        f.write("Loss Statistics:\n")
        f.write(f"  Mean: {stats['mean_loss']:.4f}\n")
        f.write(f"  Std:  {stats['std_loss']:.4f}\n")
        f.write(f"  Max:  {stats['max_loss']:.4f}\n")
        f.write(f"  Min:  {stats['min_loss']:.4f}\n") 