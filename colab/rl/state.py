"""강화학습을 위한 상태 표현 모듈"""

import numpy as np
from colab.p_models.types import PokemonType

class BattleState:
    """배틀 상태를 강화학습에 적합한 형태로 변환하는 클래스"""
    
    @staticmethod
    def get_state_vector(battle, for_opponent=False):
        """배틀 상태를 벡터로 변환"""
        state = []

        if not for_opponent:
            # 플레이어 관점
            player_team = battle.player_team
            opponent_team = battle.opponent_team
        else:
            # 상대방 관점 (플레이어와 상대방이 뒤바뀜)
            player_team = battle.opponent_team
            opponent_team = battle.player_team

        # 현재 포켓몬 정보
        player_pokemon = player_team.active_pokemon
        opponent_pokemon = opponent_team.active_pokemon

        # 플레이어 포켓몬 정보
        state.extend(BattleState._get_pokemon_state(player_pokemon))
        
        # 상대방 포켓몬 정보
        state.extend(BattleState._get_pokemon_state(opponent_pokemon))

        # 팀 정보 (남은 포켓몬 수)
        state.append(len([p for p in player_team.pokemons if not p.is_fainted()]) / len(player_team.pokemons))
        state.append(len([p for p in opponent_team.pokemons if not p.is_fainted()]) / len(opponent_team.pokemons))

        # 지형 효과 정보
        terrain_state = [0.0] * 4  # 풀, 전기, 에스퍼, 페어리
        if battle.terrain:
            terrain_name = battle.terrain['name']
            if terrain_name == "Grassy Terrain":
                terrain_state[0] = 1.0
            elif terrain_name == "Electric Terrain":
                terrain_state[1] = 1.0
            elif terrain_name == "Psychic Terrain":
                terrain_state[2] = 1.0
            elif terrain_name == "Misty Terrain":
                terrain_state[3] = 1.0
        state.extend(terrain_state)

        return np.array(state, dtype=np.float32)

    @staticmethod
    def _get_pokemon_state(pokemon):
        """개별 포켓몬의 상태를 벡터로 변환"""
        state = []

        # HP 비율 (1)
        state.append(pokemon.current_hp / pokemon.stats['hp'])

        # 타입 (원-핫 인코딩) (18)
        for type_id in range(18):
            state.append(1.0 if type_id in pokemon.types else 0.0)

        # 주요 스탯 (5)
        for stat_name in ['atk', 'def', 'spa', 'spd', 'spe']:
            state.append(pokemon.calculate_stat(stat_name) / 255.0)  # 정규화

        # 상태 이상 (원-핫 인코딩) (7)
        status_conditions = [None, 'Poison', 'Paralyze', 'Burn', 'Sleep', 'Freeze', 'Confusion']
        for status in status_conditions:
            state.append(1.0 if pokemon.status_condition == status else 0.0)

        # 스탯 변화 (7)
        for stat_name in ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion']:
            state.append((pokemon.stat_stages[stat_name] + 6) / 12.0)  # -6~+6 범위를 0~1로 정규화

        # 기술 정보 (PP 비율) - 항상 4개의 기술 (4)
        for i in range(4):
            if i < len(pokemon.moves) and pokemon.moves[i]:
                state.append(pokemon.moves[i].pp / pokemon.moves[i].max_pp)
            else:
                state.append(0.0)  # 4개 미만의 기술은 0으로 패딩

        return state

    @staticmethod
    def get_state_size():
        """상태 벡터의 크기 반환"""
        # 포켓몬당: 1(HP) + 18(타입) + 5(스탯) + 7(상태) + 7(스탯변화) + 4(기술) = 42
        # 팀 정보: 2(남은 포켓몬 수)
        # 지형 효과: 4
        return 42 * 2 + 2 + 4  # 총 90차원 