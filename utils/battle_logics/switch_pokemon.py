from typing import Literal
from context.battle_store import store
from context.duration_store import duration_store
from utils.battle_logics.apply_appearance import apply_appearance
from utils.battle_logics.apply_none_move_damage import apply_trap_damage
from utils.battle_logics.get_best_switch_index import get_best_switch_index
from utils.battle_logics.update_battle_pokemon import (
    add_status, change_hp, change_rank, remove_status, reset_rank, reset_state, set_active
)
from utils.battle_logics.update_environment import remove_aura, remove_disaster, remove_trap

SideType = Literal["my", "enemy"]

UNMAIN_STATUS_CONDITION = ['헤롱헤롱', '씨뿌리기']
UNMAIN_STATUS_CONDITION_WITH_DURATION = [
    '도발', '트집', '사슬묶기', '회복봉인', '앵콜',
    '소리기술사용불가', '하품', '혼란', '교체불가',
    '조이기', '멸망의노래', '풀죽음'
]
MAIN_STATUS_CONDITION = ['화상', '마비', '잠듦', '얼음', '독', '맹독']


async def switch_pokemon(side: SideType, new_index: int, baton_touch: bool = False):
    team = store.state["my_team"] if side == "my" else store.state["enemy_team"]
    current_index = store.state["active_my"] if side == "my" else store.state["active_enemy"]
    env = store.state["my_env"] if side == "my" else store.state["enemy_env"]
    switching_pokemon = team[current_index]
    next_pokemon = team[new_index]

    if new_index == -1:
        store.add_log(f"{side}는 더 이상 낼 포켓몬이 없음")
        return

    if switching_pokemon.base.ability and switching_pokemon.base.ability.name == "재생력" and switching_pokemon.current_hp > 0:
        store.update_pokemon(side, current_index,
                             lambda p: change_hp(p, switching_pokemon.base.hp // 3))

    if baton_touch:
        store.update_pokemon(side, new_index, lambda p: p.deepcopy(
            rank=team[current_index].rank,
            substitute=team[current_index].substitute,
            status=[
                s for s in team[current_index].status if s in UNMAIN_STATUS_CONDITION or s in UNMAIN_STATUS_CONDITION_WITH_DURATION
            ]
        ))
        duration_store.transfer_effects(side, current_index, new_index)

    store.update_pokemon(side, current_index, lambda p: reset_state(p, is_switch=True))
    store.update_pokemon(side, current_index, lambda p: reset_rank(p))
    store.update_pokemon(side, current_index, lambda p: p.deepcopy(is_first_turn=False))

    for status in UNMAIN_STATUS_CONDITION + UNMAIN_STATUS_CONDITION_WITH_DURATION:
        if status in switching_pokemon.status:
            if status in UNMAIN_STATUS_CONDITION_WITH_DURATION:
                duration_store.remove_effect(side, status)
            store.update_pokemon(side, current_index,
                                  lambda p: remove_status(p, status))

    if switching_pokemon.base.ability and switching_pokemon.base.ability.name == "자연회복":
        for status in UNMAIN_STATUS_CONDITION + UNMAIN_STATUS_CONDITION_WITH_DURATION + MAIN_STATUS_CONDITION:
            if status in switching_pokemon.status:
                if status in UNMAIN_STATUS_CONDITION_WITH_DURATION:
                    duration_store.remove_effect(side, status)
                store.update_pokemon(side, current_index,
                                      lambda p: remove_status(p, status))

    store.update_pokemon(side, current_index, lambda p: set_active(p, False))

    ability_name = switching_pokemon.base.ability.name if switching_pokemon.base.ability else None
    if ability_name and switching_pokemon.base.ability.appear:
        if "disaster" in switching_pokemon.base.ability.appear:
            remove_disaster(ability_name)
        if "aura_change" in switching_pokemon.base.ability.appear:
            remove_aura(ability_name)

    store.update_pokemon(side, new_index, lambda p: set_active(p, True))
    store.update_pokemon(side, new_index, lambda p: p.deepcopy(is_first_turn=True))
    if side == "my":
        store.set_active_my(new_index)
    else:
        store.set_active_enemy(new_index)

    if env.trap:
        result = await apply_trap_damage(next_pokemon, env.trap)
        trapped = result["updated"]
        trap_log = result.get("log")
        trap_condition = result.get("status_condition")

        store.update_pokemon(side, new_index, lambda _: trapped)

        if trap_condition:
            if trap_condition == "독압정 제거":
                remove_trap(side, "독압정")
                remove_trap(side, "맹독압정")
            elif trap_condition == "끈적끈적네트":
                store.update_pokemon(side, new_index, lambda p: change_rank(p, "speed", -1))
            else:
                store.update_pokemon(side, new_index,
                                      lambda p: add_status(p, trap_condition, side))

        if trap_log:
            store.add_log(trap_log)

        next_pokemon = trapped

    if next_pokemon.current_hp <= 0 and side == "enemy":
        switch_index = get_best_switch_index(side)
        await switch_pokemon(side, switch_index)
    else:
        wncp = "나" if side == "my" else "상대"
        store.add_log(f"{wncp}는 {team[new_index].base.name}을/를 내보냈다!")
        apply_appearance(next_pokemon, side)