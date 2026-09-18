# 해시 함수와 체이닝 기반 해시맵의 저장·조회·삭제 및 확장을 구현한다.

from typing import Optional

from doubly_linked_list import DoublyLinkedList, Node


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
        self._buckets = [DoublyLinkedList() for _ in range(self._capacity)] # 각 버킷의 연결 리스트를 담아, 계산한 인덱스로 해당 버킷에 접근하게 함

    def _hash(self, key: str) -> int:
        """문자열 키로 현재 버킷 범위의 인덱스를 계산하며 저장 상태는 바꾸지 않는다."""
        result = 0

        for letter in key:
            result = (result * 37 + ord(letter)) % self._capacity
            # 문자 번호를 단순히 더하면 "ab"와 "ba"가 같아지므로
            # 기존 `result`에 일정한 수를 곱해 앞선 문자에 가중치를 주고,
            # 현재 문자의 `ord()`를 더해 문자의 내용과 순서를 함께 반영함

        return result

    def _find_node(self, key: str) -> Optional[Node]:
        """키와 일치하는 기존 버킷 노드를 반환하고, 없으면 None을 반환한다."""
        idx = self._hash(key)
        current = self._buckets[idx].head

        while current:
            if key == current.data.key:
                return current
            else:
                current = current.next
        
        return None

    def put(self, key: str, value: object) -> None:
        """새 키의 엔트리를 추가하거나 기존 키의 값을 갱신한다."""
        entry = self._find_node(key)
        if entry == None: # 새 엔트리를 추가
            idx = self._hash(key)
            hash_entry = HashEntry(key, value)
            bucket = self._buckets[idx]
            bucket.insert_back(hash_entry)
            self._size += 1
        else:             # 기존 엔트리를 갱신
            entry.data.value = value