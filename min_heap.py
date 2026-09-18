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

    def size(self) -> int:
        """현재 힙에 저장된 항목 수를 반환한다."""
        return len(self._items)
