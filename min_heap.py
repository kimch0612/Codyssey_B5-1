# 만료 시각이 가장 빠른 항목을 찾는 최소 힙을 구현한다.
from typing import List, Tuple


class MinHeap:
    """만료 시각이 가장 빠른 항목을 루트에 두는 최소 힙이다."""

    def __init__(self) -> None:
        self._items: List[Tuple[float, str]] = [] # (만료 시각, 키)

    def size(self) -> int:
        """현재 힙에 저장된 항목 수를 반환한다."""
        return len(self._items)
