# env/battle_env.py
# 이거 엉망 코드임! 완전히 새로 짜야함
import random
import numpy as np
import gym
from gym import spaces
from typing import Dict, List, Tuple, Optional, Union
import os
import sys

# 현재 디렉토리의 상위 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 하이퍼파라미터 정의
HYPERPARAMS = {
    "state_dim": 140,  # 상태 공간의 차원
    "action_dim": 8,   # 행동 공간의 차원 (4개 기술 + 4개 교체)
}

# 절대 경로 import
from p_data.mock_pokemon import create_mock_pokemon_list
from RL.get_state_vector import get_state
from RL.base_ai_choose_action import base_ai_choose_action
from RL.agent_choose_action import agent_choose_action
from RL.reward_calculator import calculate_reward
from utils.battle_logics.battle_sequence import battle_sequence, BattleAction
from context.battle_store import battle_store_instance
from context.battle_environment import PublicBattleEnvironment, IndividualBattleEnvironment
from context.duration_store import duration_store
from context.form_check_wrapper import with_form_check
from p_models.battle_pokemon import BattlePokemon
from p_models.move_info import MoveInfo
from p_models.ability_info import AbilityInfo
from p_models.types import WeatherType, FieldType
from p_models.rank_state import RankManager
from p_models.status import StatusManager

