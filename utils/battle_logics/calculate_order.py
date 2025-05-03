from typing import Optional, Literal
import random

from context.battle_store import store
from utils.battle_logics.rank_effect import calculate_rank_effect

def calculate_order(player_move: Optional[dict], ai_move: Optional[dict]) -> Literal["my", "enemy"]:
    state = store.get_state()
    public_env = state["public_env"]
    my_team = state["my_team"]
    active_my = state["active_my"]
    enemy_team = state["enemy_team"]
    active_enemy = state["active_enemy"]
    my_pokemon = my_team[active_my]
    opponent_pokemon = enemy_team[active_enemy]

    # 우선도 조정: 힐링시프트, 짓궂은마음, 질풍날개 등
    def boost_priority(pokemon, move):
        if pokemon.base.ability and move:
            if pokemon.base.ability.name == '힐링시프트' and any(e.get("heal") for e in move.get("effects", [])):
                move["priority"] = move.get("priority", 0) + 3
            elif pokemon.base.ability.name == '짓궂은마음' and move.get("category") == "변화":
                move["priority"] = move.get("priority", 0) + 1
            elif pokemon.base.ability.name == '질풍날개' and move.get("type") == "비행" and pokemon.current_hp == pokemon.base.hp:
                move["priority"] = 1

    boost_priority(my_pokemon, player_move)
    boost_priority(opponent_pokemon, ai_move)

    # 스피드 계산
    def calculate_speed(pokemon):
        speed = pokemon.base.speed * calculate_rank_effect(pokemon.rank.speed)
        if "마비" in pokemon.status:
            speed *= 0.5
        ability = pokemon.base.ability.name if pokemon.base.ability else ""
        if ability in ['곡예', '엽록소', '쓱쓱', '눈치우기', '모래헤치기']:
            if (ability == '엽록소' and public_env.weather != '쾌청') or \
               (ability == '쓱쓱' and public_env.weather != '비') or \
               (ability == '눈치우기' and public_env.weather != '싸라기눈') or \
               (ability == '모래헤치기' and public_env.weather != '모래바람'):
                return speed
            speed *= 2
        return speed

    my_speed = calculate_speed(my_pokemon)
    opponent_speed = calculate_speed(opponent_pokemon)

    if public_env.room == "트릭룸":
        my_speed *= -1
        opponent_speed *= -1

    # 기본 선공 판단
    speed_diff = my_speed - opponent_speed
    if speed_diff == 0:
        speed_diff = random.random() - 0.5
    who_is_first = "my" if speed_diff >= 0 else "enemy"

    # 그래스슬라이더 예외
    if player_move and player_move.get("name") == "그래스슬라이더" and public_env.field != "그래스필드":
        player_move["priority"] = 0
    if ai_move and ai_move.get("name") == "그래스슬라이더" and public_env.field != "그래스필드":
        ai_move["priority"] = 0

    # 우선도 비교
    def priority(move): return move.get("priority", 0) if move else 0

    if player_move and ai_move:
        if priority(player_move) > priority(ai_move):
            who_is_first = "my"
        elif priority(player_move) < priority(ai_move):
            who_is_first = "enemy"
        else:
            who_is_first = "my" if speed_diff >= 0 else "enemy"
    elif ai_move:
        who_is_first = "my" if priority(ai_move) < 0 else "enemy"
    elif player_move:
        who_is_first = "enemy" if priority(player_move) < 0 else "my"

    store.add_log(f"🦅 {who_is_first}의 선공!")
    print(f"{who_is_first}의 선공!")
    return who_is_first