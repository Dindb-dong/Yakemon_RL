"""강화학습을 위한 보상 계산 모듈"""

class BattleReward:
    """배틀 보상 계산 클래스"""
    
    @staticmethod
    def calculate_reward(battle, action_type, action_index, result):
        """행동에 대한 보상 계산"""
        reward = 0.0

        # 기본 보상: 데미지 비율
        if result.get("success", False):
            if "damage" in result and "before_hp" in result:
                damage = result["damage"]
                before_hp = result["before_hp"]
                if before_hp > 0:
                    reward += (damage / before_hp) * 0.5  # 데미지 비율에 0.5 가중치

        # 추가 보상: 상태 이상 부여
        if result.get("success", False) and "effects" in result:
            for effect in result["effects"]:
                if "상태가 되었다" in effect:
                    reward += 0.3  # 상태 이상 부여 성공

        # 추가 보상: 효과가 뛰어남
        if result.get("success", False) and result.get("effectiveness") == "효과가 뛰어났다!":
            reward += 0.2  # 효과가 뛰어난 기술 사용

        # 추가 보상: 치명타
        if result.get("success", False) and "급소에 맞았다!" in result.get("effects", []):
            reward += 0.3  # 치명타 성공

        # 패널티: 기술 실패
        if not result.get("success", False):
            reward -= 0.1  # 기술 실패

        # 패널티: PP 소진
        if action_type == "move" and result.get("success", False):
            pokemon = battle.player_team.active_pokemon
            if pokemon.moves[action_index].pp == 0:
                reward -= 0.2  # PP 소진

        # 승리/패배 보상
        if battle.is_battle_over():
            winner = battle.get_winner()
            if winner == "player":
                reward += 1.0  # 승리
            else:
                reward -= 1.0  # 패배

        return reward

    @staticmethod
    def calculate_team_reward(battle):
        """팀 전체 상태에 대한 보상 계산"""
        reward = 0.0

        # 남은 포켓몬 수에 따른 보상
        player_alive = len([p for p in battle.player_team.pokemons if not p.is_fainted()])
        opponent_alive = len([p for p in battle.opponent_team.pokemons if not p.is_fainted()])
        
        # 포켓몬 수 차이에 따른 보상
        reward += (player_alive - opponent_alive) * 0.2

        # 현재 포켓몬의 HP 비율에 따른 보상
        player_hp_ratio = battle.player_team.active_pokemon.current_hp / battle.player_team.active_pokemon.stats['hp']
        opponent_hp_ratio = battle.opponent_team.active_pokemon.current_hp / battle.opponent_team.active_pokemon.stats['hp']
        
        # HP 비율 차이에 따른 보상
        reward += (player_hp_ratio - opponent_hp_ratio) * 0.3

        return reward 