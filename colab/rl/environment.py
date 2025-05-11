"""강화학습 환경 모듈"""

import random
import numpy as np
from tqdm import tqdm
from copy import deepcopy
import gymnasium as gym

from colab.p_models.team import PokemonTeam
from colab.p_models.templates import POKEMON_TEMPLATES, create_pokemon_from_template, FIRE_POKEMON, WATER_POKEMON, GRASS_POKEMON
from colab.battle.battle import PokemonBattle
from colab.p_models.types import Terrain, get_type_name
from colab.rl.state import BattleState

def create_fixed_team():
    """리자몽, 이상해꽃, 거북왕으로 구성된 고정 팀 생성"""
    # 해당 포켓몬 템플릿 찾기
    venusaur_template = next(p for p in POKEMON_TEMPLATES if p["name"] == "이상해꽃")
    charizard_template = next(p for p in POKEMON_TEMPLATES if p["name"] == "리자몽")
    blastoise_template = next(p for p in POKEMON_TEMPLATES if p["name"] == "거북왕")

    # 포켓몬 생성
    venusaur = create_pokemon_from_template(venusaur_template)
    charizard = create_pokemon_from_template(charizard_template)
    blastoise = create_pokemon_from_template(blastoise_template)

    # 팀 생성
    team = [venusaur, charizard, blastoise]
    return PokemonTeam(team)

def create_balanced_team():
    """불, 물, 풀 타입의 포켓몬으로 구성된 균형 잡힌 팀 생성"""
    # 각 주요 타입의 포켓몬 선택
    fire_pokemon = create_pokemon_from_template(random.choice(FIRE_POKEMON))
    water_pokemon = create_pokemon_from_template(random.choice(WATER_POKEMON))
    grass_pokemon = create_pokemon_from_template(random.choice(GRASS_POKEMON))

    # 팀 생성
    team = [fire_pokemon, water_pokemon, grass_pokemon]

    # 순서 랜덤화
    random.shuffle(team)

    return PokemonTeam(team)

def create_pokemon_teams():
    """포켓몬 팀 생성 (각 팀이 불, 물, 풀 타입을 포함하도록)"""
    # 균형 잡힌 팀 생성
    player_team = create_fixed_team()
    opponent_team = create_balanced_team()

    return player_team, opponent_team

