from typing import List, Literal
from context.battle_store import store
from utils.battle_logics.update_battle_pokemon import change_rank
from utils.battle_logics.update_environment import set_aura, set_weather, set_field, add_disaster
from p_models.battle_pokemon import BattlePokemon

SideType = Literal["my", "enemy"]

def apply_appearance(pokemon: BattlePokemon, side: SideType) -> List[str]:
    logs: List[str] = []
    ability = pokemon.base.ability
    if not ability or not ability.appear:
        return logs

    active_my = store.state["active_my"]
    active_enemy = store.state["active_enemy"]
    my_team = store.state["my_team"]
    enemy_team = store.state["enemy_team"]
    public_env = store.state["public_env"]
    update = store.update_pokemon
    add_log = store.add_log

    my_index = active_my if side == "my" else active_enemy
    opp_index = active_enemy if side == "my" else active_my
    my_pokemon = my_team[my_index] if side == "my" else enemy_team[my_index]
    opp_pokemon = enemy_team[opp_index] if side == "my" else my_team[opp_index]
    opp_side = "enemy" if side == "my" else "my"

    for effect in ability.appear:
        if effect == "weather_change":
            if ability.name == "가뭄":
                set_weather("쾌청")
                add_log(f"☀️ {pokemon.base.name}의 특성으로 날씨가 쾌청이 되었다!")
            elif ability.name == "잔비":
                set_weather("비")
                add_log(f"🌧️ {pokemon.base.name}의 특성으로 날씨가 비가 되었다!")
            elif ability.name == "눈퍼뜨리기":
                set_weather("싸라기눈")
                add_log(f"☃️ {pokemon.base.name}의 특성으로 날씨가 싸라기눈이 되었다!")
            elif ability.name == "모래날림":
                set_weather("모래바람")
                add_log(f"🏜️ {pokemon.base.name}의 특성으로 날씨가 모래바람이 되었다!")

        elif effect == "field_change":
            if ability.name == "일렉트릭메이커":
                set_field("일렉트릭필드")
                add_log(f"⚡️ {pokemon.base.name}의 특성으로 필드가 일렉트릭필드로 바뀌었다!")
            elif ability.name == "그래스메이커":
                set_field("그래스필드")
                add_log(f"🌱 {pokemon.base.name}의 특성으로 필드가 그래스필드로 바뀌었다!")
            elif ability.name == "미스트메이커":
                set_field("미스트필드")
                add_log(f"😶‍🌫️ {pokemon.base.name}의 특성으로 필드가 미스트필드로 바뀌었다!")
            elif ability.name == "사이코메이커":
                set_field("사이코필드")
                add_log(f"🔮 {pokemon.base.name}의 특성으로 필드가 사이코필드로 바뀌었다!")

        elif effect == "aura_change":
            if ability.name == "페어리오라":
                set_aura("페어리오라")
                add_log(f"😇 {pokemon.base.name}의 특성으로 페어리오라가 생겼다!")
            else:
                set_aura("다크오라")
                add_log(f"😈 {pokemon.base.name}의 특성으로 다크오라가 생겼다!")

        elif effect == "disaster":
            add_disaster(ability.name)
            add_log(f"🌋 {pokemon.base.name}의 특성으로 {ability.name} 효과가 발동했다!")

        elif effect == "rank_change":
            if ability.name == "위협" and not (opp_pokemon.base.ability and "intimidate_nullification" in (opp_pokemon.base.ability.util or [])):
                update(opp_side, opp_index, lambda p: change_rank(p, "attack", -1))
                add_log(f"🔃 {pokemon.base.name}의 등장으로 {opp_pokemon.base.name}의 공격력이 떨어졌다!")

            elif ability.name == "다운로드":
                if opp_pokemon.base.defense > opp_pokemon.base.sp_defense:
                    update(side, my_index, lambda p: change_rank(p, "spAttack", 1))
                    add_log(f"🔃 상대의 특수방어가 낮아서 {pokemon.base.name}의 특수공격이 상승했다!")
                elif opp_pokemon.base.defense < opp_pokemon.base.sp_defense:
                    update(side, my_index, lambda p: change_rank(p, "attack", 1))
                    add_log(f"🔃 상대의 방어가 낮아서 {pokemon.base.name}의 공격이 상승했다!")
                else:
                    update(side, my_index, lambda p: change_rank(p, "spAttack", 1))
                    add_log(f"🔃 상대의 방어와 특수방어가 같아서 {pokemon.base.name}의 특수공격이 상승했다!")

            elif ability.name == "고대활성" and public_env.weather == "쾌청":
                stats = {
                    "attack": my_pokemon.base.attack,
                    "defense": my_pokemon.base.defense,
                    "spAttack": my_pokemon.base.sp_attack,
                    "spDefense": my_pokemon.base.sp_defense,
                    "speed": my_pokemon.base.speed,
                }
                best_stat = max(stats, key=stats.get)
                update(side, my_index, lambda p: change_rank(p, best_stat, 1))
                add_log(f"🔃 {pokemon.base.name}의 {best_stat} 능력이 상승했다!")

            elif ability.name == "쿼크차지" and public_env.field == "일렉트릭필드":
                stats = {
                    "attack": my_pokemon.base.attack,
                    "defense": my_pokemon.base.defense,
                    "spAttack": my_pokemon.base.sp_attack,
                    "spDefense": my_pokemon.base.sp_defense,
                    "speed": my_pokemon.base.speed,
                }
                best_stat = max(stats, key=stats.get)
                update(side, my_index, lambda p: change_rank(p, best_stat, 1))
                add_log(f"🔃 {pokemon.base.name}의 {best_stat} 능력이 상승했다!")

        elif effect == "heal":
            add_log(f"➕ {pokemon.base.name}이 회복 효과를 발동했다!")

        elif effect == "ability_change":
            new_ability = opp_pokemon.base.ability
            update(side, my_index, lambda p: p.copy_with(ability=new_ability))
            add_log(f"➕ {pokemon.base.name}의 특성이 {new_ability.name if new_ability else '???'}으로 변화했다!")
            if new_ability and new_ability.appear:
                apply_appearance(my_pokemon, side)

    update(side, my_index, lambda p: p.copy_with(is_first_turn=True))
    return logs