class YakemonEnv(gym.Env):
    """
    Yakemon 배틀 환경을 위한 Gym 인터페이스
    """
    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(YakemonEnv, self).__init__()
        self.pokemon_list = create_mock_pokemon_list()
        
        # 상태 공간 정의 (140차원)
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(140,),
            dtype=np.float32
        )
        
        # 행동 공간 정의 (8개 행동: 4개 기술 + 4개 교체)
        self.action_space = spaces.Discrete(8)
        
        # 배틀 스토어와 환경 초기화
        self.battle_store = battle_store_instance
        self.duration_store = duration_store
        self.public_env = PublicBattleEnvironment()
        self.my_env = IndividualBattleEnvironment()
        self.enemy_env = IndividualBattleEnvironment()
        
        # 추가 속성 초기화
        self.my_team = []
        self.enemy_team = []
        self.turn = 1
        self.done = False
        
        self.reset()

    def reset(self, my_team=None, enemy_team=None):
        """
        환경 초기화
        """
        # 팀이 주어지지 않은 경우 랜덤 팀 생성
        if my_team is None:
            my_team = create_mock_pokemon_list()[:6]
        if enemy_team is None:
            enemy_team = create_mock_pokemon_list()[6:12]
        
        # 배틀 스토어 초기화
        self.battle_store.reset_all()
        self.battle_store.set_my_team(my_team)
        self.battle_store.set_enemy_team(enemy_team)
        
        # 내부 팀 변수 업데이트
        self.my_team = my_team
        self.enemy_team = enemy_team
        
        # 배틀 환경 설정
        weather_types = ['sunny', 'rainy', 'sandstorm', 'hail', 'fog', 'clear']
        field_types = ['electric', 'psychic', 'grassy', 'misty', 'normal']
        
        public_env = PublicBattleEnvironment(
            weather=random.choice(weather_types),
            field=random.choice(field_types),
            aura=random.sample(['fairy', 'dark', 'dragon'], k=random.randint(0, 3)),
            disaster=random.sample(['earthquake', 'tsunami', 'volcano'], k=random.randint(0, 2)),
            room=random.choice(['trick', 'magic', 'wonder', None])
        )
        
        my_env = IndividualBattleEnvironment(
            trap=random.sample(['spikes', 'stealth_rock', 'toxic_spikes'], k=random.randint(0, 3)),
            screen=random.choice(['reflect', 'light_screen', 'aurora_veil', 'safeguard', 'mist', None]),
            substitute=random.choice([True, False]),
            disguise=random.choice([True, False])
        )
        
        enemy_env = IndividualBattleEnvironment(
            trap=random.sample(['spikes', 'stealth_rock', 'toxic_spikes'], k=random.randint(0, 3)),
            screen=random.choice(['reflect', 'light_screen', 'aurora_veil', 'safeguard', 'mist', None]),
            substitute=random.choice([True, False]),
            disguise=random.choice([True, False])
        )
        
        # 배틀 스토어에 환경 설정
        self.battle_store.set_public_env(public_env.__dict__)
        self.battle_store.set_my_env(my_env.__dict__)
        self.battle_store.set_enemy_env(enemy_env.__dict__)
        
        # 내부 환경 변수 업데이트
        self.public_env = public_env
        self.my_env = my_env
        self.enemy_env = enemy_env
        
        # 턴 초기화
        self.turn = 1
        self.done = False
        
        # 초기 상태 반환
        return self._get_state()

    def _get_state(self):
        """현재 상태 벡터 반환"""
        return get_state(
            my_team=self.my_team,
            enemy_team=self.enemy_team,
            active_my=self.battle_store.get_active_index("my"),
            active_enemy=self.battle_store.get_active_index("enemy"),
            public_env=self.public_env.__dict__,
            my_env=self.my_env.__dict__,
            enemy_env=self.enemy_env.__dict__,
            turn=self.turn,
            my_effects=self.duration_store.my_effects,
            enemy_effects=self.duration_store.enemy_effects
        )

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        환경에서 한 스텝 진행
        
        Args:
            action: 수행할 행동 (0-7)
                0-3: 기술 사용
                4-7: 포켓몬 교체
        
        Returns:
            observation: 다음 상태
            reward: 보상
            done: 에피소드 종료 여부
            info: 추가 정보
        """
        # 현재 상태 저장
        current_state = self._get_state()
        
        # 행동 실행
        if action < 4:  # 기술 사용
            move = self.my_team[self.battle_store.get_active_index("my")]['base']['moves'][action]
            battle_action = {"type": "move", "index": action, "move": move}
        else:  # 포켓몬 교체
            switch_index = action - 4
            battle_action = {"type": "switch", "index": switch_index}
        
        # 배틀 시퀀스 실행
        battle_sequence(
            my_action=battle_action,
            enemy_action=base_ai_choose_action(
                side="enemy",
                my_team=self.enemy_team,
                enemy_team=self.my_team,
                active_my=self.battle_store.get_active_index("enemy"),
                active_enemy=self.battle_store.get_active_index("my"),
                public_env=self.public_env.__dict__,
                enemy_env=self.my_env.__dict__,
                my_env=self.enemy_env.__dict__,
                add_log=self.battle_store.add_log
            )
        )
        
        # 다음 상태 가져오기
        next_state = self._get_state()
        
        # 보상 계산
        reward = calculate_reward(
            my_team=self.my_team,
            enemy_team=self.enemy_team,
            active_my=self.battle_store.get_active_index("my"),
            active_enemy=self.battle_store.get_active_index("enemy"),
            public_env=self.public_env.__dict__,
            my_env=self.my_env.__dict__,
            enemy_env=self.enemy_env.__dict__,
            turn=self.turn,
            my_effects=self.duration_store.my_effects,
            enemy_effects=self.duration_store.enemy_effects,
            action=action,
            done=self.done,
            battle_store=self.battle_store,
            duration_store=self.duration_store
        )
        
        # 턴 증가
        self.turn += 1
        
        # 게임 종료 체크
        self.done = self.check_game_end()
        
        # 추가 정보
        info = {
            'turn': self.turn,
            'my_hp': self.my_team[self.battle_store.get_active_index("my")]['currentHp'],
            'enemy_hp': self.enemy_team[self.battle_store.get_active_index("enemy")]['currentHp'],
            'public_env': self.public_env.__dict__,
            'my_env': self.my_env.__dict__,
            'enemy_env': self.enemy_env.__dict__
        }
        
        return next_state, reward, self.done, info

    def check_game_end(self) -> bool:
        """게임 종료 조건 체크"""
        # 내 팀의 모든 포켓몬이 쓰러졌는지 확인
        my_all_fainted = all(p['currentHp'] <= 0 for p in self.my_team)
        
        # 상대 팀의 모든 포켓몬이 쓰러졌는지 확인
        enemy_all_fainted = all(p['currentHp'] <= 0 for p in self.enemy_team)
        
        return my_all_fainted or enemy_all_fainted

    def render(self, mode='human'):
        """환경의 현재 상태를 시각화"""
        if mode == 'human':
            print(f"\nTurn: {self.turn}")
            print(f"My Pokemon: {self.my_team[self.battle_store.get_active_index('my')].name}")
            print(f"HP: {self.my_team[self.battle_store.get_active_index('my')].hp:.1f}")
            print(f"Enemy Pokemon: {self.enemy_team[self.battle_store.get_active_index('enemy')].name}")
            print(f"HP: {self.enemy_team[self.battle_store.get_active_index('enemy')].hp:.1f}")
            print(f"Public Environment: {self.public_env.get_state()}")
            print(f"My Environment: {self.my_env.get_state()}")
            print(f"Enemy Environment: {self.enemy_env.get_state()}")
            print(f"Done: {self.done}\n")