class PokemonEnv(gym.Env):
    """강화학습을 위한 환경 클래스 (턴 순서와 기절 처리 수정)"""
    def __init__(self, create_pokemon_teams_fn, opponent_agent=None):
        """
        환경 초기화
        Args:
            create_pokemon_teams_fn: 포켓몬 팀을 생성하는 함수
            opponent_agent: 상대 에이전트 (None인 경우 기본 AI 사용)
        """
        self.create_pokemon_teams_fn = create_pokemon_teams_fn
        self.opponent_agent = opponent_agent
        self.battle = None

        # 액션 공간 정의 (4개 기술 + 2개 교체)
        self.action_space = gym.spaces.Discrete(6)

        # 관찰 공간 정의 (상태 벡터 크기에 맞춰 조정)
        self.observation_space = gym.spaces.Box(
            low=0.0,
            high=1.0,
            shape=(BattleState.get_state_size(),),  # 상태 벡터 크기
            dtype=np.float32
        )

        # 초기화
        self.reset()

    def reset(self, seed=None, options=None):
        """환경 초기화"""
        super().reset(seed=seed)

        # 팀 생성
        player_team, opponent_team = self.create_pokemon_teams_fn()

        # 배틀 초기화 또는 기존 배틀 리셋
        if self.battle is None:
            self.battle = PokemonBattle(player_team, opponent_team)
        else:
            self.battle.player_team = player_team
            self.battle.opponent_team = opponent_team
            self.battle.reset()

        self.done = False
        self.reward = 0
        self.total_player_hp_sum = sum(p.stats['hp'] for p in self.battle.player_team.pokemons)
        self.total_opponent_hp_sum = sum(p.stats['hp'] for p in self.battle.opponent_team.pokemons)
        self.prev_player_hp_sum = sum(p.current_hp for p in self.battle.player_team.pokemons)
        self.prev_opponent_hp_sum = sum(p.current_hp for p in self.battle.opponent_team.pokemons)

        observation = self.get_state()
        info = {}

        return observation, info

    def step(self, action):
        """행동 수행 및 환경 진행"""
        truncated = False
        if self.done:
            return self.get_state(), 0, True, truncated, {"battle_over": True}

        # 보상 계산을 위한 이전 상태 저장
        prev_player_hp_sum = self.prev_player_hp_sum
        prev_opponent_hp_sum = self.prev_opponent_hp_sum

        # 행동 분류
        if action < 4:  # 기술 사용
            action_type = "move"
            action_index = action

            # 안전 검사: 유효한 기술인지 확인
            valid_moves = self.battle.player_team.active_pokemon.get_valid_moves()
            if action not in valid_moves:
                if valid_moves:
                    action_index = valid_moves[0]
                else:
                    return self.get_state(), -1, False, truncated, {"error": "No valid moves available"}
        else:  # 포켓몬 교체
            action_type = "switch"
            valid_switches = self.battle.player_team.get_valid_switches()
            switch_index = action - 4

            if switch_index < len(valid_switches):
                action_index = valid_switches[switch_index]
            else:
                return self.get_state(), -1, False, truncated, {"error": "Invalid switch index"}

        # 플레이어 행동 수행 (상대방 행동 포함)
        results = self.battle.player_action(action_type, action_index, self.opponent_agent)

        # 결과 정보 추출
        player_result = None
        opponent_result = None

        for item in results:
            if isinstance(item, dict):
                if item.get("actor") == "player":
                    player_result = item.get("result", {})
                elif item.get("actor") == "opponent":
                    opponent_result = item.get("result", {})

        # 보상 계산을 위한 현재 상태
        current_player_hp_sum = sum(p.current_hp for p in self.battle.player_team.pokemons)
        current_opponent_hp_sum = sum(p.current_hp for p in self.battle.opponent_team.pokemons)

        # HP 백분율 계산
        player_hp_percent = current_player_hp_sum / self.total_player_hp_sum
        opponent_hp_percent = current_opponent_hp_sum / self.total_opponent_hp_sum
        prev_player_hp_percent = prev_player_hp_sum / self.total_player_hp_sum
        prev_opponent_hp_percent = prev_opponent_hp_sum / self.total_opponent_hp_sum

        # HP 차이 백분율 계산
        player_hp_diff = player_hp_percent - prev_player_hp_percent
        opponent_hp_diff = opponent_hp_percent - prev_opponent_hp_percent

        # 저장된 HP 값 업데이트
        self.prev_player_hp_sum = current_player_hp_sum
        self.prev_opponent_hp_sum = current_opponent_hp_sum

        # 배틀 종료 확인
        if self.battle.is_battle_over():
            self.done = True
            winner = self.battle.get_winner()

            # 최종 보상 계산
            if winner == "player":
                win_reward = 10.0
                health_bonus = player_hp_percent * 5.0
                health_penalty = (1.0 - player_hp_percent) * 2.0
                damage_bonus = (1.0 - opponent_hp_percent) * 5.0

                reward = win_reward + health_bonus - health_penalty + damage_bonus
            else:
                loss_penalty = -10.0
                damage_bonus = (1.0 - opponent_hp_percent) * 3.0

                reward = loss_penalty + damage_bonus

            return self.get_state(), reward, True, truncated, {"battle_over": True, "winner": winner}

        # 중간 보상 계산
        damage_reward = -opponent_hp_diff * 3.0
        damage_penalty = player_hp_diff * 3.0

        effectiveness_bonus = 0.0
        if player_result and player_result.get("effectiveness") == "효과가 뛰어났다!":
            effectiveness_bonus = 2

        effectiveness_penalty = 0.0
        if player_result and player_result.get("effectiveness") == "효과가 별로인 듯하다...":
            effectiveness_penalty = -2

        miss_penalty = 0.0
        if player_result and player_result.get("success") and player_result.get("damage", 0) == 0:
            miss_penalty = -0.2

        status_bonus = 0.0
        if player_result and player_result.get("success") and "effects" in player_result:
            status_bonus = 0.2

        critical_bonus = 0.0
        if player_result and player_result.get("success") and "effects" in player_result:
            for effect in player_result["effects"]:
                if "급소에 맞았다!" in effect:
                    critical_bonus = 0.3
                    break

        terrain_bonus = 0.0
        if (self.battle.terrain and player_result and player_result.get("success") and
            player_result.get("damage", 0) > 0):
            terrain_type = self.battle.terrain['name']
            player_move = self.battle.player_team.active_pokemon.moves[action_index]
            move_type_name = get_type_name(player_move.type)

            if ((terrain_type == Terrain.GRASSY and move_type_name == "풀") or
                (terrain_type == Terrain.ELECTRIC and move_type_name == "전기") or
                (terrain_type == Terrain.PSYCHIC and move_type_name == "에스퍼")):
                terrain_bonus = 0.4

        reward = (damage_reward + damage_penalty +
                 effectiveness_bonus + effectiveness_penalty +
                 critical_bonus + terrain_bonus)

        reward = max(-10.0, min(10.0, reward))

        return self.get_state(), reward, False, False, {
            "player_result": player_result,
            "opponent_result": opponent_result,
            "player_hp_diff": player_hp_diff,
            "opponent_hp_diff": opponent_hp_diff
        }

    def get_state(self):
        """강화학습을 위한 상태 벡터 반환"""
        return BattleState.get_state_vector(self.battle)

    def get_valid_actions(self):
        """유효한 행동 목록 반환"""
        return self.battle.get_valid_actions()

class ParallelPokemonEnv:
    """여러 포켓몬 배틀을 위한 병렬 환경"""

    def __init__(self, num_envs=16, opponent_agent=None):
        """
        여러 포켓몬 환경 초기화

        Args:
            num_envs: 병렬 환경 수
            opponent_agent: 선택적 상대 에이전트 (자기 대결용)
        """
        self.num_envs = num_envs
        self.envs = []

        # 환경 생성
        for _ in range(num_envs):
            self.envs.append(PokemonEnv(create_pokemon_teams, opponent_agent))

    def reset(self):
        """모든 환경 초기화"""
        states = []
        for env in self.envs:
            states.append(env.reset())
        return np.array(states)

    def reset_single(self, env_idx):
        """단일 환경 초기화"""
        return self.envs[env_idx].reset()

    def step(self, actions):
        """모든 환경에서 한 스텝 진행"""
        states = []
        rewards = []
        dones = []
        infos = []

        for env, action in zip(self.envs, actions):
            state, reward, done, info = env.step(action)
            states.append(state)
            rewards.append(reward)
            dones.append(done)
            infos.append(info)

        return np.array(states), np.array(rewards), np.array(dones), infos

    def get_valid_actions(self):
        """각 환경의 유효한 행동 목록 반환"""
        valid_actions = []
        for env in self.envs:
            valid_actions.append(env.get_valid_actions())
        return valid_actions

    def update_opponent(self, opponent_agent):
        """모든 환경의 상대 에이전트 업데이트"""
        for env in self.envs:
            env.opponent_agent = opponent_agent 