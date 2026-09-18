# 해시 함수와 체이닝 기반 해시맵의 저장·조회·삭제 및 확장을 구현한다.

from doubly_linked_list import DoublyLinkedList


class HashEntry:
    """해시맵에 저장할 문자열 키와 그에 연결된 값을 보관한다."""

    def __init__(self, key: str, value: object) -> None:
        """전달받은 키와 값을 그대로 보관한다."""
        self.key = key      # 저장된 항목을 찾고 구분할 문자열 키를 보관
        self.value = value  # 해당 키에 연결된 값 객체를 보관


class HashMap:
    """버킷별 이중 연결 리스트로 충돌을 처리하는 해시맵이다."""

    def __init__(self) -> None:
        """독립된 빈 버킷 8개와 저장된 키 수 0인 초기 상태를 만든다."""
        self._capacity = 8  # 현재 버킷 수를 보관하며, 버킷 인덱스 계산과 확장 판단에 사용
        self._size = 0      # 현재 저장된 서로 다른 키의 개수를 보관
        self._buckets = [DoublyLinkedList() for _ in range(self._capacity)]