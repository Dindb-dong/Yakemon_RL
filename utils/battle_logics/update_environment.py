from context.battle_store import store
from context.duration_store import duration_store
from typing import Literal

SideType = Literal["my", "enemy"]

def set_screen(side: SideType, screen: str, remove: bool = False):
    env = store.state["my_env"] if side == "my" else store.state["enemy_env"]
    setter = store.set_my_env if side == "my" else store.set_enemy_env
    add_effect = duration_store.add_effect

    if screen:
        if remove:
            setter({"screen": screen})
            return

        if env.screen and screen in env.screen:
            store.add_log(f"{screen}이 이미 발동되어 있다!")
        else:
            if screen == '오로라베일' and (env.screen and ('빛의장막' in env.screen or '리플렉터' in env.screen)):
                store.add_log("오로라베일은 빛의장막, 리플렉터와 중복 발동할 수 없다!")
            elif screen in ['빛의장막', '리플렉터'] and (env.screen and '오로라베일' in env.screen):
                store.add_log("빛의장막, 리플렉터는 오로라베일과 중복 발동할 수 없다!")
            else:
                setter({"screen": screen})
                add_effect({"name": screen, "remaining_turn": 5}, side)
                store.add_log(f"{screen}이 발동되었다!")
                print(f"update_environment: {screen}이 발동되었다!")

def set_weather(weather: str):
    add_effect = duration_store.add_effect
    public_env = store.state["public_env"]
    if weather and public_env.weather != weather:
        add_effect({"name": weather, "remaining_turn": 5}, "public")
    store.set_public_env({"weather": weather})
    print(f"update_environment: {weather}이 발동되었다!")

def set_field(field: str):
    if field:
        duration_store.add_effect({"name": field, "remaining_turn": 5}, "public")
    store.set_public_env({"field": field})
    print(f"update_environment: {field}이 발동되었다!")

def set_room(room: str):
    public_env = store.state["public_env"]
    add_effect = duration_store.add_effect
    if room:
        if public_env.room == room:
            store.add_log(f"{room}이 이미 발동되어 있다!")
        else:
            store.add_log(f"{room}이 발동됐다!")
            add_effect({"name": room, "remaining_turn": 5}, "public")
    store.set_public_env({"room": room})
    print(f"update_environment: {room}이 발동되었다!")
def set_aura(aura: str):
    public_env = store.state["public_env"]
    aura_list = public_env.aura or []
    if aura not in aura_list:
        store.set_public_env({"aura": aura_list + [aura]})

def remove_aura(aura: str):
    public_env = store.state["public_env"]
    updated = [a for a in public_env.aura if a != aura]
    store.set_public_env({"aura": updated})

def add_trap(side: SideType, new_trap: str):
    env = store.state["my_env"] if side == "my" else store.state["enemy_env"]
    setter = store.set_my_env if side == "my" else store.set_enemy_env
    trap_list = list(env.trap)
    add_log = store.add_log

    if new_trap == "독압정":
        if "독압정" in trap_list:
            trap_list.remove("독압정")
            trap_list.append("맹독압정")
            setter({"trap": trap_list})
            add_log("☠️ 맹독압정이 설치되었다!")
            return

    spike_levels = ["압정뿌리기", "압정뿌리기2", "압정뿌리기3"]
    if new_trap in spike_levels:
        for i, level in enumerate(spike_levels):
            if level in trap_list:
                if i < 2:
                    trap_list.remove(level)
                    trap_list.append(spike_levels[i+1])
                    setter({"trap": trap_list})
                    add_log(f"🧷 {spike_levels[i+1]}가 설치되었다!")
                    return
                else:
                    add_log("⚠️ 이미 압정뿌리기3이 설치되어 있습니다.")
                    return
        trap_list.append("압정뿌리기")
        setter({"trap": trap_list})
        add_log("🧷 압정뿌리기가 설치되었다!")
        return

    if new_trap not in trap_list: # 그 외 트랩 추가
        trap_list.append(new_trap)
        setter({"trap": trap_list})
        add_log(f"⚙️ {new_trap}이 설치되었다!")

def remove_trap(side: SideType, trap: str):
    env = store.state["my_env"] if side == "my" else store.state["enemy_env"]
    setter = store.set_my_env if side == "my" else store.set_enemy_env
    updated = [t for t in env.trap if t != trap]
    setter({"trap": updated})

def reset_trap(side: SideType):
    setter = store.set_my_env if side == "my" else store.set_enemy_env
    setter({"trap": []})

def add_disaster(disaster: str):
    public_env = store.state["public_env"]
    disaster_list = public_env.disaster or []
    if disaster_list.count(disaster) == 1: # 중복 발동 방지
        store.set_public_env({"disaster": [d for d in disaster_list if d != disaster]})
    else:
        store.set_public_env({"disaster": disaster_list + [disaster]})

def remove_disaster(disaster: str):
    public_env = store.state["public_env"]
    disaster_list = public_env.disaster or []
    if disaster not in disaster_list: # 만약 교체로 인해 없애려 했는데 이미 없는 상태라는 뜻은, 
      # 중복돼서 적용되고 있었다는 뜻이니까, 다시 활성화.
        store.set_public_env({"disaster": disaster_list + [disaster]})
    else:
        store.set_public_env({"disaster": [d for d in disaster_list if d != disaster]})

def reset_environment():
    store.set_public_env({"weather": None, "field": None, "aura": [], "disaster": []})
    store.set_my_env({"trap": []})
    store.set_enemy_env({"trap": []})