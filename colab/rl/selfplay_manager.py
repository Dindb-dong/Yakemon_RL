class SelfPlayManager:
    """자가 대전 관리 클래스"""

    def __init__(self, win_rate_threshold=60.0, eval_episodes=100):
        """
        인자:
            win_rate_threshold: 상대방 업데이트를 위한 승률 임계값
            eval_episodes: 자가 대전 평가를 위한 에피소드 수
        """
        self.win_rate_threshold = win_rate_threshold
        self.eval_episodes = eval_episodes
        self.opponent_agent = None
        self.opponent_version = -1  # 초기 -1 (상대방 없음)
        self.selfplay_active = False
        self.selfplay_win_rate = 0.0
        self.selfplay_evaluations = []  # 자가 대전 평가 기록
        self.fixed_team = None

        # AI 상대 평가 결과 추가
        self.ai_opponent_win_rate = 0.0

    def start_selfplay(self, agent):
        """자가 대전 시작"""
        if self.fixed_team is None:
            self.fixed_team = create_fixed_team()  # 고정 팀 명시적 생성
        self.opponent_agent = agent.clone()
        self.opponent_version = agent.version
        self.selfplay_active = True
        print(f"\n자가 대전 시작! 상대방 버전: {self.opponent_version}")
        return self.opponent_agent

    def evaluate_selfplay(self, agent, env_creator):
        """자가 대전 성능 평가"""
        if not self.selfplay_active or self.opponent_agent is None:
            return 0.0

        print(f"\n[자가 대전 평가] 버전 {agent.version} vs 버전 {self.opponent_version}")

        def selfplay_team_creator():
            return create_selfplay_teams(self.fixed_team, randomize_order=True)

        # 평가 환경 설정
        env = PokemonEnv(selfplay_team_creator, opponent_agent=self.opponent_agent)

        # 통계
        wins = 0

        for episode in range(self.eval_episodes):
            state = env.reset()
            done = False

            # 탐색률 백업 (평가 중에는 탐색 없음)
            epsilon_backup = agent.epsilon
            agent.epsilon = 0

            while not done:
                # 행동 선택 및 실행
                valid_actions = env.get_valid_actions()
                action = agent.choose_action(state, valid_actions)
                next_state, reward, done, info = env.step(action)

                state = next_state

                # 너무 긴 에피소드 방지
                if env.battle.turn >= 50:
                    break

            # 탐색률 복원
            agent.epsilon = epsilon_backup

            # 승리 확인
            if info.get('battle_over', False) and info.get('winner', None) == 'player':
                wins += 1

        # 자가 대전 승률 계산
        self.selfplay_win_rate = (wins / self.eval_episodes) * 100

        # 평가 결과 기록
        self.selfplay_evaluations.append({
            'agent_version': agent.version,
            'opponent_version': self.opponent_version,
            'win_rate': self.selfplay_win_rate,
            'episodes': self.eval_episodes
        })

        print(f"[자가 대전 결과] 승률: {self.selfplay_win_rate:.1f}% ({wins}/{self.eval_episodes})")

        # 추가: 기존 AI에 대한 평가 수행
        self.evaluate_against_ai(agent, env_creator)

        return self.selfplay_win_rate

    def evaluate_against_ai(self, agent, env_creator, eval_episodes=50):
        """기존 AI에 대한 성능 평가"""
        print(f"\n[기존 AI 평가] 버전 {agent.version}")

        # 평가 환경 설정 (랜덤 타입 밸런스 팀 사용)
        env = PokemonEnv(create_balanced_teams)  # 기존 AI와 랜덤 밸런스 팀

        # 통계
        wins = 0

        for episode in range(eval_episodes):
            state = env.reset()
            done = False

            # 탐색률 백업 (평가 중에는 탐색 없음)
            epsilon_backup = agent.epsilon
            agent.epsilon = 0

            while not done:
                # 행동 선택 및 실행
                valid_actions = env.get_valid_actions()
                action = agent.choose_action(state, valid_actions)
                next_state, reward, done, info = env.step(action)

                state = next_state

                # 너무 긴 에피소드 방지
                if env.battle.turn >= 50:
                    break

            # 탐색률 복원
            agent.epsilon = epsilon_backup

            # 승리 확인
            if info.get('battle_over', False) and info.get('winner', None) == 'player':
                wins += 1

        # 기존 AI 대상 승률 계산
        self.ai_opponent_win_rate = (wins / eval_episodes) * 100

        print(f"[기존 AI 결과] 승률: {self.ai_opponent_win_rate:.1f}% ({wins}/{eval_episodes})")

        return self.ai_opponent_win_rate

    def should_update_opponent(self):
        """상대방 업데이트 여부 결정"""
        return self.selfplay_active and self.selfplay_win_rate >= self.win_rate_threshold

    def update_opponent(self, agent):
        """상대방 업데이트"""
        # 버전 증가
        new_version = agent.increment_version()

        # 새 상대방 생성
        self.opponent_agent = agent.clone()
        self.opponent_version = new_version

        print(f"\n자가 대전 상대방 업데이트! 새 버전: {self.opponent_version}")
        return self.opponent_agent

    def get_selfplay_info(self):
        """자가 대전 정보 반환"""
        if not self.selfplay_active:
            return None

        return {
            'active': self.selfplay_active,
            'opponent_version': self.opponent_version,
            'win_rate': self.selfplay_win_rate,
            'ai_win_rate': self.ai_opponent_win_rate,  # 기존 AI 승률 추가
            'evaluations': self.selfplay_evaluations
        } 