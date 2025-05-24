# env/battle_env.py
import asyncio
import random
import numpy as np
import gym
from gym import spaces
from typing import Dict, List, Tuple, Optional, Union
import os
import sys

from p_models.battle_pokemon import BattlePokemon
from utils.battle_logics.create_battle_pokemon import create_battle_pokemon

# 현재 디렉토리의 상위 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 하이퍼파라미터 정의
HYPERPARAMS = {
    "state_dim": 1165,  # 상태 공간의 차원
    "action_dim": 6,   # 행동 공간의 차원 (4개 기술 + 2개 교체)
}

# 절대 경로 import
from p_data.mock_pokemon import create_mock_pokemon_list
from RL.get_state_vector import get_state
from RL.base_ai_choose_action import base_ai_choose_action
from RL.reward_calculator import calculate_reward
from utils.battle_logics.battle_sequence import battle_sequence, BattleAction, remove_fainted_pokemon
from context.battle_environment import PublicBattleEnvironment, IndividualBattleEnvironment
from context.battle_store import store
from context.duration_store import duration_store
# from context.form_check_wrapper import with_form_check
# from p_models.battle_pokemon import BattlePokemon
# from p_models.move_info import MoveInfo
# from p_models.ability_info import AbilityInfo
# from p_models.types import WeatherType, FieldType
# from p_models.rank_state import RankManager
# from p_models.status import StatusManager

def random_enemy_action(enemy_team: List[BattlePokemon], active_enemy: int):
        current_pokemon = enemy_team[active_enemy]
        valid_actions = [
            i for i in range(6)
            if (i < 4 and current_pokemon.pp.get(current_pokemon.base.moves[i].name, 0) > 0)
            or (i >= 4 and i - 4 != active_enemy and enemy_team[i - 4].current_hp > 0)
        ]
        if valid_actions:
            chosen = random.choice(valid_actions)
            if chosen < 4:
                return current_pokemon.base.moves[chosen]
            else:
                return {"type": "switch", "index": chosen - 4}
        else:
            return current_pokemon.base.moves[0]

