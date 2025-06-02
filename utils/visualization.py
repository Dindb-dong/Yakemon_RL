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
        tuple: (super_effective_moves, ineffective_moves, switches, alive_enemies_distribution, 
               good_switches, bad_switches, good_attacks, bad_attacks, good_choices, bad_choices)
    """
    # 100판 단위로 통계를 저장할 리스트 초기화
    num_bins = (total_episodes + 99) // 100
    super_effective_moves = np.zeros(num_bins, dtype=np.float64)
    ineffective_moves = np.zeros(num_bins, dtype=np.float64)
    switches = np.zeros(num_bins, dtype=np.float64)
    good_switches = np.zeros(num_bins, dtype=np.float64)    # 좋은 교체 선택
    bad_switches = np.zeros(num_bins, dtype=np.float64)     # 나쁜 교체 선택
    good_attacks = np.zeros(num_bins, dtype=np.float64)     # 좋은 공격 선택
    bad_attacks = np.zeros(num_bins, dtype=np.float64)      # 나쁜 공격 선택
    good_choices = np.zeros(num_bins, dtype=np.float64)     # 기타 좋은 선택
    bad_choices = np.zeros(num_bins, dtype=np.float64)      # 기타 나쁜 선택
    
    # Alive Enemies 분포를 저장할 2차원 리스트 초기화
    # [구간][남은 포켓몬 수(0-3)] 형태로 저장
    alive_enemies_distribution = np.zeros((num_bins, 4), dtype=np.float64)
    
    current_episode = 0
    current_alive_enemies = None
    
    for line in log_lines:
        # 에피소드 시작 확인
        if "Episode" in line:
            match = re.search(r"Episode (\d+)", line)
            if match:
                current_episode = int(match.group(1))
                current_alive_enemies = None  # 에피소드 시작시 초기화
        
        bin_index = current_episode // 100
        if bin_index >= len(good_choices):
            continue
            
        # 좋은 교체 선택 확인
        if "Good switch:" in line:
            good_switches[bin_index] += 1
        
        # 나쁜 교체 선택 확인
        if "Bad switch:" in line:
            bad_switches[bin_index] += 1
        
        # 좋은 공격 선택 확인
        if "Good Attack:" in line:
            good_attacks[bin_index] += 1
        
        # 나쁜 공격 선택 확인
        if "Bad Attack:" in line:
            bad_attacks[bin_index] += 1
        
        # 기타 좋은 선택 확인
        if "Good choice:" in line and "Good switch:" not in line and "Good Attack:" not in line:
            good_choices[bin_index] += 1
        
        # 기타 나쁜 선택 확인
        if "Bad choice:" in line and "Bad switch:" not in line and "Bad Attack:" not in line:
            bad_choices[bin_index] += 1
        
        # 효과가 굉장한 기술 사용 확인
        if "효과가 굉장했다" in line and 'my' in line:
            super_effective_moves[bin_index] += 1
        
        # 효과가 없는 기술 사용 확인
        if "효과가 없었다" in line and 'my' in line:
            ineffective_moves[bin_index] += 1
        
        # 교체 확인
        if "내가 교체하려는 포켓몬" in line:
            switches[bin_index] += 1
        
        # 상대 포켓몬 쓰러뜨림 확인
        if "Alive Enemies" in line:
            match = re.search(r"Alive Enemies: (\d+)", line)
            if match:
                remaining = int(match.group(1))
                # 0-3 사이의 값으로 제한
                remaining = min(3, max(0, remaining))
                alive_enemies_distribution[bin_index][remaining] += 1
    
    return (super_effective_moves, ineffective_moves, switches, alive_enemies_distribution, 
            good_switches, bad_switches, good_attacks, bad_attacks, good_choices, bad_choices)

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
    
    # 무한값 필터링
    rewards_history = np.array(rewards_history)
    finite_mask = np.isfinite(rewards_history)
    filtered_rewards = rewards_history[finite_mask]
    
    # 1. 보상, 승리 횟수 및 손실 그래프
    plt.figure(figsize=(15, 12))
    
    # 보상 그래프
    plt.subplot(3, 1, 1)
    plt.plot(rewards_history, label='Average Reward', color='blue', alpha=0.6)
    
    # 이동 평균 추가 (100 에피소드)
    window_size = min(100, len(filtered_rewards))
    if window_size > 0:
        moving_avg = np.convolve(filtered_rewards, np.ones(window_size)/window_size, mode='valid')
        plt.plot(range(window_size-1, len(filtered_rewards)), moving_avg, 
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
    plt.hist(filtered_rewards, bins=50, alpha=0.7, color='blue')
    plt.title(f'{agent_name} Reward Distribution')
    plt.xlabel('Average Reward')
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    
    # 보상 누적 분포
    plt.subplot(1, 2, 2)
    sorted_rewards = np.sort(filtered_rewards)
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
        super_effective_moves, ineffective_moves, switches, alive_enemies_distribution, good_switches, bad_switches, good_attacks, bad_attacks, good_choices, bad_choices = analyze_battle_statistics(log_lines, len(rewards_history))
        
        plt.figure(figsize=(15, 30))  # 그래프 크기 증가
        
        # 효과가 굉장한 기술 사용 횟수
        plt.subplot(8, 1, 1)
        episodes = np.arange(0, len(rewards_history), 100)
        plt.bar(episodes, super_effective_moves, width=80, alpha=0.7, color='red', label='Super Effective')
        plt.bar(episodes, ineffective_moves, width=80, alpha=0.7, color='gray', label='Ineffective', bottom=super_effective_moves)
        plt.title(f'{agent_name} Move Effectiveness per 100 Episodes')
        plt.xlabel('Episode')
        plt.ylabel('Number of Moves')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 교체 횟수
        plt.subplot(8, 1, 2)
        plt.bar(episodes, switches, width=80, alpha=0.7, color='blue')
        plt.title(f'{agent_name} Pokemon Switches per 100 Episodes')
        plt.xlabel('Episode')
        plt.ylabel('Number of Switches')
        plt.grid(True, alpha=0.3)
        
        # 상대 포켓몬 쓰러뜨린 횟수 분포
        plt.subplot(8, 1, 3)
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
        
        # 좋은/나쁜 교체 선택
        plt.subplot(8, 1, 4)
        plt.bar(episodes, good_switches, width=80, alpha=0.7, color='green', label='Good Switches')
        plt.bar(episodes, bad_switches, width=80, alpha=0.7, color='red', label='Bad Switches', bottom=good_switches)
        plt.title(f'{agent_name} Switch Quality per 100 Episodes')
        plt.xlabel('Episode')
        plt.ylabel('Number of Switches')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 좋은/나쁜 공격 선택
        plt.subplot(8, 1, 5)
        plt.bar(episodes, good_attacks, width=80, alpha=0.7, color='green', label='Good Attacks')
        plt.bar(episodes, bad_attacks, width=80, alpha=0.7, color='red', label='Bad Attacks', bottom=good_attacks)
        plt.title(f'{agent_name} Attack Quality per 100 Episodes')
        plt.xlabel('Episode')
        plt.ylabel('Number of Attacks')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 기타 좋은/나쁜 선택
        plt.subplot(8, 1, 6)
        plt.bar(episodes, good_choices, width=80, alpha=0.7, color='green', label='Good Choices')
        plt.bar(episodes, bad_choices, width=80, alpha=0.7, color='red', label='Bad Choices', bottom=good_choices)
        plt.title(f'{agent_name} Other Choice Quality per 100 Episodes')
        plt.xlabel('Episode')
        plt.ylabel('Number of Choices')
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        # 교체 선택 품질 비율
        plt.subplot(8, 1, 7)
        total_switches = np.array(good_switches) + np.array(bad_switches)
        good_switch_ratio = np.divide(good_switches, total_switches, out=np.zeros_like(good_switches), where=total_switches!=0)
        plt.plot(episodes, good_switch_ratio, color='blue', marker='o', label='Good Switch Ratio')
        plt.title(f'{agent_name} Good Switch Ratio per 100 Episodes')
        plt.xlabel('Episode')
        plt.ylabel('Ratio of Good Switches')
        plt.ylim(0, 1)
        plt.grid(True, alpha=0.3)
        
        # 공격 선택 품질 비율
        plt.subplot(8, 1, 8)
        total_attacks = np.array(good_attacks) + np.array(bad_attacks)
        good_attack_ratio = np.divide(good_attacks, total_attacks, out=np.zeros_like(good_attacks), where=total_attacks!=0)
        plt.plot(episodes, good_attack_ratio, color='blue', marker='o', label='Good Attack Ratio')
        plt.title(f'{agent_name} Good Attack Ratio per 100 Episodes')
        plt.xlabel('Episode')
        plt.ylabel('Ratio of Good Attacks')
        plt.ylim(0, 1)
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(save_path, f'{agent_name}_battle_statistics.png'), dpi=300, bbox_inches='tight')
        plt.close()
        
        # 배틀 통계를 JSON 파일로 저장
        battle_stats = {
            'super_effective_moves': super_effective_moves.tolist(),
            'ineffective_moves': ineffective_moves.tolist(),
            'switches': switches.tolist(),
            'alive_enemies_distribution': alive_enemies_distribution.tolist(),
            'good_switches': good_switches.tolist(),
            'bad_switches': bad_switches.tolist(),
            'good_attacks': good_attacks.tolist(),
            'bad_attacks': bad_attacks.tolist(),
            'good_choices': good_choices.tolist(),
            'bad_choices': bad_choices.tolist()
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