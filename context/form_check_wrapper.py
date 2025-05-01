# context/form_check_wrapper.py

from typing import List, Callable, TypeVar, Any
from copy import deepcopy
from p_models.battle_pokemon import BattlePokemon

T = TypeVar('T', bound=dict)

def with_form_check(config: Callable[[Callable[[T], None], Callable[[], T], Any], Any]) -> Callable[[Callable[[T], None], Callable[[], T], Any], Any]:
    def wrapper(set_state: Callable[[T], None], get_state: Callable[[], T], api: Any):
        def wrapped_set_state(next_state: T):
            # 1. 원래 set 먼저 호출
            set_state(next_state)

            # 2. myTeam, enemyTeam 각각 폼체인지 체크
            def update_form_if_needed(team: List[BattlePokemon]) -> List[BattlePokemon]:
                updated_team = []
                for poke in team:
                    if callable(poke.form_condition):
                        should_change = poke.form_condition(poke)
                        expected_form = 1 if should_change else 0
                        if poke.form_num != expected_form:
                            if expected_form == 1:
                                if poke.base.form_change:
                                    changed = deepcopy(poke.base.form_change)
                                    changed.memorized_base = deepcopy(poke.base)
                                    changed.memorized_base.form_change = None  # 참조 순환 제거
                                    changed.memorized_base.memorized_base = None
                                    poke.base = changed
                            elif expected_form == 0:
                                if poke.base.memorized_base:
                                    poke.base = deepcopy(poke.base.memorized_base)
                            poke.form_num = expected_form
                            print(f"{poke.base.name}의 모습이 변했다! (expected_form: {expected_form})")
                    updated_team.append(poke)
                return updated_team

            current_state = get_state()

            new_my_team = update_form_if_needed(current_state['myTeam'])
            new_enemy_team = update_form_if_needed(current_state['enemyTeam'])

            if (new_my_team != current_state['myTeam'] or new_enemy_team != current_state['enemyTeam']):
                # 3. 변경되었으면 set 호출
                set_state({
                    **current_state,
                    'myTeam': new_my_team,
                    'enemyTeam': new_enemy_team,
                })

        return config(wrapped_set_state, get_state, api)

    return wrapper