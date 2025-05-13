from typing import Dict, Optional, Literal
import random

from context.battle_store import BattleStoreState
from context.battle_store import store
from p_models.battle_pokemon import BattlePokemon
from p_models.move_info import MoveInfo
from utils.battle_logics.rank_effect import calculate_rank_effect

async def calculate_order(player_move: Optional[MoveInfo], ai_move: Optional[MoveInfo]) -> Literal["my", "enemy"]:
    state: BattleStoreState = store.get_state()
    public_env = state["public_env"]
    my_team = state["my_team"]
    active_my = state["active_my"]
    enemy_team = state["enemy_team"]
    active_enemy = state["active_enemy"]
    my_pokemon = my_team[active_my]
    opponent_pokemon = enemy_team[active_enemy]

    # 우선도 조정: 힐링시프트, 짓궂은마음, 질풍날개 등
    def boost_priority(pokemon: BattlePokemon, move: Optional[MoveInfo]):
        if pokemon.base.ability and move:
            if pokemon.base.ability.name == '힐링시프트' and any(e.heal for e in move.effects):
                move["priority"] = move.priority + 3
            elif pokemon.base.ability.name == '짓궂은마음' and move.category == "변화":
                move["priority"] = move.priority + 1
            elif pokemon.base.ability.name == '질풍날개' and move.type == "비행" and pokemon.current_hp == pokemon.base.hp:
                move["priority"] = 1

    boost_priority(my_pokemon, player_move)
    boost_priority(opponent_pokemon, ai_move)

    # 스피드 계산
    def calculate_speed(pokemon: BattlePokemon):
        speed = pokemon.base.speed * calculate_rank_effect(pokemon.rank['speed'])
        
        if "마비" in pokemon.status:
            speed *= 0.5
            print(f"{pokemon.base.name}가 마비로 인해 스피드가 절반으로 감소: {speed}")
            
        ability = pokemon.base.ability.name if pokemon.base.ability else ""
        if ability in ['곡예', '엽록소', '쓱쓱', '눈치우기', '모래헤치기']:
            if (ability == '엽록소' and public_env.weather != '쾌청') or \
                (ability == '쓱쓱' and public_env.weather != '비') or \
                (ability == '눈치우기' and public_env.weather != '싸라기눈') or \
                (ability == '모래헤치기' and public_env.weather != '모래바람'):
                print(f"{pokemon.base.name}의 {ability} 특성이 발동되지 않음")
                return speed
            speed *= 2
            print(f"{pokemon.base.name}의 {ability} 특성으로 인해 스피드가 2배로 증가: {speed}")
            
        return speed

    my_speed = calculate_speed(my_pokemon)
    opponent_speed = calculate_speed(opponent_pokemon)

    print(f"내 포켓몬({my_pokemon.base.name})의 최종 스피드: {my_speed}")
    print(f"상대 포켓몬({opponent_pokemon.base.name})의 최종 스피드: {opponent_speed}")

    if public_env.room == "트릭룸":
        my_speed *= -1
        opponent_speed *= -1
        print("트릭룸 효과로 스피드가 반전되었습니다!")
        print(f"내 포켓몬({my_pokemon.base.name})의 트릭룸 적용 후 스피드: {my_speed}")
        print(f"상대 포켓몬({opponent_pokemon.base.name})의 트릭룸 적용 후 스피드: {opponent_speed}")

    # 기본 선공 판단
    speed_diff = my_speed - opponent_speed
    if speed_diff == 0:
        speed_diff = random.random() - 0.5
        print("스피드가 같아 랜덤으로 결정됩니다!")
    who_is_first = "my" if speed_diff >= 0 else "enemy"
    print(f"스피드 차이: {speed_diff}, 선공: {who_is_first}")

    # 그래스슬라이더 예외
    if player_move and player_move.name == "그래스슬라이더" and public_env.field != "그래스필드":
        player_move.priority = 0
        print("그래스슬라이더의 우선도가 0으로 변경되었습니다!")
    if ai_move and ai_move.name == "그래스슬라이더" and public_env.field != "그래스필드":
        ai_move.priority = 0
        print("그래스슬라이더의 우선도가 0으로 변경되었습니다!")

    # 우선도 비교
    def priority(move: MoveInfo): return move.priority if move else 0

    if player_move and ai_move:
        player_priority = priority(player_move)
        ai_priority = priority(ai_move)
        print(f"내 기술({player_move.name})의 우선도: {player_priority}")
        print(f"상대 기술({ai_move.name})의 우선도: {ai_priority}")
        
        if player_priority > ai_priority:
            who_is_first = "my"
            print("우선도로 인해 내가 선공합니다!")
        elif player_priority < ai_priority:
            who_is_first = "enemy"
            print("우선도로 인해 상대가 선공합니다!")
        else:
            who_is_first = "my" if speed_diff >= 0 else "enemy"
            print("우선도가 같아 스피드로 결정됩니다!")
    elif ai_move:
        who_is_first = "my" if priority(ai_move) < 0 else "enemy"
    elif player_move:
        who_is_first = "enemy" if priority(player_move) < 0 else "my"

    store.add_log(f"🦅 {who_is_first}의 선공!")
    print(f"{who_is_first}의 선공!")
    return who_is_first