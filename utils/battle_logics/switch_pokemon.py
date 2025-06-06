from typing import Literal, Optional
from context.battle_store import BattleStore, BattleStoreState, store
from context.duration_store import DurationStore, duration_store
from utils.battle_logics.apply_appearance import apply_appearance
from utils.battle_logics.apply_none_move_damage import apply_trap_damage
from utils.battle_logics.get_best_switch_index import get_best_switch_index
from utils.battle_logics.update_battle_pokemon import (
    add_status, change_hp, change_rank, remove_status, reset_rank, reset_state, set_active, set_used_move
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


async def switch_pokemon(side: SideType, new_index: int, baton_touch: bool = False, battle_store: Optional[BattleStore] = store, duration_store: Optional[DurationStore] = duration_store) -> None:
    """
    포켓몬 교체 함수
    
    Args:
        side: 'my' 또는 'enemy'
        new_index: 교체할 포켓몬의 인덱스
        baton_touch: 배턴터치로 인한 교체인지 여부
    """
    state: BattleStoreState = battle_store.get_state()
    team = state["my_team"] if side == "my" else state["enemy_team"]
    current_index = state["active_my"] if side == "my" else state["active_enemy"]
    
    # 현재 포켓몬과 교체하려는 포켓몬이 같으면 조기 종료
    if current_index == new_index:
        return
        
    env = state["my_env"] if side == "my" else state["enemy_env"]
    switching_pokemon = team[current_index]
    next_pokemon = team[new_index]

    if new_index == -1:
        battle_store.add_log(f"{side}는 더 이상 낼 포켓몬이 없음")
        print(f"{side}는 더 이상 낼 포켓몬이 없음")
        return

    if team[new_index].current_hp <= 0:
        battle_store.add_log(f"쓰러진 포켓몬으로 교체할 수 없습니다.")
        print(f"쓰러진 포켓몬으로 교체할 수 없습니다.")
        return

    if switching_pokemon.base.ability and switching_pokemon.base.ability.name == "재생력" and switching_pokemon.current_hp > 0:
        battle_store.update_pokemon(side, current_index,
                             lambda p: change_hp(p, switching_pokemon.base.hp // 3))

    if baton_touch:
        battle_store.update_pokemon(side, new_index, lambda p: p.copy_with(
            rank=team[current_index].rank,
            substitute=team[current_index].substitute,
            status=[
                s for s in team[current_index].status if s in UNMAIN_STATUS_CONDITION or s in UNMAIN_STATUS_CONDITION_WITH_DURATION
            ]
        ))
        duration_store.transfer_effects(side, current_index, new_index)

    battle_store.update_pokemon(side, current_index, lambda p: reset_state(p, is_switch=True))
    battle_store.update_pokemon(side, current_index, lambda p: reset_rank(p))
    battle_store.update_pokemon(side, current_index, lambda p: p.copy_with(is_first_turn=False))

    for status in UNMAIN_STATUS_CONDITION + UNMAIN_STATUS_CONDITION_WITH_DURATION:
        if status in switching_pokemon.status:
            if status in UNMAIN_STATUS_CONDITION_WITH_DURATION:
                duration_store.remove_effect(status, side)
            battle_store.update_pokemon(side, current_index,
                                lambda p: remove_status(p, status))

    if switching_pokemon.base.ability and switching_pokemon.base.ability.name == "자연회복":
        for status in UNMAIN_STATUS_CONDITION + UNMAIN_STATUS_CONDITION_WITH_DURATION + MAIN_STATUS_CONDITION:
            if status in switching_pokemon.status:
                if status in UNMAIN_STATUS_CONDITION_WITH_DURATION:
                    duration_store.remove_effect(status, side)
                battle_store.update_pokemon(side, current_index,
                                    lambda p: remove_status(p, status))

    battle_store.update_pokemon(side, current_index, lambda p: set_active(p, False))
    battle_store.update_pokemon(side, current_index, lambda p: set_used_move(p, None))
    ability_name = switching_pokemon.base.ability.name if switching_pokemon.base.ability else None
    if ability_name and switching_pokemon.base.ability.appear:
        if "disaster" in switching_pokemon.base.ability.appear:
            remove_disaster(ability_name)
        if "aura_change" in switching_pokemon.base.ability.appear:
            remove_aura(ability_name)

    battle_store.update_pokemon(side, new_index, lambda p: set_active(p, True))
    battle_store.update_pokemon(side, new_index, lambda p: p.copy_with(is_first_turn=True))
    if side == "my":
        battle_store.set_active_my(new_index)
    else:
        battle_store.set_active_enemy(new_index)
    print(f"교체 후 포켓몬: {next_pokemon.base.name}")
    if env.trap:
        damage, trap_log, trap_condition = apply_trap_damage(next_pokemon, env.trap)
        
        # Update HP and check for fainting
        new_hp = max(0, next_pokemon.current_hp - damage)
        battle_store.update_pokemon(side, new_index, lambda p: p.copy_with(current_hp=new_hp))
        
        if new_hp <= 0:
            battle_store.add_log(f"{next_pokemon.base.name}이(가) 쓰러졌다!")
            switch_index = get_best_switch_index(side)
            if switch_index != -1 and switch_index != new_index:
                await switch_pokemon(side, switch_index)
            return

        if trap_condition:
            if trap_condition == "독압정 제거":
                remove_trap(side, "독압정")
                remove_trap(side, "맹독압정")
            elif trap_condition == "끈적끈적네트":
                battle_store.update_pokemon(side, new_index, lambda p: change_rank(p, "speed", -1))
            else:
                battle_store.update_pokemon(side, new_index,
                                    lambda p: add_status(p, trap_condition, side, battle_store=battle_store, duration_store=duration_store))

        if trap_log:
            battle_store.add_log(trap_log)
            print(trap_log)

    if team[new_index].current_hp <= 0 and side == "enemy":
        switch_index = get_best_switch_index(side)
        if switch_index != -1 and switch_index != new_index:  # 새로운 인덱스가 다를 때만 재귀 호출
            await switch_pokemon(side, switch_index)
        return
    else:
        wncp = "나" if side == "my" else "상대"
        battle_store.add_log(f"{wncp}는 {team[new_index].base.name}을/를 내보냈다!")
        apply_appearance(team[new_index], side)