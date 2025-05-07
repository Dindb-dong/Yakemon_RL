import os
import json
import numpy as np
from datetime import datetime

class TrainingLogger:
    """강화학습 훈련 과정의 로깅을 담당하는 클래스"""

    def __init__(self, log_dir='./pokemon_rl_logs'):
        """
        로깅 디렉토리 초기화 및 로그 파일 설정
        """
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # 실험 ID 생성 (타임스탬프 기반)
        self.experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 로그 파일 경로 설정
        self.log_file = os.path.join(log_dir, f"training_log_{self.experiment_id}.json")
        
        # 로그 데이터 초기화
        self.log_data = {
            'episodes': [],
            'steps': [],
            'rewards': [],
            'losses': [],
            'epsilons': [],
            'win_rates': [],
            'avg_turns': [],
            'avg_damage_dealt': [],
            'avg_damage_taken': [],
            'super_effective_rates': [],
            'critical_hit_rates': [],
            'switch_counts': [],
            'battle_completion_rates': []
        }

    def log_episode(self, episode, step, reward, loss=None, epsilon=None, 
                   win_rate=None, avg_turns=None, avg_damage_dealt=None, 
                   avg_damage_taken=None, super_effective_rate=None, 
                   critical_hit_rate=None, switch_count=None, 
                   battle_completion_rate=None):
        """
        에피소드별 훈련 데이터 로깅
        """
        # 기본 데이터 저장
        self.log_data['episodes'].append(episode)
        self.log_data['steps'].append(step)
        self.log_data['rewards'].append(reward)

        # 선택적 데이터 저장
        if loss is not None:
            self.log_data['losses'].append(loss)
        if epsilon is not None:
            self.log_data['epsilons'].append(epsilon)
        if win_rate is not None:
            self.log_data['win_rates'].append(win_rate)
        if avg_turns is not None:
            self.log_data['avg_turns'].append(avg_turns)
        if avg_damage_dealt is not None:
            self.log_data['avg_damage_dealt'].append(avg_damage_dealt)
        if avg_damage_taken is not None:
            self.log_data['avg_damage_taken'].append(avg_damage_taken)
        if super_effective_rate is not None:
            self.log_data['super_effective_rates'].append(super_effective_rate)
        if critical_hit_rate is not None:
            self.log_data['critical_hit_rates'].append(critical_hit_rate)
        if switch_count is not None:
            self.log_data['switch_counts'].append(switch_count)
        if battle_completion_rate is not None:
            self.log_data['battle_completion_rates'].append(battle_completion_rate)

        # 로그 파일 저장
        self._save_log()

    def log_evaluation(self, episode, evaluation_results):
        """
        평가 결과 로깅
        """
        self.log_episode(
            episode=episode,
            step=evaluation_results.get('step', 0),
            reward=evaluation_results.get('avg_reward', 0),
            win_rate=evaluation_results.get('win_rate', 0),
            avg_turns=evaluation_results.get('avg_turns', 0),
            avg_damage_dealt=evaluation_results.get('avg_damage_dealt', 0),
            avg_damage_taken=evaluation_results.get('avg_damage_taken', 0),
            super_effective_rate=evaluation_results.get('super_effective_rate', 0),
            critical_hit_rate=evaluation_results.get('critical_hit_rate', 0),
            switch_count=evaluation_results.get('switch_count', 0),
            battle_completion_rate=evaluation_results.get('battle_completion_rate', 0)
        )

    def _save_log(self):
        """
        로그 데이터를 JSON 파일로 저장
        """
        with open(self.log_file, 'w') as f:
            json.dump(self.log_data, f, indent=2)

    def get_statistics(self, window_size=100):
        """
        최근 window_size 에피소드의 통계 계산
        """
        stats = {}
        
        # 각 지표별로 최근 window_size개의 데이터에 대한 통계 계산
        for key in self.log_data:
            if len(self.log_data[key]) > 0:
                recent_data = self.log_data[key][-window_size:]
                stats[key] = {
                    'mean': np.mean(recent_data),
                    'std': np.std(recent_data),
                    'min': np.min(recent_data),
                    'max': np.max(recent_data),
                    'latest': recent_data[-1] if recent_data else None
                }
        
        return stats

    def print_progress(self, episode, step, stats):
        """
        현재 훈련 진행 상황 출력
        """
        print(f"\n[훈련 진행 상황] 에피소드 {episode:,} (스텝 {step:,})")
        print(f"  최근 {len(stats['rewards']['mean'])} 에피소드 평균:")
        print(f"    보상: {stats['rewards']['mean']:.2f} ± {stats['rewards']['std']:.2f}")
        print(f"    손실: {stats['losses']['mean']:.4f} ± {stats['losses']['std']:.4f}")
        print(f"    탐색률: {stats['epsilons']['latest']:.3f}")
        
        if 'win_rates' in stats:
            print(f"    승률: {stats['win_rates']['mean']:.1f}% ± {stats['win_rates']['std']:.1f}%")
        if 'avg_turns' in stats:
            print(f"    평균 턴 수: {stats['avg_turns']['mean']:.1f} ± {stats['avg_turns']['std']:.1f}")
        if 'super_effective_rates' in stats:
            print(f"    효과적 공격 비율: {stats['super_effective_rates']['mean']:.1f}% ± {stats['super_effective_rates']['std']:.1f}%")
        if 'critical_hit_rates' in stats:
            print(f"    급소 타격 비율: {stats['critical_hit_rates']['mean']:.1f}% ± {stats['critical_hit_rates']['std']:.1f}%")
        if 'switch_counts' in stats:
            print(f"    평균 교체 횟수: {stats['switch_counts']['mean']:.1f} ± {stats['switch_counts']['std']:.1f}")

    def save_checkpoint(self, agent, episode, step, is_best=False):
        """
        에이전트 상태 저장
        """
        checkpoint_dir = os.path.join(self.log_dir, 'checkpoints')
        os.makedirs(checkpoint_dir, exist_ok=True)

        # 일반 체크포인트 저장
        checkpoint_path = os.path.join(checkpoint_dir, f"checkpoint_ep{episode:06d}.h5")
        agent.save_model(checkpoint_path)

        # 최고 성능 모델인 경우 별도 저장
        if is_best:
            best_model_path = os.path.join(checkpoint_dir, "best_model.h5")
            agent.save_model(best_model_path)
            print(f"\n최고 성능 모델 저장: {best_model_path}")

        # 체크포인트 메타데이터 저장
        metadata = {
            'episode': episode,
            'step': step,
            'epsilon': agent.epsilon,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        metadata_path = os.path.join(checkpoint_dir, f"checkpoint_ep{episode:06d}_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2) 