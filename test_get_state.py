import unittest
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
            rank={"attack": 0, "defense": 0, "spAttack": 0, "spDefense": 0, "speed": 0, "accuracy": 0, "dodge": 0, "critical": 0},
            status=[],
            is_active=True
        )
        
        # Create mock teams
        self.my_team = [self.battle_pokemon] * 3
        self.enemy_team = [self.battle_pokemon] * 3
        
        # Create mock environment
        self.public_env = {
            "weather": "쾌청",
            "field": "그래스필드",
            "room": "트릭룸"
        }
        
        self.my_env = {
            "traps": ["독압정"]
        }
        
        self.enemy_env = {
            "traps": ["맹독압정"]
        }
        
        # Create mock effects
        self.my_effects = [
            {"name": "빛의장막", "remainingTurn": 3}
        ]
        
        self.enemy_effects = [
            {"name": "리플렉터", "remainingTurn": 2}
        ]

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
        
        # Check if state is a dictionary
        self.assertIsInstance(state, dict)
        
        # Check if all expected keys are present
        expected_keys = [
            'current_hp', 'type1', 'type2', 'attack', 'defense', 'sp_attack', 'sp_defense', 'speed',
            'weather', 'field', 'room', 'turn'
        ]
        for key in expected_keys:
            self.assertIn(key, state)
        
        # Check if values are in correct ranges
        self.assertGreaterEqual(state['current_hp'], 0)
        self.assertLessEqual(state['current_hp'], 1)
        self.assertGreaterEqual(state['type1'], 0)
        self.assertLessEqual(state['type1'], 1)
        
        # Check if the state vector has the expected length
        self.assertEqual(len(state), 126)  # Based on the actual calculation

if __name__ == '__main__':
    unittest.main() 
    
# python -m unittest test_get_state.py -v