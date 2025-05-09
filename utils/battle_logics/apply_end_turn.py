from context.battle_store import store
from context.duration_store import duration_store
from utils.battle_logics.update_battle_pokemon import (
    add_status, change_hp, change_rank, remove_status, reset_state, set_locked_move
)
from utils.battle_logics.apply_none_move_damage import apply_status_condition_damage
from utils.battle_logics.switch_pokemon import MAIN_STATUS_CONDITION
from utils.battle_logics.update_environment import set_weather, set_field, set_screen
import random


def apply_end_turn_effects():
    state = store.get_state()
    my_team = state["my_team"]
    enemy_team = state["enemy_team"]
    active_my = state["active_my"]
    active_enemy = state["active_enemy"]
    public_env = state["public_env"]
    my_env = state["my_env"]
    enemy_env = state["enemy_env"]

    my_active = my_team[active_my]
    enemy_active = enemy_team[active_enemy]

    # === 필드 효과 ===
    for i, pokemon in enumerate([my_active, enemy_active]):
        side = "my" if i == 0 else "enemy"
        if public_env.field == "그래스필드":
            if "비행" not in pokemon.base.types and pokemon.position != "하늘" and pokemon.current_hp > 0:
                heal = pokemon.base.hp // 16
                store.update_pokemon(side, active_my if i == 0 else active_enemy, lambda p: change_hp(p, heal))
                store.add_log(f"➕ {pokemon.base.name}은/는 그래스필드로 회복했다!")

    # === 상태이상 및 날씨 효과 ===
    for i, pokemon in enumerate([my_active, enemy_active]):
        side = "my" if i == 0 else "enemy"
        opponent_side = "enemy" if side == "my" else "my"
        active_index = active_my if side == "my" else active_enemy
        team = my_team if side == "my" else enemy_team
        opponent_team = enemy_team if side == "my" else my_team
        active_opponent = active_enemy if side == "my" else active_my

        for status in ["화상", "맹독", "독", "조이기"]:
            if status in pokemon.status:
                updated = apply_status_condition_damage(pokemon, status)
                store.update_pokemon(side, active_index, lambda p: updated)

        if "씨뿌리기" in pokemon.status and (not (pokemon.base.ability and pokemon.base.ability.name == "매직가드")):
            damage = pokemon.base.hp // 8
            store.update_pokemon(side, active_index, lambda p: change_hp(p, -damage))
            if opponent_team[active_opponent].current_hp > 0:
                store.update_pokemon(opponent_side, active_opponent, lambda p: change_hp(p, damage))
            store.add_log(f"🌱 {opponent_team[active_opponent].base.name}은 씨뿌리기로 회복했다!")
            store.add_log(f"🌱 {pokemon.base.name}은 씨뿌리기의 피해를 입었다!")

        if public_env.weather == "모래바람":
            immune_abilities = ["모래숨기", "모래의힘"]
            immune_types = ["바위", "땅", "강철"]
            immune = (
                pokemon.base.ability and pokemon.base.ability.name in immune_abilities
            ) or any(t in immune_types for t in pokemon.base.types)
            if not immune:
                damage = pokemon.base.hp // 16
                store.update_pokemon(side, active_index, lambda p: change_hp(p, -damage))
                store.add_log(f"🌪️ {pokemon.base.name}은 모래바람에 의해 피해를 입었다!")

    # === 지속형 효과 종료 처리 ===
    expired = duration_store.decrement_turns()
    for i, side in enumerate(["my", "enemy"]):
        active_index = active_my if side == "my" else active_enemy
        for effect_name in expired[side]:
            store.update_pokemon(side, active_index, lambda p: remove_status(p, effect_name))
            store.add_log(f"🏋️‍♂️ {'내' if side == 'my' else '상대'} 포켓몬의 {effect_name} 상태가 해제되었다!")

    if public_env.weather and public_env.weather in expired["public"]:
        set_weather(None)
        store.add_log(f"날씨({public_env.weather})의 효과가 사라졌다!")

    if public_env.field and public_env.field in expired["public"]:
        set_field(None)
        store.add_log(f"필드({public_env.field})의 효과가 사라졌다!")

    if my_env.screen and my_env.screen in expired["myEnv"]:
        set_screen("my", None)
        store.add_log(f"내 필드의 {my_env.screen}이/가 사라졌다!")

    if enemy_env.screen and enemy_env.screen in expired["enemyEnv"]:
        set_screen("enemy", None)
        store.add_log(f"상대 필드의 {enemy_env.screen}이/가 사라졌다!")

    # === 특성 효과 처리 ===
    for i, pokemon in enumerate([my_active, enemy_active]):
        side = "my" if i == 0 else "enemy"
        active_index = active_my if side == "my" else active_enemy
        ability_name = pokemon.base.ability.name if pokemon.base.ability else None

        if ability_name == "포이즌힐":
            if "독" in pokemon.status:
                store.update_pokemon(side, active_index, lambda p: change_hp(p, p.base.hp * 3 // 16))
                store.add_log(f"➕ {pokemon.base.name}은 포이즌힐로 체력을 회복했다!")
            elif "맹독" in pokemon.status:
                store.update_pokemon(side, active_index, lambda p: change_hp(p, p.base.hp * 22 // 96))
                store.add_log(f"➕ {pokemon.base.name}은 포이즌힐로 체력을 회복했다!")

        if ability_name == "아이스바디" and public_env.weather == "싸라기눈":
            store.update_pokemon(side, active_index, lambda p: change_hp(p, p.base.hp // 16))
            store.add_log(f"➕ {pokemon.base.name}은 아이스바디로 체력을 회복했다!")

        if ability_name == "가속":
            store.update_pokemon(side, active_index, lambda p: change_rank(p, "speed", 1))
            store.add_log(f"🦅 {pokemon.base.name}의 가속 특성 발동!")

        if ability_name == "변덕쟁이":
            stats = ["attack", "spAttack", "defense", "spDefense", "speed"]
            up = random.choice(stats)
            down = random.choice(stats)
            store.update_pokemon(side, active_index, lambda p: change_rank(p, up, 2))
            store.update_pokemon(side, active_index, lambda p: change_rank(p, down, -1))
            store.add_log(f"🦅 {pokemon.base.name}의 변덕쟁이 특성 발동!")

        if ability_name == "선파워" and public_env.weather == "쾌청":
            store.update_pokemon(side, active_index, lambda p: change_hp(p, -p.base.hp // 16))
            store.add_log(f"🦅 {pokemon.base.name}의 선파워 특성 발동!")

        if ability_name == "탈피" and any(s in MAIN_STATUS_CONDITION for s in pokemon.status):
            for s in pokemon.status:
                if s in MAIN_STATUS_CONDITION:
                    store.update_pokemon(side, active_index, lambda p: remove_status(p, s))
            store.add_log(f"🦅 {pokemon.base.name}의 탈피 특성 발동!")

    # === 상태 초기화 및 고정기술 처리 ===
    for i, side in enumerate(["my", "enemy"]):
        active = active_my if side == "my" else active_enemy
        team = my_team if side == "my" else enemy_team
        store.update_pokemon(side, active, lambda p: reset_state(p))
        if team[active].locked_move and team[active].locked_move_turn == 0:
            store.update_pokemon(side, active, lambda p: set_locked_move(p, None))
            store.add_log(f"{team[active].base.name}은 지쳐서 혼란에 빠졌다..!")
            store.update_pokemon(side, active, lambda p: add_status(p, "혼란", side))