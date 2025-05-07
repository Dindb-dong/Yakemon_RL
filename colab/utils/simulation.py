"""배틀 시뮬레이션 유틸리티 모듈"""

import random
import time
from tqdm import tqdm
from ..p_models.team import PokemonTeam
from ..p_models.types import Terrain, TYPE_NAMES
from ..battle.battle import PokemonBattle
from ..p_models.moves import get_move_priority
from ..p_models.templates import POKEMON_TEMPLATES, create_pokemon_from_template
from ..rl.environment import create_pokemon_teams

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

def print_pokemon_info(pokemon):
    """포켓몬 정보 출력"""
    print(f"{pokemon.name} (HP: {pokemon.current_hp}/{pokemon.stats['hp']})")

    # 타입 정보
    types_str = ', '.join([type_name for type_name, type_id in TYPE_NAMES.items() if type_id in pokemon.types])
    print(f"Types: {types_str}")

    # 기술 목록
    print("Moves:")
    for i, move in enumerate(pokemon.moves):
        priority = get_move_priority(move)
        priority_str = ""
        if priority != 0:
            priority_str = f" (우선도: {priority})"

        critical_str = ""
        if move.effects and 'critical_rate' in move.effects:
            critical_str = f" (치명타율↑: {move.effects['critical_rate']})"

        print(f"  {i+1}. {move.name} (PP: {move.pp}/{move.max_pp}){priority_str}{critical_str}")

    # 상태이상
    if pokemon.status_condition:
        print(f"Status: {pokemon.status_condition}")

    # 치명타 단계 표시
    if pokemon.critical_hit_stage > 0:
        print(f"Critical Hit Stage: {pokemon.critical_hit_stage}")

    # 능력치 변화
    stat_changes = []
    for stat, value in pokemon.stat_stages.items():
        if value != 0:
            direction = "↑" if value > 0 else "↓"
            stat_changes.append(f"{stat}{direction}{abs(value)}")

    if stat_changes:
        print(f"Stat Changes: {', '.join(stat_changes)}")

    print()

def print_battle_state(battle):
    """배틀 상태 출력"""
    print("\n" + "="*50)
    print(f"Turn {battle.turn}")
    print("="*50)

    # 지형 효과 표시
    if battle.terrain:
        print(f"Active Terrain: {battle.terrain['name']} ({battle.terrain['turns']} turns left)")

    print("Player's Pokemon:")
    print_pokemon_info(battle.player_team.active_pokemon)

    print("Opponent's Pokemon:")
    print_pokemon_info(battle.opponent_team.active_pokemon)
    print("-"*50)

def format_result(result, actor_pokemon, target_pokemon):
    """결과 메시지 포맷팅"""
    if not result.get("success", False):
        return result.get("message", "행동 실패!")

    message = f"{actor_pokemon.name}의 "

    # 기술명 추가 (결과에 없을 경우 대비)
    move_name = result.get("move_name", "기술")
    message += f"{move_name}! "

    # 데미지가 있는 경우
    if "damage" in result and result["damage"] > 0:
        message += f"\n{target_pokemon.name}에게 {result['damage']}의 데미지! "
        message += f"({result['before_hp']} -> {result['after_hp']})"

        # 타입 상성 메시지
        if "effectiveness" in result and result["effectiveness"]:
            message += f"\n{result['effectiveness']}"

    # 효과 메시지
    if "effects" in result and result["effects"]:
        for effect in result["effects"]:
            message += f"\n{effect}"

    # 기절 메시지
    if result.get("fainted", False):
        message += f"\n{target_pokemon.name}은(는) 쓰러졌다!"

    return message

