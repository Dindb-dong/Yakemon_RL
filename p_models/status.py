from typing import List, Literal

# StatusState 타입 정의
StatusState = Literal[
    '화상', '마비', '독', '맹독', '얼음', '잠듦',
    '혼란', '풀죽음', '앵콜', '트집', '도발', '헤롱헤롱',
    '사슬묶기', '회복봉인', '씨뿌리기', '길동무', '소리기술사용불가',
    '하품', '교체불가', '조이기', '멸망의노래'
]

class StatusManager:
    def __init__(self, initial_status: List[StatusState] = []):
        self.status: List[StatusState] = initial_status.copy()

    def add_status(self, status: StatusState) -> None:
        if not status or self.has_status(status):
            return

        exclusive = ['마비', '독', '맹독', '얼음', '잠듦', '화상']
        if any(s in self.status for s in exclusive) and status in exclusive:
            print('중복 상태이상!')
            return

        self.status.append(status)

    def remove_status(self, status: StatusState) -> None:
        self.status = [s for s in self.status if s != status]

    def clear_status(self) -> None:
        self.status = []

    def has_status(self, status: StatusState) -> bool:
        return status in self.status

    def get_status(self) -> List[StatusState]:
        return self.status