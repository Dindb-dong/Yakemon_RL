from typing import Tuple, Optional, List
from p_models.battle_pokemon import BattlePokemon
from context.battle_store import store
from utils.type_relation import calculate_type_effectiveness
from p_models.types import WeatherType

def apply_trap_damage(pokemon: BattlePokemon, trap: List[str]) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    if not pokemon or not pokemon.base:
        return None, None, None

    damage = 0
    log = None
    status_condition = ""

    types = pokemon.base.types
    ability_name = pokemon.base.ability.name if pokemon.base.ability else None

    if ability_name != "매직가드":
        for item in trap:
            if item == "스텔스록":
                multiplier = calculate_type_effectiveness("바위", types)
                damage += int(pokemon.base.hp * 0.125 * multiplier)
                if damage:
                    log = f"{pokemon.base.name} 은 {item}의 피해를 입었다! {pokemon.current_hp}에서 {pokemon.current_hp - damage}로 변경"

            elif item == "끈적끈적네트":
                if "비행" in types or ability_name == "부유":
                    log = "끈적끈적네트는 영향을 주지 않았다!"
                else:
                    status_condition = "끈적끈적네트"
                    log = "끈적끈적네트를 밟았다!"

            elif item == "독압정":
                if "비행" in types or ability_name == "부유" or "강철" in types or "독" in types:
                    log = "독압정은 영향을 주지 않았다!"
                elif "독" in types:
                    status_condition = "독압정 제거"
                    log = "독압정은 제거됐다!"
                else:
                    status_condition = "독"
                    log = f"{item}이 {pokemon.base.name}에게 {status_condition}을 유발했다!"

            elif item == "맹독압정":
                if "비행" in types or "고스트" in types or "강철" in types:
                    log = "맹독압정은 영향을 주지 않았다!"
                elif "독" in types:
                    status_condition = "맹독압정 제거"
                    log = "맹독압정은 제거됐다!"
                else:
                    status_condition = "맹독"
                    log = f"{item}이 {pokemon.base.name}에게 {status_condition}을 유발했다!"

            elif item.startswith("압정뿌리기"):
                if "비행" in types or ability_name == "부유":
                    log = "압정뿌리기는 효과가 없었다!"
                else:
                    ratio = {"압정뿌리기": 1/8, "압정뿌리기2": 1/6, "압정뿌리기3": 1/4}.get(item, 1/8)
                    spike_damage = int(pokemon.base.hp * ratio)
                    if spike_damage > 0:
                        damage += spike_damage
                        log = f"{pokemon.base.name}은(는) {item}의 피해를 입었다! {pokemon.current_hp}에서 {pokemon.current_hp - damage}로 변경"

    return damage, log, status_condition


def apply_weather_damage(pokemon: BattlePokemon, weather: WeatherType) -> BattlePokemon:
    if not pokemon or not pokemon.base:
        return pokemon

    add_log = store.add_log
    damage = 0
    types = pokemon.base.types
    ability_name = pokemon.base.ability.name if pokemon.base.ability else None

    if ability_name != "매직가드":
        if weather == "모래바람" and not any(t in types for t in ["바위", "강철", "땅"]) \
          and ability_name not in ["모래헤치기", "모래숨기", "모래의힘"]:
            damage = int(pokemon.base.hp * 0.125)
            add_log(f"{pokemon.base.name}은 모래바람에 의해 피해를 입었다!")

    return pokemon.copy_with(current_hp=max(0, pokemon.current_hp - damage))


def apply_recoil_damage(pokemon: BattlePokemon, recoil: float, applied_damage: int) -> BattlePokemon:
    if not pokemon or not pokemon.base:
        return pokemon

    add_log = store.add_log
    ability_name = pokemon.base.ability.name if pokemon.base.ability else None
    damage = 0

    if ability_name not in ["매직가드", "돌머리"]:
        damage = int(applied_damage * recoil)
        add_log(f"{pokemon.base.name}은 반동으로 피해를 입었다!")

    return pokemon.copy_with(current_hp=max(0, pokemon.current_hp - damage))


def apply_thorn_damage(pokemon: BattlePokemon) -> BattlePokemon:
    if not pokemon or not pokemon.base:
        return pokemon

    add_log = store.add_log
    ability_name = pokemon.base.ability.name if pokemon.base.ability else None
    damage = 0
    print(f"apply_thorn_damage 호출: {pokemon.base.name}")
    if ability_name != "매직가드":
        damage = int(pokemon.base.hp * 0.125)
        add_log(f"{pokemon.base.name}은 가시에 의해 피해를 입었다!")
        print(f"{pokemon.base.name}은 가시에 의해 피해를 입었다!\n {pokemon.current_hp}에서 {pokemon.current_hp - damage}로 변경")

    return pokemon.copy_with(current_hp=max(0, pokemon.current_hp - damage))


def apply_status_condition_damage(pokemon: BattlePokemon, status: str) -> BattlePokemon:
    if not pokemon or not pokemon.base:
        return pokemon

    add_log = store.add_log
    ability_name = pokemon.base.ability.name if pokemon.base.ability else None
    damage = 0

    if ability_name != "매직가드":
        if status == "화상":
            damage = int(pokemon.base.hp * 0.0625)
            add_log(f"🔥 {pokemon.base.name}은 화상으로 피해를 입었다!")
            print(f"🔥 {pokemon.base.name}은 화상으로 피해를 입었다!\n {pokemon.current_hp}에서 {pokemon.current_hp - damage}로 변경")
        elif status == "독":
            damage = int(pokemon.base.hp * 0.125)
            add_log(f"🍄 {pokemon.base.name}은 독으로 피해를 입었다!")
            print(f"🍄 {pokemon.base.name}은 독으로 피해를 입었다!\n {pokemon.current_hp}에서 {pokemon.current_hp - damage}로 변경")
        elif status == "조이기":
            damage = int(pokemon.base.hp * 0.125)
            add_log(f"🪢 {pokemon.base.name}은 조임 피해를 입었다!")
            print(f"🪢 {pokemon.base.name}은 조임 피해를 입었다!\n {pokemon.current_hp}에서 {pokemon.current_hp - damage}로 변경")
        elif status == "맹독":
            damage = int(pokemon.base.hp * (1 / 6))
            add_log(f"🍄 {pokemon.base.name}은 맹독으로 피해를 입었다!")
            print(f"🍄 {pokemon.base.name}은 맹독으로 피해를 입었다!\n {pokemon.current_hp}에서 {pokemon.current_hp - damage}로 변경")
    return pokemon.copy_with(current_hp=max(0, pokemon.current_hp - damage))