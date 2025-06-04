import unittest
import numpy as np
from RL.get_state_vector import get_state
from p_models.battle_pokemon import BattlePokemon
from p_models.pokemon_info import PokemonInfo
from p_models.move_info import MoveInfo
from context.battle_store import BattleStore

class TestGetState(unittest.TestCase):
    def setUp(self):
        self.battle_store = BattleStore()
        # Create mock PokemonInfo
        self.pokemon_info = PokemonInfo(
            id=1,
            name="이상해씨",
            types=["풀", "독"],
            hp=45,
            attack=49,
            defense=49,
            sp_attack=65,
            sp_defense=65,
            speed=45,
            moves=[
                MoveInfo(id=1, name="몸통박치기", type="노말", power=40, pp=35, accuracy=100, category="물리", target="opponent"),
                MoveInfo(id=2, name="잎날가르기", type="풀", power=55, pp=25, accuracy=95, category="물리", target="opponent"),
            ]
        )
        
        # Create mock BattlePokemon
        self.battle_pokemon = BattlePokemon(
            base=self.pokemon_info,
            current_hp=45,
            pp={"몸통박치기": 35, "잎날가르기": 25},
            rank={"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0, "accuracy": 0, "dodge": 0, "critical": 0},
            status=[],
            is_active=True
        )
        
        # Create mock teams
        self.my_team = [self.battle_pokemon] * 3
        self.enemy_team = [self.battle_pokemon] * 3
        
        # Create mock environment (dummy, not used in new version)
        self.public_env = None
        self.my_env = None
        self.enemy_env = None
        
        # Create mock effects (dummy, not used in new version)
        self.my_effects = []
        self.enemy_effects = []

    def test_get_state(self):
        # Test the function
        state = get_state(
            store=self.battle_store,
            my_team=self.my_team,
            enemy_team=self.enemy_team,
            active_my=0,
            active_enemy=0,
            public_env=self.public_env,
            my_env=self.my_env,
            enemy_env=self.enemy_env,
            turn=1,
            my_effects=self.my_effects,
            enemy_effects=self.enemy_effects
        )
        
        print(f"State vector length: {len(state)}")
        # Check if state is a numpy array
        self.assertIsInstance(state, np.ndarray)
        
        # Check if the state vector has the expected length (example: 1+24+5+6+2*(1+4+3+6+6+6)+6*포켓몬 feature)
        # For now, just check it's 1D and not empty
        self.assertEqual(len(state.shape), 1)
        self.assertGreater(state.shape[0], 0)
        
        # Check if values are in correct ranges for a few elements
        self.assertGreaterEqual(state[0], 0)
        self.assertLessEqual(state[0], 1)
        # Check that all values are finite
        self.assertTrue(np.all(np.isfinite(state)))

if __name__ == '__main__':
    unittest.main()

# python -m unittest test_get_state.py -v