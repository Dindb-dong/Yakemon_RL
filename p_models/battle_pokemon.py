from typing import Optional, List, Dict, Callable
from p_models.pokemon_info import PokemonInfo

class BattlePokemon:
    def __init__(
        self,
        pokemon_info: PokemonInfo,
        level: int = 50,
        moves: Optional[List['MoveInfo']] = None,
        ability: Optional[str] = None,
        item: Optional[str] = None,
        nature: Optional[str] = None,
        evs: Optional[Dict[str, int]] = None,
        ivs: Optional[Dict[str, int]] = None
    ):
        self.pokemon_info = pokemon_info
        self.level = level
        self.moves = moves or []
        self.ability = ability
        self.item = item
        self.nature = nature
        self.evs = evs or {}
        self.ivs = ivs or {}
        
        # 현재 상태
        self.hp = self.calculate_max_hp()
        self.status = None
        self.volatile_status = []
        self.stat_stages = {
            'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0
        }
        self.boosts = {
            'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0,
            'accuracy': 0, 'evasion': 0
        }
        
    def calculate_max_hp(self) -> int:
        """최대 HP 계산"""
        base_hp = self.pokemon_info.base_stats['hp']
        iv = self.ivs.get('hp', 31)
        ev = self.evs.get('hp', 0)
        
        # HP = ((2 * Base + IV + EV/4) * Level/100) + Level + 10
        hp = ((2 * base_hp + iv + ev/4) * self.level/100) + self.level + 10
        return int(hp)
    
    def calculate_stat(self, stat: str) -> int:
        """스탯 계산"""
        base = self.pokemon_info.base_stats[stat]
        iv = self.ivs.get(stat, 31)
        ev = self.evs.get(stat, 0)
        stage = self.stat_stages[stat]
        
        # Stat = ((2 * Base + IV + EV/4) * Level/100 + 5) * Nature
        stat_value = ((2 * base + iv + ev/4) * self.level/100 + 5)
        
        # 스테이지 보정
        if stage > 0:
            stat_value *= (2 + stage) / 2
        elif stage < 0:
            stat_value *= 2 / (2 - stage)
            
        return int(stat_value)
    
    def apply_status(self, status: str):
        """상태이상 적용"""
        if self.status is None:
            self.status = status
    
    def remove_status(self):
        """상태이상 제거"""
        self.status = None
    
    def apply_volatile_status(self, status: str):
        """일시적 상태이상 적용"""
        if status not in self.volatile_status:
            self.volatile_status.append(status)
    
    def remove_volatile_status(self, status: str):
        """일시적 상태이상 제거"""
        if status in self.volatile_status:
            self.volatile_status.remove(status)
    
    def change_stat_stage(self, stat: str, amount: int):
        """스탯 스테이지 변경"""
        self.stat_stages[stat] = max(-6, min(6, self.stat_stages[stat] + amount))
    
    def change_boost(self, stat: str, amount: int):
        """부스트 변경"""
        self.boosts[stat] = max(-6, min(6, self.boosts[stat] + amount))
    
    def take_damage(self, amount: int):
        """데미지 적용"""
        self.hp = max(0, self.hp - amount)
    
    def heal(self, amount: int):
        """회복"""
        max_hp = self.calculate_max_hp()
        self.hp = min(max_hp, self.hp + amount)
    
    def is_fainted(self) -> bool:
        """기절 여부 확인"""
        return self.hp <= 0
    
    def get_state(self) -> Dict:
        """현재 상태 반환"""
        return {
            'hp': self.hp,
            'max_hp': self.calculate_max_hp(),
            'status': self.status,
            'volatile_status': self.volatile_status,
            'stat_stages': self.stat_stages,
            'boosts': self.boosts
        }