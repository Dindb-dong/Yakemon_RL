import os
import numpy as np
import matplotlib.pyplot as plt
import json
import re
import sys
from io import StringIO
from contextlib import contextmanager

@contextmanager
def capture_output():
    """표준 출력을 캡처하면서 동시에 화면에도 출력하는 컨텍스트 매니저"""
    new_out = StringIO()
    old_out = sys.stdout
    
    class TeeOutput:
        def __init__(self, original, capture):
            self.original = original
            self.capture = capture
        
        def write(self, text):
            self.original.write(text)  # 화면에 출력
            self.capture.write(text)   # 캡처
            
        def flush(self):
            self.original.flush()
            self.capture.flush()
    
    try:
        sys.stdout = TeeOutput(old_out, new_out)
        yield new_out
    finally:
        sys.stdout = old_out

def analyze_battle_statistics(log_lines: list, total_episodes: int) -> tuple:
    """
    배틀 로그를 분석하여 통계를 추출
    
    Args:
        log_lines: 배틀 로그 라인들의 리스트
        total_episodes: 총 에피소드 수
    
    Returns:
        tuple: (super_effective_moves, ineffective_moves, switches, alive_enemies_distribution)
    """
    # 100판 단위로 통계를 저장할 리스트 초기화
    num_bins = (total_episodes + 99) // 100
    super_effective_moves = [0] * num_bins
    ineffective_moves = [0] * num_bins
    switches = [0] * num_bins
    
    # Alive Enemies 분포를 저장할 2차원 리스트 초기화
    # [구간][남은 포켓몬 수(0-3)] 형태로 저장
    alive_enemies_distribution = [[0] * 4 for _ in range(num_bins)]
    
    current_episode = 0
    current_alive_enemies = None
    
    for line in log_lines:
        # 에피소드 시작 확인
        if "Episode" in line:
            match = re.search(r"Episode (\d+)", line)
            if match:
                current_episode = int(match.group(1))
                current_alive_enemies = None  # 에피소드 시작시 초기화
        
        # 효과가 굉장한 기술 사용 확인
        if "효과가 굉장했다" in line and 'my' in line:
            bin_index = current_episode // 100
            if bin_index < len(super_effective_moves):
                super_effective_moves[bin_index] += 1
        
        # 효과가 없는 기술 사용 확인
        if "효과가 없었다" in line and 'my' in line:
            bin_index = current_episode // 100
            if bin_index < len(ineffective_moves):
                ineffective_moves[bin_index] += 1
        
        # 교체 확인
        if "내가 교체하려는 포켓몬" in line:
            bin_index = current_episode // 100
            if bin_index < len(switches):
                switches[bin_index] += 1
        
        # 상대 포켓몬 쓰러뜨림 확인
        if "Alive Enemies" in line:
            match = re.search(r"Alive Enemies: (\d+)", line)
            if match:
                remaining = int(match.group(1))
                current_alive_enemies = remaining
                bin_index = current_episode // 100
                if bin_index < len(alive_enemies_distribution):
                    # 0-3 사이의 값으로 제한
                    remaining = min(3, max(0, remaining))
                    alive_enemies_distribution[bin_index][remaining] += 1
    
    return super_effective_moves, ineffective_moves, switches, alive_enemies_distribution

def plot_training_results(
    rewards_history: list,
    losses_history: list,
    agent_name: str,
    save_path: str = 'results',
    victories_history: list = None,  # 승리 기록 추가
    log_lines: list = None  # 로그 라인 리스트 추가
) -> None:
    """
    학습 결과 시각화
    
    Args:
        rewards_history: 에피소드별 평균 보상 기록
        losses_history: 에피소드별 평균 손실 기록
        agent_name: 에이전트 이름
        save_path: 결과 저장 경로
        victories_history: 에피소드별 승리 여부 기록 (1: 승리, 0: 패배)
        log_lines: 배틀 로그 라인들의 리스트
    """
    os.makedirs(save_path, exist_ok=True)
    
    # 1. 보상, 승리 횟수 및 손실 그래프
    plt.figure(figsize=(15, 12))
    
    # 보상 그래프
    plt.subplot(3, 1, 1)
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
    
    # 누적 승리 횟수 그래프 추가
    if victories_history is not None:
        plt.subplot(3, 1, 2)
        # 누적 승리 횟수 계산
        cumulative_victories = np.cumsum(victories_history)
        episodes = np.arange(1, len(victories_history) + 1)
        
        plt.plot(episodes, cumulative_victories, label='Cumulative Victories', color='purple', alpha=0.6)
        plt.ylabel('Number of Victories')
        plt.legend()
        plt.grid(True, alpha=0.3)
    
    # 손실 그래프
    plt.subplot(3, 1, 3)
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
    
    # 3. 배틀 통계 분석 (로그 라인이 제공된 경우)
    if log_lines:
        super_effective_moves, ineffective_moves, switches, alive_enemies_distribution = analyze_battle_statistics(log_lines, len(rewards_history))
        
        plt.figure(figsize=(15, 15))
        
        # 효과가 굉장한 기술 사용 횟수
        plt.subplot(4, 1, 1)
        episodes = np.arange(0, len(rewards_history), 100)
        plt.bar(episodes, super_effective_moves, width=80, alpha=0.7, color='red', label='Super Effective')
        plt.bar(episodes, ineffective_moves, width=80, alpha=0.7, color='gray', label='Ineffective', bottom=super_effective_moves)
        plt.title(f'{agent_name} Move Effectiveness per 100 Episodes')
        plt.xlabel('Episode')
        plt.ylabel('Number of Moves')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 교체 횟수
        plt.subplot(4, 1, 2)
        plt.bar(episodes, switches, width=80, alpha=0.7, color='blue')
        plt.title(f'{agent_name} Pokemon Switches per 100 Episodes')
        plt.xlabel('Episode')
        plt.ylabel('Number of Switches')
        plt.grid(True, alpha=0.3)
        
        # 상대 포켓몬 쓰러뜨린 횟수 분포
        plt.subplot(4, 1, 3)
        x = np.arange(len(alive_enemies_distribution))
        width = 0.2  # 막대 너비
        
        # 각 구간별로 4개의 막대를 그립니다
        for i in range(4):
            values = [dist[i] for dist in alive_enemies_distribution]
            plt.bar(x + i*width, values, width, label=f'{i} Pokemon Left', alpha=0.7)
        
        plt.title(f'{agent_name} Distribution of Remaining Enemy Pokemon')
        plt.xlabel('Episode Range (x100)')
        plt.ylabel('Number of Episodes')
        plt.xticks(x + width*1.5, [f'{i*100}-{(i+1)*100-1}' for i in range(len(alive_enemies_distribution))])
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(save_path, f'{agent_name}_battle_statistics.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 배틀 통계를 JSON 파일로 저장
        battle_stats = {
            'super_effective_moves': super_effective_moves,
            'ineffective_moves': ineffective_moves,
            'switches': switches,
            'alive_enemies_distribution': alive_enemies_distribution
        }
        
        with open(os.path.join(save_path, f'{agent_name}_battle_stats.json'), 'w') as f:
            json.dump(battle_stats, f, indent=4)
    
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