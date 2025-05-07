import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import json
from datetime import datetime

# 평가 결과 저장 디렉토리
EVAL_DIR = './pokemon_rl_evaluation'
os.makedirs(EVAL_DIR, exist_ok=True)

class ModelEvaluator:
    """강화학습 모델 성능 평가 및 동적 주기의 시각화"""

    def __init__(self):
        """
        에피소드 수에 따른 동적 평가 주기 초기화:
        - 첫 100 에피소드: 10 에피소드마다
        - 101-1000 에피소드: 100 에피소드마다
        - 1001+ 에피소드: 1000 에피소드마다
        """
        # 교체 수를 포함한 평가 결과 저장
        self.results = {
            'episodes': [],
            'steps': [],
            'win_rate': [],
            'avg_reward': [],
            'avg_turns': [],
            'avg_damage_dealt': [],
            'avg_damage_taken': [],
            'super_effective_rate': [],
            'critical_hit_rate': [],
            'avg_hp_remaining': [],
            'battle_completion_rate': [],
            'selfplay_opponent_version': [],
            'selfplay_win_rate': [],
            'ai_opponent_win_rate': [],  # 기존 AI 승률 추가
            'switch_count': []  # 교체 횟수 추적
        }

        # 실험 ID 생성 (타임스탬프 기반)
        self.experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.result_path = os.path.join(EVAL_DIR, f"eval_results_{self.experiment_id}.json")

        # 마지막 평가 에피소드 수
        self.last_eval_episode = 0

        # 각 평가마다 평가할 에피소드 수
        self.eval_episodes = 100  # 기본값 100으로 변경

        # 최고 승률 기록 및 시각화 주기 관리
        self.best_win_rate = 0.0
        self.best_model_episode = 0   # 최고 성능 모델의 에피소드
        self.visualization_count = 0  # 시각화 수 제한을 위한 카운터

    def should_evaluate(self, episode_count):
        """
        동적 주기에 따라 평가 여부 결정
        특정 주기마다 또는 100 에피소드마다 평가 실행
        """
        # 100 에피소드마다 무조건 평가 수행 (요구사항)
        if episode_count % 1000 == 0 and episode_count > 0:
            self.eval_episodes = 10  # 100 에피소드마다 100판 평가
            self.last_eval_episode = episode_count
            return True

        # 초기 단계에서는 더 자주 평가
        if episode_count <= 100 and episode_count % 1000 == 0:
            self.eval_episodes = 0
            self.last_eval_episode = episode_count
            return True

        return False

    def evaluate(self, agent, env_creator, step_count, episode_count, selfplay_info=None, save_best=True):
        """종합적인 지표 평가"""
        print(f"\n[평가 시작] 에피소드 {episode_count:,} (스텝 {step_count:,}) - {self.eval_episodes} 테스트 배틀")

        # 통계 초기화
        wins = 0
        total_reward = 0
        total_turns = 0
        total_damage_dealt = 0
        total_damage_taken = 0
        total_effective_moves = 0
        total_moves_used = 0
        total_critical_hits = 0
        total_hp_remaining_pct = 0
        completed_battles = 0
        total_switches = 0  # 교체 횟수

        for episode in range(self.eval_episodes):
            # 환경 생성 및 초기화
            env = env_creator()
            state = env.reset()
            done = False
            episode_reward = 0

            # 에피소드 통계
            episode_damage_dealt = 0
            episode_damage_taken = 0
            episode_effective_moves = 0
            episode_moves_used = 0
            episode_critical_hits = 0
            episode_switches = 0  # 에피소드별 교체 횟수

            # 탐색률 백업 (평가 중에는 탐색 없음)
            epsilon_backup = agent.epsilon
            agent.epsilon = 0

            while not done:
                # 행동 선택 및 실행
                valid_actions = env.get_valid_actions()
                action = agent.choose_action(state, valid_actions)
                next_state, reward, done, info = env.step(action)

                # 턴 정보 수집
                if action < 4:  # 기술 사용 행동
                    episode_moves_used += 1

                    # 플레이어 결과 분석
                    if 'player_result' in info:
                        player_result = info['player_result']
                        if player_result and player_result.get('success', False):
                            # 데미지 계산
                            damage = player_result.get('damage', 0)
                            if damage > 0:
                                episode_damage_dealt += damage

                            # 효과 판정 - 다양한 문자열 패턴 지원
                            effectiveness = player_result.get('effectiveness', '')
                            if (effectiveness and
                                ('super effective' in effectiveness.lower() or
                                'very effective' in effectiveness.lower() or
                                '효과가 뛰어났다' in effectiveness)):
                                episode_effective_moves += 1

                            # 급소 확인
                            if 'effects' in player_result:
                                for effect in player_result['effects']:
                                    if any(crit_text in effect.lower() for crit_text in
                                        ["critical hit", "critical", "급소에 맞았다"]):
                                        episode_critical_hits += 1
                                        break

                    # 상대방 결과 분석
                    if 'opponent_result' in info:
                        opponent_result = info['opponent_result']
                        if opponent_result and opponent_result.get('success', False):
                            damage = opponent_result.get('damage', 0)
                            if damage > 0:
                                episode_damage_taken += damage

                else:  # 교체 행동 (action >= 4)
                    episode_switches += 1  # 교체 횟수 증가

                state = next_state
                episode_reward += reward

                # 너무 긴 에피소드 방지
                if env.battle.turn >= 50:
                    break

            # 탐색률 복원
            agent.epsilon = epsilon_backup

            # 에피소드 결과 수집
            total_reward += episode_reward
            total_turns += env.battle.turn
            total_switches += episode_switches  # 교체 횟수 추가

            # 승리 확인
            if info.get('battle_over', False) and info.get('winner', None) == 'player':
                wins += 1

            # 배틀 완료 확인 (기권이 아님)
            if info.get('battle_over', False):
                completed_battles += 1

            # 데미지 관련 통계
            total_damage_dealt += episode_damage_dealt
            total_damage_taken += episode_damage_taken

            # 효과적인 공격 비율
            total_effective_moves += episode_effective_moves
            total_moves_used += max(1, episode_moves_used)  # 0으로 나누기 방지

            # 급소 공격 비율
            total_critical_hits += episode_critical_hits

            # 잔여 HP 비율 계산
            if hasattr(env.battle, 'player_team') and env.battle.player_team:
                remaining_hp = sum(p.current_hp for p in env.battle.player_team.pokemons if hasattr(p, 'current_hp'))
                max_hp = sum(p.stats.get('hp', 0) for p in env.battle.player_team.pokemons if hasattr(p, 'stats'))
                hp_remaining_pct = remaining_hp / max_hp if max_hp > 0 else 0
                total_hp_remaining_pct += hp_remaining_pct

        # 평균 지표 계산
        avg_reward = total_reward / (self.eval_episodes+1)
        win_rate = (wins / (self.eval_episodes+1)) * 100
        avg_turns = total_turns / (self.eval_episodes+1)
        avg_damage_dealt = total_damage_dealt / (self.eval_episodes+1)
        avg_damage_taken = total_damage_taken / (self.eval_episodes+1)
        super_effective_rate = (total_effective_moves / total_moves_used) * 100 if total_moves_used > 0 else 0
        critical_hit_rate = (total_critical_hits / total_moves_used) * 100 if total_moves_used > 0 else 0
        avg_hp_remaining = (total_hp_remaining_pct / (self.eval_episodes+1)) * 100
        battle_completion_rate = (completed_battles / (self.eval_episodes+1)) * 100
        avg_switches = total_switches / (self.eval_episodes+1)  # 평균 교체 횟수

        # 최고 승률 모델 확인 및 저장
        if save_best and win_rate > self.best_win_rate:
            self.best_win_rate = win_rate
            self.best_model_episode = episode_count
            # 최고 성능 모델 저장 요청 (외부에서 처리)
            print(f"\n새로운 최고 승률 모델! 승률: {win_rate:.1f}%, 에피소드: {episode_count}")
            is_best = True
        else:
            is_best = False

        # 결과 저장
        self.results['episodes'].append(episode_count)
        self.results['steps'].append(step_count)
        self.results['win_rate'].append(win_rate)
        self.results['avg_reward'].append(avg_reward)
        self.results['avg_turns'].append(avg_turns)
        self.results['avg_damage_dealt'].append(avg_damage_dealt)
        self.results['avg_damage_taken'].append(avg_damage_taken)
        self.results['super_effective_rate'].append(super_effective_rate)
        self.results['critical_hit_rate'].append(critical_hit_rate)
        self.results['avg_hp_remaining'].append(avg_hp_remaining)
        self.results['battle_completion_rate'].append(battle_completion_rate)
        self.results['switch_count'].append(avg_switches)  # 교체 횟수 저장

        # 자가 대전 정보 저장 (제공된 경우)
        if selfplay_info:
            self.results['selfplay_opponent_version'].append(selfplay_info.get('opponent_version', -1))
            self.results['selfplay_win_rate'].append(selfplay_info.get('win_rate', 0.0))
            self.results['ai_opponent_win_rate'].append(selfplay_info.get('ai_win_rate', 0.0))  # AI 상대 승률 추가
        else:
            # 자가 대전이 아닌 경우 -1 및 0으로 채움
            self.results['selfplay_opponent_version'].append(-1)
            self.results['selfplay_win_rate'].append(0.0)
            self.results['ai_opponent_win_rate'].append(0.0)

        # 결과 출력 (명확하고 상세하게)
        print(f"\n[평가 결과] 에피소드 {episode_count:,} (스텝 {step_count:,}):")
        print(f"  승률: {win_rate:.1f}% ({wins}/{self.eval_episodes})")
        print(f"  평균 보상: {avg_reward:.2f}")
        print(f"  평균 턴 수: {avg_turns:.1f}")
        print(f"  공격 효율: {avg_damage_dealt:.1f} 가한 데미지 vs {avg_damage_taken:.1f} 받은 데미지")
        print(f"  타입 상성 활용: {super_effective_rate:.1f}% 효과적인 공격 비율")
        print(f"  급소 타격: {critical_hit_rate:.1f}% (총 {total_critical_hits}회)")
        print(f"  평균 교체 횟수: {avg_switches:.1f} (총 {total_switches}회)")  # 교체 횟수 강조
        print(f"  평균 잔여 HP: {avg_hp_remaining:.1f}%")
        print(f"  배틀 완료율: {battle_completion_rate:.1f}%")

        # 자가 대전 정보 출력 (제공된 경우)
        if selfplay_info:
            print(f"\n  자가 대전 평가:")
            print(f"    상대방 버전: {selfplay_info.get('opponent_version', -1)}")
            print(f"    자가 대전 승률: {selfplay_info.get('win_rate', 0.0):.1f}%")
            print(f"    기존 AI 상대 승률: {selfplay_info.get('ai_win_rate', 0.0):.1f}%")  # AI 상대 승률 표시

        # 결과 파일 저장
        self._save_results()

        # 시각화 주기 관리 - 에피소드 초기와 100의 배수일 때만 저장
        should_visualize = (episode_count <= 200 or episode_count % 100 == 0)

        if should_visualize:
            self.visualization_count += 1
            # 평가할 때마다 시각화 저장
            self.visualize(episode_count, step_count, save=True)

            # 초기 학습 중이거나 중요 마일스톤에서는 화면에 시각화 표시
            if episode_count <= 200 or episode_count % 500 == 0:
                self.visualize(episode_count, step_count, save=False)

        # 반환값: 최고 모델 여부, 승률, 평균 보상, 평균 턴 수
        return is_best, win_rate, avg_reward, avg_turns

    def _save_results(self):
        """결과를 JSON 파일로 저장"""
        with open(self.result_path, 'w') as f:
            json.dump(self.results, f, indent=2)

    def visualize(self, episode_count, step_count=None, save=False):
        """평가 결과 시각화 - 더 명확한 표현과 중요 지표 강조"""
        if not self.results['episodes']:
            print("시각화할 데이터가 없습니다.")
            return

        # Seaborn 스타일 설정 - 더 현대적인 스타일 적용
        sns.set(style="whitegrid")
        plt.rcParams['axes.titleweight'] = 'bold'
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['xtick.labelsize'] = 10
        plt.rcParams['ytick.labelsize'] = 10

        # 10개 그래프가 있는 그림 생성 (2x5 레이아웃)
        plt.figure(figsize=(20, 16))

        # 모든 플롯에 사용할 x축 값
        x_values = self.results['episodes']

        # 1. 시간 경과에 따른 승률
        plt.subplot(2, 5, 1)
        plt.plot(x_values, self.results['win_rate'], 'b-', linewidth=2)
        plt.title('Win Rate Change', fontsize=14, fontweight='bold')
        plt.xlabel('Episode', fontsize=12)
        plt.ylabel('Win Rate (%)', fontsize=12)
        plt.grid(True, alpha=0.3)

        # 2. 시간 경과에 따른 평균 보상
        plt.subplot(2, 5, 2)
        plt.plot(x_values, self.results['avg_reward'], 'g-', linewidth=2)
        plt.title('Average Reward Change', fontsize=14, fontweight='bold')
        plt.xlabel('Episode', fontsize=12)
        plt.ylabel('Average Reward', fontsize=12)
        plt.grid(True, alpha=0.3)

        # 3. 배틀당 평균 턴 수
        plt.subplot(2, 5, 3)
        plt.plot(x_values, self.results['avg_turns'], 'r-', linewidth=2)
        plt.title('Average Turn per Battle', fontsize=14, fontweight='bold')
        plt.xlabel('Episode', fontsize=12)
        plt.ylabel('Turns', fontsize=12)
        plt.grid(True, alpha=0.3)

        # 4. 데미지 지표
        plt.subplot(2, 5, 4)
        plt.plot(x_values, self.results['avg_damage_dealt'], 'c-', label='Applied Damage', linewidth=2)
        plt.plot(x_values, self.results['avg_damage_taken'], 'm-', label='Taken Damage', linewidth=2)
        plt.title('Average Damage per Battle', fontsize=14, fontweight='bold')
        plt.xlabel('Epsiode', fontsize=12)
        plt.ylabel('Damage', fontsize=12)
        plt.legend(fontsize=10)
        plt.grid(True, alpha=0.3)

        # 5. 이동 효과 및 급소 타격 (강조 표시)
        plt.subplot(2, 5, 5)
        plt.plot(x_values, self.results['super_effective_rate'], 'orange', label='Super Effective', linewidth=3)
        plt.plot(x_values, self.results['critical_hit_rate'], 'red', label='Critical Hit', linewidth=3)

        # 채우기 추가하여 더 눈에 띄게 표시
        plt.fill_between(x_values, self.results['super_effective_rate'], alpha=0.2, color='orange')
        plt.fill_between(x_values, self.results['critical_hit_rate'], alpha=0.2, color='red')

        plt.title('Type Learning', fontsize=14, fontweight='bold')
        plt.xlabel('Episode', fontsize=12)
        plt.ylabel('Ratio (%)', fontsize=12)
        plt.legend(fontsize=10, loc='upper left')
        plt.grid(True, alpha=0.3)

        # 최근 값 표시
        if len(self.results['super_effective_rate']) > 0:
            latest_se = self.results['super_effective_rate'][-1]
            latest_crit = self.results['critical_hit_rate'][-1]

            plt.annotate(f"{latest_se:.1f}%",
                        xy=(x_values[-1], latest_se),
                        xytext=(10, 0), textcoords='offset points',
                        ha='left', va='center', fontsize=10, color='darkorange')

            plt.annotate(f"{latest_crit:.1f}%",
                        xy=(x_values[-1], latest_crit),
                        xytext=(10, 0), textcoords='offset points',
                        ha='left', va='center', fontsize=10, color='darkred')

        # 6. 잔여 HP 비율
        plt.subplot(2, 5, 6)
        plt.plot(x_values, self.results['avg_hp_remaining'], 'g-', linewidth=2)
        plt.title('Average HP Left', fontsize=14, fontweight='bold')
        plt.xlabel('Episode', fontsize=12)
        plt.ylabel('HP Ratio (%)', fontsize=12)
        plt.grid(True, alpha=0.3)

        # 7. 배틀당 평균 교체 횟수 (강조 표시)
        plt.subplot(2, 5, 7)
        plt.plot(x_values, self.results['switch_count'], 'purple', linewidth=3)
        # 교체 횟수가 없는 경우와 있는 경우를 구분하여 배경색 지정
        plt.fill_between(x_values, self.results['switch_count'], alpha=0.3, color='purple')
        plt.title('Learnt Switch Strategy', fontsize=14, fontweight='bold')
        plt.xlabel('Episode', fontsize=12)
        plt.ylabel('Average Switch per Battle', fontsize=12)
        plt.grid(True, alpha=0.3)

        # 최근 값 표시
        if len(self.results['switch_count']) > 0:
            latest_val = self.results['switch_count'][-1]
            plt.annotate(f"{latest_val:.1f}",
                        xy=(x_values[-1], latest_val),
                        xytext=(10, 0), textcoords='offset points',
                        ha='left', va='center', fontsize=12, fontweight='bold',
                        color='purple')

        # 8. 데미지 효율 vs 승률
        plt.subplot(2, 5, 8)
        damage_efficiency = []
        for dealt, taken in zip(self.results['avg_damage_dealt'], self.results['avg_damage_taken']):
            if taken > 0:
                damage_efficiency.append(dealt / taken)
            else:
                damage_efficiency.append(dealt if dealt > 0 else 1.0)  # 받은 데미지가 0일 때

        scatter = plt.scatter(damage_efficiency, self.results['win_rate'],
                  c=x_values, cmap='viridis', s=50)
        plt.colorbar(scatter, label='Episode')
        plt.title('Damage Efficiency Vs Win Rate', fontsize=14, fontweight='bold')
        plt.xlabel('Damage Efficiency', fontsize=12)
        plt.ylabel('Win Rate (%)', fontsize=12)
        plt.grid(True, alpha=0.3)

        # 9. 자가 대전 및 AI 상대 승률 비교 (수정)
        plt.subplot(2, 5, 9)

        # 자가 대전이 시작된 데이터 필터링
        selfplay_indices = [i for i, v in enumerate(self.results['selfplay_opponent_version']) if v >= 0]

        if selfplay_indices:
            selfplay_episodes = [self.results['episodes'][i] for i in selfplay_indices]
            selfplay_win_rates = [self.results['selfplay_win_rate'][i] for i in selfplay_indices]
            ai_win_rates = [self.results['ai_opponent_win_rate'][i] for i in selfplay_indices]
            selfplay_versions = [self.results['selfplay_opponent_version'][i] for i in selfplay_indices]

            # 버전별 색상
            unique_versions = sorted(set(selfplay_versions))
            colors = plt.cm.tab10(np.linspace(0, 1, len(unique_versions)))

            # 버전별 자가 대전 승률 그래프
            for version, color in zip(unique_versions, colors):
                version_indices = [i for i, v in enumerate(selfplay_versions) if v == version]
                if version_indices:
                    version_episodes = [selfplay_episodes[i] for i in version_indices]
                    version_win_rates = [selfplay_win_rates[i] for i in version_indices]
                    plt.plot(version_episodes, version_win_rates,
                            marker='o', label=f'Self Play Opponent v{version}',
                            color=color, linewidth=2)

            # AI 상대 승률 추가 (점선으로 구분)
            plt.plot(selfplay_episodes, ai_win_rates,
                  marker='s', label='Baseline',
                  color='black', linestyle='--', linewidth=2)

            plt.axhline(y=60, color='r', linestyle='--', label='Update Threshold (60%)')
            plt.legend(fontsize=9, loc='upper left')
            plt.title('Self Play, Baseline Win Rate Comparison', fontsize=14, fontweight='bold')
            plt.xlabel('Episode', fontsize=12)
            plt.ylabel('Win Rate (%)', fontsize=12)
        else:
            plt.text(0.5, 0.5, 'No Self Play Data',
                    horizontalalignment='center', verticalalignment='center',
                    transform=plt.gca().transAxes, fontsize=14)
        plt.grid(True, alpha=0.3)

        # 10. 배틀 완료율
        plt.subplot(2, 5, 10)
        plt.plot(x_values, self.results['battle_completion_rate'], 'b-', linewidth=2)
        plt.title('Battle Finish Rate', fontsize=14, fontweight='bold')
        plt.xlabel('Episode', fontsize=12)
        plt.ylabel('Finish Rate (%)', fontsize=12)
        plt.grid(True, alpha=0.3)

        # 레이아웃 조정
        plt.tight_layout()

        # 저장 또는 표시
        if save:
            save_path = os.path.join(EVAL_DIR, f"eval_plot_{self.experiment_id}_ep{episode_count:06d}.png")
            plt.savefig(save_path, dpi=150, bbox_inches='tight')

            # 최고 승률 모델의 시각화는 특별히 복사본 저장
            if episode_count == self.best_model_episode:
                best_save_path = os.path.join(EVAL_DIR, f"best_model_plot_{self.experiment_id}.png")
                plt.savefig(best_save_path, dpi=150, bbox_inches='tight')
                print(f"최고 성능 모델 플롯 저장: {best_save_path}")
            else:
                print(f"플롯 저장: {save_path}")
        else:
            plt.show()

        plt.close() 