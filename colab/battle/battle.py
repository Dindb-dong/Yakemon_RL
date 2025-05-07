"""배틀 클래스를 정의하는 모듈"""

from .damage import calculate_damage

class PokemonBattle:
    """Pokémon battle class - updated with speed-based turn order and proper switching"""
    def __init__(self, player_team, opponent_team):
        self.player_team = player_team
        self.opponent_team = opponent_team
        self.turn = 0
        self.last_move_result = None
        self.pending_switch = None  # To track forced switches after fainting
        self.terrain = None  # 현재 지형 효과 추가

    def set_terrain(self, terrain_type, duration=5):
        """지형 효과 설정"""
        self.terrain = {
            'name': terrain_type,
            'turns': duration
        }
        return f"{terrain_type} 효과가 발동되었다!"

    def is_battle_over(self):
        """Check if battle is over"""
        return self.player_team.all_fainted() or self.opponent_team.all_fainted()

    def get_winner(self):
        """Get winner"""
        if self.player_team.all_fainted():
            return "opponent"
        if self.opponent_team.all_fainted():
            return "player"
        return None

    def reset(self):
        """Reset battle to initial state"""
        # 두 팀의 포켓몬을 모두 리셋
        self.player_team.reset()
        self.opponent_team.reset()

        # 기타 배틀 상태 초기화
        self.turn = 0
        self.last_move_result = None
        self.pending_switch = None
        self.terrain = None  # 지형 효과 초기화

    def _perform_move(self, attacker, defender, move_index):
        """Move execution logic"""
        # 안전 체크 추가
        if move_index >= len(attacker.moves):
            print(f"오류: {attacker.name}의 기술 인덱스({move_index})가 범위를 벗어남 (기술 개수: {len(attacker.moves)})")
            # 유효한 첫 번째 기술 사용
            valid_moves = attacker.get_valid_moves()
            if valid_moves:
                move_index = valid_moves[0]
            else:
                # 이 부분은 실행될 가능성이 없지만 안전장치로 유지
                print(f"심각한 오류: {attacker.name}에게 유효한 기술이 없습니다.")
                return {
                    "success": False,
                    "message": f"{attacker.name}은(는) 움직일 수 없다!"
                }

        move = attacker.moves[move_index]

        # Check if Pokemon can move
        if not attacker.can_move():
            return {
                "success": False,
                "message": f"{attacker.name}은(는) {attacker.status_condition} 상태라 움직일 수 없다!"
            }

        # Calculate damage
        damage = calculate_damage(move, attacker, defender, self)

        # Apply damage
        if damage > 0:
            defender.current_hp = max(0, defender.current_hp - damage)
            message = f"{attacker.name}의 {move.name}! {defender.name}에게 {damage}의 데미지!"
        else:
            message = f"{attacker.name}의 {move.name}! 하지만 빗나갔다!"

        # Decrease PP
        move.pp -= 1

        # Check for fainting
        if defender.is_fainted():
            message += f"\n{defender.name}은(는) 쓰러졌다!"

        return {
            "success": True,
            "message": message,
            "damage": damage
        }

    def execute_turn(self, player_move_index, opponent_move_index):
        """Execute a turn of battle"""
        self.turn += 1
        results = []

        # Get active Pokemon
        player_pokemon = self.player_team.active_pokemon
        opponent_pokemon = self.opponent_team.active_pokemon

        # Determine turn order based on speed
        player_speed = player_pokemon.calculate_stat('spe')
        opponent_speed = opponent_pokemon.calculate_stat('spe')

        # Execute moves in speed order
        if player_speed >= opponent_speed:
            # Player moves first
            player_result = self._perform_move(player_pokemon, opponent_pokemon, player_move_index)
            results.append(player_result)

            if not opponent_pokemon.is_fainted():
                opponent_result = self._perform_move(opponent_pokemon, player_pokemon, opponent_move_index)
                results.append(opponent_result)
        else:
            # Opponent moves first
            opponent_result = self._perform_move(opponent_pokemon, player_pokemon, opponent_move_index)
            results.append(opponent_result)

            if not player_pokemon.is_fainted():
                player_result = self._perform_move(player_pokemon, opponent_pokemon, player_move_index)
                results.append(player_result)

        # Apply status effects at end of turn
        if not player_pokemon.is_fainted():
            status_effects = player_pokemon.apply_status_turn_end()
            results.extend([{"success": True, "message": effect} for effect in status_effects])

        if not opponent_pokemon.is_fainted():
            status_effects = opponent_pokemon.apply_status_turn_end()
            results.extend([{"success": True, "message": effect} for effect in status_effects])

        # Update terrain duration
        if self.terrain:
            self.terrain['turns'] -= 1
            if self.terrain['turns'] <= 0:
                results.append({
                    "success": True,
                    "message": f"{self.terrain['name']} 효과가 사라졌다!"
                })
                self.terrain = None

        return results 