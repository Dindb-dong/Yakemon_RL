from typing import List, Literal, Union

# StatusState 타입 정의
StatusState = Union[Literal[
    '화상', '마비', '독', '맹독', '얼음', '잠듦',
    '혼란', '풀죽음', '앵콜', '트집', '도발', '헤롱헤롱',
    '사슬묶기', '회복봉인', '씨뿌리기', '길동무', '소리기술사용불가',
    '하품', '교체불가', '조이기', '멸망의노래'
], None]

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
        if status not in self.status:
            return
        new_status = [s for s in self.status if s != status]
        self.status = new_status

    def clear_status(self) -> None:
        self.status = []

    def has_status(self, status: StatusState) -> bool:
        return status in self.status

    def get_status(self) -> List[StatusState]:
        return self.status

__all__ = ['StatusState', 'StatusManager']