def ai_battle_simulation(num_battles=3):
    """향상된 AI 간 배틀 시뮬레이션 수행"""
    for battle_num in range(num_battles):
        print("\n\n" + "*"*70)
        print(f"Battle Simulation #{battle_num+1}")
        print("*"*70)

        # 팀 생성
        player_team, opponent_team = create_pokemon_teams()
        battle = PokemonBattle(player_team, opponent_team)

        # 초기 상태 출력
        print("Battle Start!")
        print_battle_state(battle)

        # 배틀 시작
        max_turns = 50  # 무한 루프 방지

        for turn in range(max_turns):
            # 배틀 종료 확인
            if battle.is_battle_over():
                break

            # 랜덤으로 지형 효과 설정 (5% 확률)
            if random.random() < 0.05 and not battle.terrain:
                terrain_types = [Terrain.GRASSY, Terrain.ELECTRIC, Terrain.PSYCHIC, Terrain.MISTY]
                selected_terrain = random.choice(terrain_types)
                duration = random.randint(3, 5)
                message = battle.set_terrain(selected_terrain, duration)
                print(f"\nTerrain Effect: {message}")

            # 랜덤으로 치명타 단계 상승 (10% 확률)
            if random.random() < 0.1:
                pokemon = battle.player_team.active_pokemon
                if pokemon.critical_hit_stage < 3:  # 최대 3단계까지
                    pokemon.critical_hit_stage += 1
                    print(f"\n{pokemon.name}의 치명타 확률이 상승했다! (단계: {pokemon.critical_hit_stage})")

            # 플레이어 행동 (랜덤 AI)
            valid_moves = battle.player_team.active_pokemon.get_valid_moves()
            valid_switches = battle.player_team.get_valid_switches()

            # 80% 확률로 기술 사용, 20% 확률로 교체 (교체 가능하면)
            if valid_switches and random.random() < 0.2:
                action_type = "switch"
                action_index = random.choice(valid_switches)
                print(f"Player chooses to switch to {battle.player_team.pokemons[action_index].name}")
            else:
                action_type = "move"
                action_index = random.choice(valid_moves)
                move = battle.player_team.active_pokemon.moves[action_index]

                # 우선권 표시
                priority = get_move_priority(move)
                if priority != 0:
                    priority_text = "높은" if priority > 0 else "낮은"
                    print(f"Player chooses move: {move.name} ({priority_text} 우선도: {priority})")
                else:
                    print(f"Player chooses move: {move.name}")

            # 행동 실행
            results = battle.player_action(action_type, action_index)

            # 결과 출력
            for item in results:
                if isinstance(item, dict):
                    actor = item.get("actor")
                    result = item.get("result", {})

                    if actor == "player":
                        # 플레이어 행동 결과
                        if action_type == "move":
                            move = battle.player_team.active_pokemon.moves[action_index]
                            result["move_name"] = move.name

                        message = format_result(
                            result,
                            battle.player_team.active_pokemon,
                            battle.opponent_team.active_pokemon
                        )
                        print(f"\nPlayer Action: {message}")

                    elif actor == "opponent":
                        # 상대 행동 결과
                        message = format_result(
                            result,
                            battle.opponent_team.active_pokemon,
                            battle.player_team.active_pokemon
                        )
                        print(f"\nOpponent Action: {message}")

                    elif actor == "end_turn":
                        # 턴 종료 효과
                        if "effects" in item:
                            print("\nEnd of Turn Effects:")
                            for effect in item["effects"]:
                                print(f"  {effect}")

                    elif actor == "terrain":
                        # 지형 효과 메시지
                        if "message" in item:
                            print(f"\nTerrain Effect: {item['message']}")

            # 턴 종료 후 상태 출력
            print_battle_state(battle)

            # 잠시 지연 (출력을 읽기 쉽게)
            time.sleep(0.5)

        # 승자 출력
        winner = battle.get_winner()
        if winner:
            print(f"\nBattle #{battle_num+1} Winner: {winner.upper()}")
        else:
            print(f"\nBattle #{battle_num+1} ended in a draw or reached max turns")

        print("\n건너뛰려면 Enter 키를 누르세요...")
        input()

