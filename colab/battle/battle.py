"""배틀 클래스를 정의하는 모듈"""

from .damage import calculate_damage
from colab.p_models.types import TYPE_EFFECTIVENESS
from colab.p_models.moves import get_move_priority

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

    def _process_turn(self, player_action_type, player_action_index, opponent_agent=None):
        """Process a complete turn with speed comparison and priority moves"""
        results = []

        # Get active Pokémon
        player_pokemon = self.player_team.active_pokemon
        opponent_pokemon = self.opponent_team.active_pokemon

        # Handle player switch action (switches happen before moves)
        player_switched = False
        if player_action_type == "switch":
            if self.player_team.switch_pokemon(player_action_index):
                result = {"success": True, "message": f"{self.player_team.active_pokemon.name}으로 교체했습니다!"}
                results.append({"actor": "player", "result": result})
                player_switched = True
            else:
                result = {"success": False, "message": "교체할 수 없는 포켓몬입니다."}
                results.append({"actor": "player", "result": result})
                return results  # Return early if switch fails

        # Determine opponent action
        opponent_action_type = "move"
        opponent_action_index = 0

        if opponent_agent is not None:
            # Use provided agent
            state = self.get_state(for_opponent=True)
            valid_actions = self.get_valid_actions(for_opponent=True)
            action = opponent_agent.choose_action(state, valid_actions)

            # Classify action
            if action < 4:  # Use move
                opponent_action_type = "move"
                opponent_action_index = action
            else:  # Switch Pokémon
                opponent_action_type = "switch"
                switch_index = action - 4
                valid_switches = self.opponent_team.get_valid_switches()
                if 0 <= switch_index < len(valid_switches):
                    opponent_action_index = valid_switches[switch_index]
                else:
                    # Invalid switch, default to first move
                    valid_moves = self.opponent_team.active_pokemon.get_valid_moves()
                    if valid_moves:
                        opponent_action_index = valid_moves[0]
        else:
            # Default AI logic for move selection
            active_pokemon = self.opponent_team.active_pokemon
            player_pokemon = self.player_team.active_pokemon

            # Get valid moves first
            valid_moves = active_pokemon.get_valid_moves()

            # Calculate estimated damage for all moves
            best_damage = -1
            best_move_index = -1

            for i, move in enumerate(active_pokemon.moves):
                if move.pp <= 0:
                    continue

                # Calculate potential damage
                potential_damage = 0
                if move.category != 'Status':
                    # Type effectiveness
                    type_effectiveness = 1.0
                    for def_type in player_pokemon.types:
                        type_effectiveness *= TYPE_EFFECTIVENESS[move.type][def_type]

                    # STAB
                    stab = 1.5 if move.type in active_pokemon.types else 1.0

                    # Attack/defense stats
                    if move.category == 'Physical':
                        attack_stat = active_pokemon.calculate_stat('atk')
                        defense_stat = player_pokemon.calculate_stat('def')
                    else:  # Special
                        attack_stat = active_pokemon.calculate_stat('spa')
                        defense_stat = player_pokemon.calculate_stat('spd')

                    # Damage calculation (excluding random factors)
                    potential_damage = ((2 * active_pokemon.level / 5 + 2) * move.power * attack_stat / defense_stat / 50 + 2)
                    potential_damage *= stab * type_effectiveness

                # Select best move
                if potential_damage > best_damage:
                    best_damage = potential_damage
                    best_move_index = i

            # Choose move with highest potential damage
            valid_moves = active_pokemon.get_valid_moves()

            if valid_moves:
                if best_move_index != -1 and best_move_index in valid_moves:
                    opponent_action_index = best_move_index
                else:
                    opponent_action_index = valid_moves[0]  # 첫 번째 유효한 기술 선택
            else:
                # 유효한 기술이 없다면 몸부림치기 사용
                # get_valid_moves()는 몸부림치기를 추가하고 인덱스를 반환함
                opponent_action_index = active_pokemon.get_valid_moves()[0]

        # Handle opponent switch action
        opponent_switched = False
        if opponent_action_type == "switch":
            if self.opponent_team.switch_pokemon(opponent_action_index):
                result = {"success": True, "message": f"상대가 {self.opponent_team.active_pokemon.name}으로 교체했습니다!"}
                results.append({"actor": "opponent", "result": result})
                opponent_switched = True
            else:
                # If switch fails, use first valid move
                opponent_action_type = "move"
                valid_moves = self.opponent_team.active_pokemon.get_valid_moves()
                if valid_moves:
                    opponent_action_index = valid_moves[0]
                else:
                    result = {"success": False, "message": "상대방이 행동할 수 없습니다."}
                    results.append({"actor": "opponent", "result": result})
                    return results

        # Both players have switched or chosen moves, now execute moves in speed/priority order
        if not player_switched and player_action_type == "move" and not opponent_switched and opponent_action_type == "move":
            # Both chose moves, determine order based on priority and speed
            player_move = player_pokemon.moves[player_action_index]
            opponent_move = opponent_pokemon.moves[opponent_action_index]

            # 우선권 확인
            player_priority = get_move_priority(player_move)
            opponent_priority = get_move_priority(opponent_move)

            # 우선권이 다르면 우선권이 높은 쪽이 먼저, 같으면 속도로 판단
            if player_priority > opponent_priority:
                player_first = True
            elif player_priority < opponent_priority:
                player_first = False
            else:  # 우선권이 같으면 속도로 결정
                player_first = player_pokemon.calculate_stat('spe') >= opponent_pokemon.calculate_stat('spe')

            if player_first:
                # Player goes first
                player_result = self._perform_move(
                    self.player_team.active_pokemon,
                    self.opponent_team.active_pokemon,
                    player_action_index
                )
                results.append({"actor": "player", "result": player_result})

                # Check if opponent's Pokémon fainted
                opp_faint_effects, opp_switched = self._handle_fainted_pokemon(self.opponent_team, False)
                if opp_faint_effects:
                    for effect in opp_faint_effects:
                        if "effects" not in player_result:
                            player_result["effects"] = []
                        player_result["effects"].append(effect)

                # If opponent's Pokémon didn't faint and player's move was successful, opponent gets to move
                if player_result.get("success", False) and not self.opponent_team.active_pokemon.is_fainted() and not self.is_battle_over():
                    opponent_result = self._perform_move(
                        self.opponent_team.active_pokemon,
                        self.player_team.active_pokemon,
                        opponent_action_index
                    )
                    results.append({"actor": "opponent", "result": opponent_result})

                    # Check if player's Pokémon fainted
                    player_faint_effects, player_switched = self._handle_fainted_pokemon(self.player_team, True)
                    if player_faint_effects:
                        for effect in player_faint_effects:
                            if "effects" not in opponent_result:
                                opponent_result["effects"] = []
                            opponent_result["effects"].append(effect)
            else:
                # Opponent goes first
                opponent_result = self._perform_move(
                    self.opponent_team.active_pokemon,
                    self.player_team.active_pokemon,
                    opponent_action_index
                )
                results.append({"actor": "opponent", "result": opponent_result})

                # Check if player's Pokémon fainted
                player_faint_effects, player_switched = self._handle_fainted_pokemon(self.player_team, True)
                if player_faint_effects:
                    for effect in player_faint_effects:
                        if "effects" not in opponent_result:
                            opponent_result["effects"] = []
                        opponent_result["effects"].append(effect)

                # If player's Pokémon didn't faint and opponent's move was successful, player gets to move
                if opponent_result.get("success", False) and not self.player_team.active_pokemon.is_fainted() and not self.is_battle_over():
                    player_result = self._perform_move(
                        self.player_team.active_pokemon,
                        self.opponent_team.active_pokemon,
                        player_action_index
                    )
                    results.append({"actor": "player", "result": player_result})

                    # Check if opponent's Pokémon fainted
                    opp_faint_effects, opp_switched = self._handle_fainted_pokemon(self.opponent_team, False)
                    if opp_faint_effects:
                        for effect in opp_faint_effects:
                            if "effects" not in player_result:
                                player_result["effects"] = []
                            player_result["effects"].append(effect)
        elif not player_switched and player_action_type == "move":
            # Only player uses move (opponent switched)
            player_result = self._perform_move(
                self.player_team.active_pokemon,
                self.opponent_team.active_pokemon,
                player_action_index
            )
            results.append({"actor": "player", "result": player_result})

            # Check if opponent's Pokémon fainted
            opp_faint_effects, opp_switched = self._handle_fainted_pokemon(self.opponent_team, False)
            if opp_faint_effects:
                for effect in opp_faint_effects:
                    if "effects" not in player_result:
                        player_result["effects"] = []
                    player_result["effects"].append(effect)
        elif not opponent_switched and opponent_action_type == "move":
            # Only opponent uses move (player switched)
            opponent_result = self._perform_move(
                self.opponent_team.active_pokemon,
                self.player_team.active_pokemon,
                opponent_action_index
            )
            results.append({"actor": "opponent", "result": opponent_result})

            # Check if player's Pokémon fainted
            player_faint_effects, player_switched = self._handle_fainted_pokemon(self.player_team, True)
            if player_faint_effects:
                for effect in player_faint_effects:
                    if "effects" not in opponent_result:
                        opponent_result["effects"] = []
                    opponent_result["effects"].append(effect)

        # Apply end-of-turn effects
        end_turn_effects, player_end_switched, opponent_end_switched = self.end_turn_effects()
        if end_turn_effects:
            results.append({"actor": "end_turn", "effects": end_turn_effects})

        # Increment turn counter
        self.turn += 1

        return results
    
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
    
    def player_action(self, action_type, action_index, opponent_agent=None):
        """Process player action and complete the turn"""
        if action_type not in ["move", "switch"]:
            return {"success": False, "message": "잘못된 행동 유형입니다."}

        # Validate action index
        if action_type == "move" and (action_index < 0 or action_index >= len(self.player_team.active_pokemon.moves)):
            return {"success": False, "message": "잘못된 기술 인덱스입니다."}
        elif action_type == "switch":
            valid_switches = self.player_team.get_valid_switches()
            if action_index not in valid_switches:
                return {"success": False, "message": "교체할 수 없는 포켓몬입니다."}

        # Process the complete turn
        results = self._process_turn(action_type, action_index, opponent_agent)

        # Store last move result
        if results:
            self.last_move_result = results[-1].get("result", {}) if isinstance(results[-1], dict) else {}

        return results

    def opponent_action(self, opponent_agent=None):
        """This method is kept for backward compatibility but redirects to player_action"""
        # Since opponent actions are now handled within player_action, this is just a wrapper
        # that returns the last opponent result from player_action
        if self.last_move_result:
            return self.last_move_result
        else:
            # If no previous action, create a default turn with player using first move
            results = self.player_action("move", 0, opponent_agent)

            # Extract opponent result if available
            for result_item in results:
                if isinstance(result_item, dict) and result_item.get("actor") == "opponent":
                    return result_item.get("result", {"success": False, "message": "상대방 행동 실패"})

            return {"success": False, "message": "상대방 행동 실패"}
        
    def get_valid_actions(self, for_opponent=False):
        """Return list of valid actions"""
        if not for_opponent:
            team = self.player_team
        else:
            team = self.opponent_team

        valid_actions = []

        # Valid moves: 0-3
        if team.active_pokemon:
            for i, move in enumerate(team.active_pokemon.moves):
                if i < 4 and move and move.pp > 0:  # Move exists and has PP
                    valid_actions.append(i)

            # Valid switches: 4-9 (max 6 Pokémon)
            valid_switches = team.get_valid_switches()
            for i, switch_index in enumerate(valid_switches):
                valid_actions.append(4 + i)  # Index starting from 4

        # If no valid actions (should never happen in normal gameplay), return [0]
        if not valid_actions:
            valid_actions.append(0)

        return valid_actions
    
    def _handle_fainted_pokemon(self, team, is_player_team=True):
        """Handle fainted Pokémon - returns effects messages and whether a switch happened"""
        effects = []
        switch_happened = False

        if team.active_pokemon.is_fainted():
            if is_player_team:
                effects.append(f"{team.active_pokemon.name}은(는) 쓰러졌다!")
            else:
                effects.append(f"상대 {team.active_pokemon.name}은(는) 쓰러졌다!")

            # Find next available Pokémon
            next_index = team.get_first_non_fainted()
            if next_index != -1:
                team.switch_pokemon(next_index)
                if is_player_team:
                    effects.append(f"플레이어가 {team.active_pokemon.name}을(를) 내보냈다!")
                else:
                    effects.append(f"상대가 {team.active_pokemon.name}을(를) 내보냈다!")
                switch_happened = True

        return effects, switch_happened
    
    def end_turn_effects(self):
        """Apply end-of-turn effects like status conditions"""
        effects = []

        # Player Pokémon status effects
        player_effects = self.player_team.active_pokemon.apply_status_turn_end()
        effects.extend(player_effects)

        # Opponent Pokémon status effects
        opponent_effects = self.opponent_team.active_pokemon.apply_status_turn_end()
        effects.extend(opponent_effects)

        # 지형 효과 적용
        if self.terrain:
            self.terrain['turns'] -= 1

            # 풀지형 체력 회복 효과
            if self.terrain['name'] == Terrain.GRASSY:
                for pokemon in self.player_team.pokemons + self.opponent_team.pokemons:
                    if not pokemon.is_fainted():
                        heal_amount = max(1, pokemon.stats['hp'] // 16)
                        old_hp = pokemon.current_hp
                        pokemon.current_hp = min(pokemon.stats['hp'], pokemon.current_hp + heal_amount)

                        if pokemon.current_hp > old_hp:
                            effects.append(f"{pokemon.name}은(는) 풀지형으로 체력을 회복했다! (+{heal_amount} HP)")

            # 지형 효과 종료 확인
            if self.terrain['turns'] <= 0:
                effects.append(f"{self.terrain['name']} 효과가 사라졌다!")
                self.terrain = None
            else:
                effects.append(f"{self.terrain['name']} 효과가 계속된다! ({self.terrain['turns']}턴 남음)")

        # Check if any Pokémon fainted due to status effects
        player_faint_effects, player_switched = self._handle_fainted_pokemon(self.player_team, True)
        effects.extend(player_faint_effects)

        opponent_faint_effects, opponent_switched = self._handle_fainted_pokemon(self.opponent_team, False)
        effects.extend(opponent_faint_effects)

        return effects, player_switched, opponent_switched