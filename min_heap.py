# 만료 시각이 가장 빠른 항목을 찾는 최소 힙을 구현한다.
from typing import List, Optional, Tuple


class MinHeap:
    """만료 시각이 가장 빠른 항목을 루트에 두는 최소 힙이다."""

    def __init__(self) -> None:
        self._items: List[Tuple[float, str]] = [] # (만료 시각, 키)

    def _heapify_up(self, index: int) -> None:
        """지정 위치의 항목을 부모 방향으로 옮겨 최소 힙 조건을 복구한다."""
        current = index
        while current > 0:
            parent_index = (current - 1) // 2
            # 단어 선택을 '부모'라고 하긴 했지만, 실제로 데이터가 연결이 된 건 아니고 마지막으로 추가한 데이터보다 위쪽에 있는 데이터랑 비교해서 만료가 더 빠른지 늦은지 검사해서 서로의 위치를 바꾸는거라고 이해함
            if self._items[current][0] >= self._items[parent_index][0]: # 현재 항목의 만료 시각이 부모보다 크거나 같은 경우
                break # 옮길 필요가 없으므로 냅둔다
            else: # 아니라면 서로 위치를 바꾼다
                tmp_item = self._items[current]
                self._items[current] = self._items[parent_index]
                self._items[parent_index] = tmp_item
                current = parent_index
        """
                    index 0
                    /       \
                index 1     index 2
                /    \       /    \
               3      4     5      6      라고 가정하고 6번을 기준으로 parent_index를 잡으면 2가 나옴
                                           그리고 2에서 또 부모를 잡으면 인덱스가 0이 나옴
        """

    def _heapify_down(self, index: int) -> None:
        """지정 위치의 항목을 자식 방향으로 옮겨 최소 힙 조건을 복구한다."""
        current = index
        while True:
            left_index = 2 * current + 1
            right_index = 2 * current + 2

            if left_index >= self.size():
                break # left_index가 size와 같아도 이미 인덱스를 벗어난 범위임
            else:
                child_index = left_index

            if 0 <= right_index < len(self._items): # 오른쪽 인덱스가 유효(존재)한다면
                if self._items[right_index][0] < self._items[child_index][0]:
                    child_index = right_index       # 비교 대상군을 오른쪽으로 슥삭하자
            
            if self._items[current][0] <= self._items[child_index][0]: # 현재 만료 시각 <= 선택한 자식의 만료 시각 (up과 반대다)
                break
            else:
                tmp_item = self._items[current]
                self._items[current] = self._items[child_index]
                self._items[child_index] = tmp_item
                current = child_index

    def push(self, item: Tuple[float, str]) -> None:
        """만료 시각과 키를 담은 항목을 추가하고 최소 힙 조건을 유지한다."""
        self._items.append(item)
        index = self.size() - 1
        self._heapify_up(index)

    def peek(self) -> Optional[Tuple[float, str]]:
        """최소 항목을 제거하지 않고 반환하며, 빈 힙이면 None을 반환한다."""
        if not self._items:
            return None
        else:
            return self._items[0]

    def pop(self) -> Optional[Tuple[float, str]]:
        """최소 항목을 제거해 반환하며, 빈 힙이면 None을 반환한다."""
        if not self._items:
            return None
        else:
            min_item = self.peek()         # 맨 앞 데이터
            last_item = self._items.pop()  # 맨 뒤 데이터

            if self._items:
                self._items[0] = last_item # 맨 뒤 데이터를 맨 앞으로 이동
                self._heapify_down(0)

            return min_item

    def size(self) -> int:
        """현재 힙에 저장된 항목 수를 반환한다."""
        return len(self._items)