class YakemonEnv(gym.Env):
    """
    Yakemon 배틀 환경을 위한 Gym 인터페이스
    """
    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(YakemonEnv, self).__init__()
        self._battle_sequence_lock = asyncio.Lock()
        self.pokemon_list = create_mock_pokemon_list()
        
        # 상태 공간 정의 (1165차원)
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(1165,),
            dtype=np.float32
        )
        
        # 행동 공간 정의 (6개 행동: 4개 기술 + 2개 교체)
        # 각 행동이 가능한지 여부를 나타내는 마스크 추가
        self.action_space = spaces.MultiDiscrete([2] * 6)  # 각 행동이 가능하면 1, 불가능하면 0
        
        # 배틀 스토어와 환경 초기화
        self.battle_store = store
        self.duration_store = duration_store
        self.public_env = PublicBattleEnvironment()
        self.my_env = IndividualBattleEnvironment()
        self.enemy_env = IndividualBattleEnvironment()
        
        # 추가 속성 초기화
        self.my_team = []
        self.enemy_team = []
        self.turn = 1
        self.done = False
        self.switching_disabled = False  # 교체 비활성화 플래그 추가
        
        self.reset()

    def reset(self, my_team=None, enemy_team=None):
        """
        환경 초기화
        """
        # 팀이 주어지지 않은 경우 랜덤 팀 생성
        if my_team is None:
            my_team = create_mock_pokemon_list()[:3]
        if enemy_team is None:
            enemy_team = create_mock_pokemon_list()[3:6]
            
        # 만약 이미 BattlePokemon이면 변환하지 않음
        def ensure_battle_pokemon(poke):
            if isinstance(poke, BattlePokemon):
                # PP 초기화
                for move in poke.base.moves:
                    poke.pp[move.name] = move.pp_max
                return poke
            else:
                return create_battle_pokemon(poke)
        
        # PokemonInfo를 BattlePokemon으로 변환하고 PP 초기화
        my_team = [ensure_battle_pokemon(poke) for poke in my_team]
        enemy_team = [ensure_battle_pokemon(poke) for poke in enemy_team]
        
        # 배틀 스토어 초기화
        self.battle_store.reset_all()
        self.battle_store.set_my_team(my_team)
        self.battle_store.set_enemy_team(enemy_team)
        
        # 첫 번째 포켓몬을 활성화
        self.battle_store.set_active_index("my", 0)
        self.battle_store.set_active_index("enemy", 0)
        
        # 내부 팀 변수 업데이트
        self.my_team = my_team
        self.enemy_team = enemy_team
        
        # 배틀 환경 설정
        public_env = PublicBattleEnvironment()
        my_env = IndividualBattleEnvironment()
        enemy_env = IndividualBattleEnvironment()
        
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
        self.switching_disabled = False  # 교체 비활성화 플래그 초기화
        
        # 초기 상태 반환
        return self._get_state()

    def _get_action_mask(self) -> np.ndarray:
        """
        현재 상태에서 가능한 행동들의 마스크를 반환
        Returns:
            np.ndarray: 각 행동이 가능하면 1, 불가능하면 0인 마스크
        """
        mask = np.ones(6, dtype=np.int32)  # 기본적으로 모든 행동 가능
        
        current_index = self.battle_store.get_active_index("my")
        current_pokemon = self.my_team[current_index]
        
        # 기술 사용(0-3)에 대한 마스킹
        for i in range(4):
            if current_pokemon.pp.get(current_pokemon.base.moves[i].name, 0) <= 0:
                print(f"battle_env: {current_pokemon.base.moves[i].name} 기술의 PP가 0입니다.")
                mask[i] = 0
        
        # 교체가 비활성화된 경우 교체 행동 마스킹
        if self.switching_disabled:
            print("battle_env: 교체가 비활성화되어 교체가 마스킹된 상태입니다.")
            mask[4:] = 0
        else:
            # 교체 행동(4,5)에 대한 마스킹
            other_indices = [0, 1, 2]
            other_indices.remove(current_index) # 현재 포켓몬 제외
            for i in range(2):  # 교체 행동 2개
                switch_index = other_indices[i]
                # 자기 자신으로 교체하는 경우
                if switch_index == current_index:
                    mask[4 + i] = 0
                # 교체하려는 포켓몬이 쓰러진 경우
                elif self.my_team[switch_index].current_hp <= 0:
                    mask[4 + i] = 0
        print(f"battle_env: 현재 포켓몬: {current_pokemon.base.name}, 현재 포켓몬의 기술 마스크: {mask[:4]}, 교체 마스크: {mask[4:]}")
        return mask

    def _get_state(self):
        """현재 상태 벡터 반환"""
        state_vector = get_state(
            store=self.battle_store,
            my_team=self.my_team,
            enemy_team=self.enemy_team,
            active_my=self.battle_store.get_active_index("my"),
            active_enemy=self.battle_store.get_active_index("enemy"),
            public_env=self.public_env,
            my_env=self.my_env,
            enemy_env=self.enemy_env,
            turn=self.turn,
            my_effects=self.duration_store.my_effects,
            enemy_effects=self.duration_store.enemy_effects
        )
        # 상태 벡터에 action mask 추가
        action_mask = self._get_action_mask()
        return np.concatenate([state_vector, action_mask])

    async def step(self, action: int, test: bool = False) -> Tuple[np.ndarray, float, bool, Dict]:
        """
        환경에서 한 스텝 진행
        
        Args:
            action: 수행할 행동 (0-5)
                0-3: 기술 사용
                4-5: 포켓몬 교체
        
        Returns:
            observation: 다음 상태
            reward: 보상
            done: 에피소드 종료 여부
            info: 추가 정보
        """
        try:
            # 현재 상태 저장
            current_state = self._get_state()
            alive_my_pokemon = [p for p in self.my_team if p.current_hp > 0]
            alive_enemy_pokemon = [p for p in self.enemy_team if p.current_hp > 0]
            print('턴: ',self.turn)
            print(f"현재 남은 내 포켓몬: {len(alive_my_pokemon)}")
            print(f"현재 남은 상대 포켓몬: {len(alive_enemy_pokemon)}")
            print(f"현재 내 포켓몬: {self.my_team[self.battle_store.get_active_index('my')].base.name}")
            print(f"현재 상대 포켓몬: {self.enemy_team[self.battle_store.get_active_index('enemy')].base.name}")
            
            # 교체가 비활성화된 상태에서 교체 행동을 시도한 경우
            if self.switching_disabled and action >= 4:
                print("battle_env: 교체가 비활성화된 상태입니다.")
                return current_state, -100.0, self.done, {"error": "switching_disabled"}
            
            # 행동 실행
            if action == -1:
                print("battle_env: 행동 불가 상태")
                battle_action = None
            elif action < 4:  # 기술 사용
                move = self.my_team[self.battle_store.get_active_index("my")].base.moves[action]
                print(f"내 기술: {move.name}")
                battle_action = move
            else:  # 포켓몬 교체
                current_index = self.battle_store.get_active_index("my")
                # 교체 가능한 포켓몬들의 인덱스 계산
                available_indices = [i for i in range(3) if i != current_index and self.my_team[i].current_hp > 0]
                
                if not available_indices:
                    print("battle_env: 교체할 수 없습니다.")
                    self.switching_disabled = True  # 교체 비활성화 플래그 설정
                    return current_state, -100.0, self.done, {"error": "no_available_switch"}
                
                # action이 4나 5일 때, available_indices에서 적절한 인덱스 선택
                switch_index = available_indices[action - 4] if action - 4 < len(available_indices) else available_indices[0]
                
                battle_action = {"type": "switch", "index": switch_index}
                print(f"내가 교체하려는 포켓몬: {self.my_team[switch_index].base.name}")
                self.battle_store.add_log(f"내가 교체하려는 포켓몬: {self.my_team[switch_index].base.name}")
            
            # 배틀 시퀀스 실행
            async with self._battle_sequence_lock:
                try:
                    enemy_action = base_ai_choose_action(
                        side="enemy",
                        my_team=self.my_team,
                        enemy_team=self.enemy_team,
                        active_my=self.battle_store.get_active_index("my"),
                        active_enemy=self.battle_store.get_active_index("enemy"),
                        public_env=self.public_env.__dict__,
                        enemy_env=self.my_env.__dict__,
                        my_env=self.enemy_env.__dict__,
                        add_log=self.battle_store.add_log
                    ) if not test else random_enemy_action(
                        self.enemy_team, 
                        self.battle_store.get_active_index("enemy")
                        )
                    
                    # 교체와 기술이 동시에 실행되지 않도록 확인
                    if isinstance(battle_action, dict) and battle_action["type"] == "switch" and isinstance(enemy_action, dict) and enemy_action["type"] == "switch":
                        # 둘 다 교체하려는 경우, 랜덤하게 하나만 실행
                        if random.random() < 0.5:
                            enemy_action = self.enemy_team[self.battle_store.get_active_index("enemy")].base.moves[0]
                    
                    await battle_sequence(
                        my_action=battle_action,
                        enemy_action=enemy_action
                    )
                except Exception as e:
                    print(f"Error during battle sequence: {str(e)}")
                    return current_state, -100.0, True, {"error": "battle_sequence_error"}
            
            # 쓰러진 포켓몬 처리
            active_my = self.battle_store.get_active_index("my")
            active_enemy = self.battle_store.get_active_index("enemy")
            
            # 게임 종료 체크
            self.done = self.check_game_end()
            
            # 게임이 끝났다면 더 이상의 처리를 하지 않고 종료
            if self.done:
                next_state = self._get_state()
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
                print(f"Reward in this step: {reward}")
                return next_state, reward, self.done, {}
            
            # 내 포켓몬이 쓰러졌는지 확인
            if self.my_team[active_my] and self.my_team[active_my].current_hp <= 0:
                await remove_fainted_pokemon("my")
                next_state = self._get_state()
                reward = 0  # 교체만으로는 보상 없음
                
            # 상대 포켓몬이 쓰러졌는지 확인
            if active_enemy is not None:
                enemy_team = self.battle_store.get_team("enemy")
                if enemy_team and 0 <= active_enemy < len(enemy_team) and enemy_team[active_enemy] is not None:
                    if enemy_team[active_enemy].current_hp <= 0:
                        await remove_fainted_pokemon("enemy")
                        next_state = self._get_state()
                        reward = 0  # 교체만으로는 보상 없음
        
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
            print(f"Reward in this step: {reward}")
            # 턴 증가
            self.turn += 1
            
            # 추가 정보
            info = {
                'turn': self.turn,
                'my_hp': self.my_team[self.battle_store.get_active_index("my")].current_hp,
                'enemy_hp': self.enemy_team[self.battle_store.get_active_index("enemy")].current_hp,
                'public_env': self.public_env.__dict__,
                'my_env': self.my_env.__dict__,
                'enemy_env': self.enemy_env.__dict__,
                'switching_disabled': self.switching_disabled
            }
            
            return next_state, reward, self.done, info
            
        except Exception as e:
            print(f"Error in step: {str(e)}")
            return current_state, -100.0, True, {"error": "step_error"}

    def check_game_end(self) -> bool:
        """게임 종료 조건 체크"""
        # 턴 제한 체크
        if self.turn > 40:
            return True
            
        # 내 팀의 모든 포켓몬이 쓰러졌는지 확인
        my_all_fainted = all(p is not None and p.current_hp <= 0 for p in self.my_team)
        
        # 상대 팀의 모든 포켓몬이 쓰러졌는지 확인
        enemy_all_fainted = all(p is not None and p.current_hp <= 0 for p in self.enemy_team)
        
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