def battle_statistics(num_battles=100):
    """다수의 배틀에 대한 통계 분석 수행"""
    print(f"{num_battles}회의 배틀 시뮬레이션 통계 분석 중...")

    # 통계 변수
    player_wins = 0
    opponent_wins = 0
    total_turns = 0
    total_critical_hits = 0
    terrain_activations = 0
    priority_move_counts = 0
    type_effectiveness_counts = {
        "효과가 뛰어났다!": 0,  # 효과적
        "효과가 별로인 듯하다...": 0,  # 효과가 별로인
        "효과가 없는 것 같다...": 0   # 효과 없음
    }

    # 디버깅 정보
    errors = []
    struggle_usage = 0

    # 기술별 사용 횟수
    move_usage = {}

    # 포켓몬별 승률
    pokemon_wins = {}
    pokemon_appearances = {}

    for battle_num in tqdm(range(num_battles)):
        try:
            # 팀 생성
            player_team, opponent_team = create_pokemon_teams()
            battle = PokemonBattle(player_team, opponent_team)

            # 등장한 포켓몬 기록
            for pokemon in player_team.pokemons + opponent_team.pokemons:
                if pokemon.name not in pokemon_appearances:
                    pokemon_appearances[pokemon.name] = 0
                pokemon_appearances[pokemon.name] += 1

            # 배틀 시작
            max_turns = 100  # 무한 루프 방지

            for turn in range(max_turns):
                # 배틀 종료 확인
                if battle.is_battle_over():
                    break

                # 지형 효과 설정 (5% 확률)
                if random.random() < 0.05 and not battle.terrain:
                    terrain_types = [Terrain.GRASSY, Terrain.ELECTRIC, Terrain.PSYCHIC, Terrain.MISTY]
                    selected_terrain = random.choice(terrain_types)
                    duration = random.randint(3, 5)
                    battle.set_terrain(selected_terrain, duration)
                    terrain_activations += 1

                # 플레이어 행동 (랜덤 AI)
                valid_moves = battle.player_team.active_pokemon.get_valid_moves()
                valid_switches = battle.player_team.get_valid_switches()

                # 몸부림치기 체크
                for idx in valid_moves:
                    if idx < len(battle.player_team.active_pokemon.moves):
                        move = battle.player_team.active_pokemon.moves[idx]
                        if move.name == "몸부림치기":
                            struggle_usage += 1

                # 80% 확률로 기술 사용, 20% 확률로 교체 (교체 가능하면)
                if valid_switches and random.random() < 0.2:
                    action_type = "switch"
                    action_index = random.choice(valid_switches)
                else:
                    action_type = "move"
                    if not valid_moves:
                        # 유효한 기술이 없으면 로그 기록
                        error_info = f"배틀 #{battle_num}, 턴 {turn}: 유효한 기술이 없음"
                        errors.append(error_info)
                        # 포켓몬의 현재 기술 정보
                        pokemon = battle.player_team.active_pokemon
                        error_info += f"\n포켓몬: {pokemon.name}, 기술 수: {len(pokemon.moves)}"
                        for i, move in enumerate(pokemon.moves):
                            error_info += f"\n기술 {i}: {move.name} (PP: {move.pp}/{move.max_pp})"
                        errors.append(error_info)

                        # 몸부림치기 사용
                        valid_moves = battle.player_team.active_pokemon.get_valid_moves()

                    action_index = random.choice(valid_moves)

                    # 기술 사용 전 안전 확인
                    if action_index >= len(battle.player_team.active_pokemon.moves):
                        error_info = f"배틀 #{battle_num}, 턴 {turn}: 잘못된 기술 인덱스 {action_index} (기술 수: {len(battle.player_team.active_pokemon.moves)})"
                        errors.append(error_info)

                        # 유효한 기술 다시 가져오기
                        valid_moves = battle.player_team.active_pokemon.get_valid_moves()
                        action_index = valid_moves[0]

                    # 기술 사용 횟수 증가
                    move_name = battle.player_team.active_pokemon.moves[action_index].name
                    if move_name not in move_usage:
                        move_usage[move_name] = 0
                    move_usage[move_name] += 1

                    # 우선권 기술 체크
                    move = battle.player_team.active_pokemon.moves[action_index]
                    if get_move_priority(move) != 0:
                        priority_move_counts += 1

                # 행동 실행
                try:
                    results = battle.player_action(action_type, action_index)
                except Exception as e:
                    error_info = f"배틀 #{battle_num}, 턴 {turn}: 행동 실행 예외 발생: {str(e)}"
                    error_info += f"\n행동 유형: {action_type}, 인덱스: {action_index}"
                    error_info += f"\n포켓몬: {battle.player_team.active_pokemon.name}, 기술 수: {len(battle.player_team.active_pokemon.moves)}"
                    errors.append(error_info)
                    # 배틀 중단
                    break

                # 결과 분석
                for item in results:
                    if isinstance(item, dict):
                        result = item.get("result", {})

                        # 치명타 확인
                        if "effects" in result:
                            for effect in result["effects"]:
                                if "급소에 맞았다!" in effect:
                                    total_critical_hits += 1

                        # 타입 상성 확인
                        if "effectiveness" in result and result["effectiveness"]:
                            effectiveness = result["effectiveness"]
                            if effectiveness in type_effectiveness_counts:
                                type_effectiveness_counts[effectiveness] += 1

            # 승자 확인
            winner = battle.get_winner()
            if winner == "player":
                player_wins += 1

                # 이긴 포켓몬 통계
                for pokemon in player_team.pokemons:
                    if pokemon.name not in pokemon_wins:
                        pokemon_wins[pokemon.name] = 0
                    pokemon_wins[pokemon.name] += 1
            elif winner == "opponent":
                opponent_wins += 1

                # 이긴 포켓몬 통계
                for pokemon in opponent_team.pokemons:
                    if pokemon.name not in pokemon_wins:
                        pokemon_wins[pokemon.name] = 0
                    pokemon_wins[pokemon.name] += 1

            # 전체 턴 수 누적
            total_turns += battle.turn

        except Exception as e:
            # 예외 발생 시 오류 정보 기록
            error_info = f"배틀 #{battle_num}: 예외 발생: {str(e)}"
            errors.append(error_info)

    # 통계 결과 출력
    print("\n" + "="*50)
    print(f"배틀 시뮬레이션 통계 결과 (총 {num_battles}회)")
    print("="*50)

    # 승률
    completed_battles = player_wins + opponent_wins
    if completed_battles > 0:
        print(f"완료된 배틀: {completed_battles}회")
        print(f"플레이어 승리: {player_wins}회 ({player_wins/completed_battles*100:.1f}%)")
        print(f"상대방 승리: {opponent_wins}회 ({opponent_wins/completed_battles*100:.1f}%)")
    else:
        print("완료된 배틀이 없습니다.")

    # 평균 턴 수
    if completed_battles > 0:
        avg_turns = total_turns / completed_battles
        print(f"평균 턴 수: {avg_turns:.1f}")

    # 특수 효과 통계
    print(f"총 치명타 발생: {total_critical_hits}회")
    print(f"지형 효과 발생: {terrain_activations}회")
    print(f"우선권 기술 사용: {priority_move_counts}회")
    print(f"몸부림치기 사용: {struggle_usage}회")

    # 타입 상성 통계
    print("\n타입 상성 통계:")
    for effectiveness, count in type_effectiveness_counts.items():
        print(f"  {effectiveness}: {count}회")

    # 가장 많이 사용된 기술 Top 5
    if move_usage:
        print("\n가장 많이 사용된 기술 Top 5:")
        sorted_moves = sorted(move_usage.items(), key=lambda x: x[1], reverse=True)
        for i, (move_name, count) in enumerate(sorted_moves[:5]):
            print(f"  {i+1}. {move_name}: {count}회")

    # 포켓몬별 승률 Top 5
    if pokemon_wins:
        print("\n승률이 높은 포켓몬 Top 5:")
        pokemon_win_rates = {}
        for pokemon_name, wins in pokemon_wins.items():
            if pokemon_name in pokemon_appearances and pokemon_appearances[pokemon_name] > 0:
                appearances = pokemon_appearances[pokemon_name]
                win_rate = wins / appearances * 100
                pokemon_win_rates[pokemon_name] = (win_rate, wins, appearances)

        if pokemon_win_rates:
            sorted_win_rates = sorted(pokemon_win_rates.items(), key=lambda x: x[1][0], reverse=True)
            for i, (pokemon_name, (win_rate, wins, appearances)) in enumerate(sorted_win_rates[:5]):
                print(f"  {i+1}. {pokemon_name}: {win_rate:.1f}% ({wins}/{appearances})")

    # 오류 정보 출력
    if errors:
        print("\n" + "="*50)
        print(f"발생한 오류 ({len(errors)}건):")
        print("="*50)
        for i, error in enumerate(errors[:10]):  # 처음 10개만 표시
            print(f"{i+1}. {error}")

        if len(errors) > 10:
            print(f"... 외 {len(errors) - 10}건의 오류") 