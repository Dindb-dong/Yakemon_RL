"""배틀 시각화 유틸리티 모듈"""

import matplotlib.pyplot as plt
import numpy as np
from ..p_models.types import TYPE_NAMES, get_type_name, TYPE_EFFECTIVENESS

class BattleVisualizer:
    """배틀 시각화 클래스"""
    
    @staticmethod
    def plot_battle_state(battle):
        """현재 배틀 상태 시각화"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # 플레이어 포켓몬 정보
        player_pokemon = battle.player_team.active_pokemon
        BattleVisualizer._plot_pokemon_info(ax1, player_pokemon, "플레이어")
        
        # 상대방 포켓몬 정보
        opponent_pokemon = battle.opponent_team.active_pokemon
        BattleVisualizer._plot_pokemon_info(ax2, opponent_pokemon, "상대방")
        
        plt.tight_layout()
        return fig

    @staticmethod
    def _plot_pokemon_info(ax, pokemon, title):
        """개별 포켓몬 정보 시각화"""
        # HP 바
        hp_ratio = pokemon.current_hp / pokemon.stats['hp']
        ax.barh(0, hp_ratio, color='green', alpha=0.6)
        ax.set_xlim(0, 1)
        ax.set_yticks([])
        ax.set_xlabel('HP')
        
        # 포켓몬 이름과 타입
        type_names = [get_type_name(t) for t in pokemon.types]
        ax.set_title(f"{title}: {pokemon.name} ({', '.join(type_names)})")
        
        # 상태 이상
        if pokemon.status_condition:
            ax.text(0.5, 0.5, f"상태: {pokemon.status_condition}", 
                   ha='center', va='center', transform=ax.transAxes)
        
        # 스탯 변화
        stat_changes = []
        for stat, stage in pokemon.stat_stages.items():
            if stage != 0:
                stat_changes.append(f"{stat}: {stage:+d}")
        if stat_changes:
            ax.text(0.5, 0.4, f"스탯 변화: {', '.join(stat_changes)}", 
                   ha='center', va='center', transform=ax.transAxes)

    @staticmethod
    def plot_learning_curve(rewards, losses=None):
        """학습 곡선 시각화"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5))
        
        # 보상 그래프
        ax1.plot(rewards)
        ax1.set_title('에피소드별 보상')
        ax1.set_xlabel('에피소드')
        ax1.set_ylabel('보상')
        
        # 손실 그래프 (있는 경우)
        if losses:
            ax2.plot(losses)
            ax2.set_title('학습 손실')
            ax2.set_xlabel('학습 스텝')
            ax2.set_ylabel('손실')
        
        plt.tight_layout()
        return fig

    @staticmethod
    def plot_type_effectiveness():
        """타입 상성 시각화"""
        type_names = list(TYPE_NAMES.keys())
        effectiveness = np.zeros((len(type_names), len(type_names)))
        
        for i, atk_type in enumerate(type_names):
            for j, def_type in enumerate(type_names):
                effectiveness[i, j] = TYPE_EFFECTIVENESS[TYPE_NAMES[atk_type]][TYPE_NAMES[def_type]]
        
        plt.figure(figsize=(12, 10))
        plt.imshow(effectiveness, cmap='RdYlGn')
        plt.colorbar(label='효과')
        plt.xticks(range(len(type_names)), type_names, rotation=45)
        plt.yticks(range(len(type_names)), type_names)
        plt.title('타입 상성')
        plt.tight_layout()
        return plt.gcf() 