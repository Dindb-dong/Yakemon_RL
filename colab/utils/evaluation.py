"""배틀 평가 유틸리티 모듈"""

import numpy as np
from collections import defaultdict
from ..rl.reward import BattleReward

class BattleEvaluator:
    """배틀 평가 클래스"""
    
    @staticmethod
    def evaluate_agent(agent, battle, num_episodes=100):
        """에이전트 성능 평가"""
        results = {
            'wins': 0,
            'losses': 0,
            'avg_turns': 0,
            'avg_reward': 0,
            'move_usage': defaultdict(int),
            'switch_usage': defaultdict(int)
        }
        
        for episode in range(num_episodes):
            battle.reset()
            episode_reward = 0
            turns = 0
            
            while not battle.is_battle_over():
                # 현재 상태와 유효한 행동 가져오기
                state = battle.get_state()
                valid_actions = battle.get_valid_actions()
                
                # 에이전트의 행동 선택
                action = agent.act(state, valid_actions)
                
                # 행동 실행
                if action < 4:  # 기술 사용
                    action_type = "move"
                    move_index = action
                    results['move_usage'][battle.player_team.active_pokemon.moves[move_index].name] += 1
                else:  # 포켓몬 교체
                    action_type = "switch"
                    switch_index = action - 4
                    valid_switches = battle.player_team.get_valid_switches()
                    if valid_switches:
                        switch_index = valid_switches[switch_index]
                        results['switch_usage'][battle.player_team.pokemons[switch_index].name] += 1
                
                # 행동 실행 및 보상 계산
                result = battle.player_action(action_type, action)
                reward = BattleReward.calculate_reward(battle, action_type, action, result)
                episode_reward += reward
                turns += 1
            
            # 에피소드 결과 기록
            winner = battle.get_winner()
            if winner == "player":
                results['wins'] += 1
            else:
                results['losses'] += 1
            
            results['avg_turns'] += turns
            results['avg_reward'] += episode_reward
        
        # 평균 계산
        results['avg_turns'] /= num_episodes
        results['avg_reward'] /= num_episodes
        
        # 승률 계산
        results['win_rate'] = results['wins'] / num_episodes
        
        return results

    @staticmethod
    def analyze_battle_log(battle_log):
        """배틀 로그 분석"""
        analysis = {
            'total_turns': len(battle_log),
            'move_usage': defaultdict(int),
            'switch_usage': defaultdict(int),
            'status_effects': defaultdict(int),
            'critical_hits': 0,
            'super_effective_moves': 0,
            'not_very_effective_moves': 0
        }
        
        for turn in battle_log:
            for action in turn:
                if action.get('actor') in ['player', 'opponent']:
                    result = action.get('result', {})
                    
                    # 기술 사용 분석
                    if 'message' in result and '의 ' in result['message']:
                        move_name = result['message'].split('의 ')[1].split('!')[0]
                        analysis['move_usage'][move_name] += 1
                    
                    # 효과 분석
                    if 'effects' in result:
                        for effect in result['effects']:
                            if '상태가 되었다' in effect:
                                status = effect.split('에게 ')[1].split(' 상태')[0]
                                analysis['status_effects'][status] += 1
                            elif '급소에 맞았다' in effect:
                                analysis['critical_hits'] += 1
                    
                    # 기술 효과 분석
                    if 'effectiveness' in result:
                        if result['effectiveness'] == '효과가 뛰어났다!':
                            analysis['super_effective_moves'] += 1
                        elif result['effectiveness'] == '효과가 별로인 듯하다...':
                            analysis['not_very_effective_moves'] += 1
        
        return analysis

    @staticmethod
    def print_evaluation_results(results):
        """평가 결과 출력"""
        print("\n=== 에이전트 평가 결과 ===")
        print(f"승률: {results['win_rate']:.2%}")
        print(f"평균 턴 수: {results['avg_turns']:.1f}")
        print(f"평균 보상: {results['avg_reward']:.2f}")
        
        print("\n=== 기술 사용 통계 ===")
        for move, count in sorted(results['move_usage'].items(), key=lambda x: x[1], reverse=True):
            print(f"{move}: {count}회")
        
        print("\n=== 포켓몬 교체 통계 ===")
        for pokemon, count in sorted(results['switch_usage'].items(), key=lambda x: x[1], reverse=True):
            print(f"{pokemon}: {count}회") 