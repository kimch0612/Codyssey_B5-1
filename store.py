# 자료구조를 조합해 키·값 저장소와 LRU·메모리·TTL 관리를 구현한다.

from typing import Optional

from hash_map import HashMap
from doubly_linked_list import DoublyLinkedList


class StoreEntry:
    """문자열 키와 값을 묶는 저장소 엔트리. LRU 리스트 노드의 data에 보관된다."""

    def __init__(self, key: str, value: str) -> None:
        """전달받은 키와 값을 보관한다."""
        self.key = key
        self.value = value


class Store:
    """문자열 키·값을 보관하는 저장소. 해시맵과 LRU 이중 연결 리스트를 내부 저장소로 사용한다."""

    def __init__(self) -> None:
        """빈 저장소를 만든다."""
        self._data = HashMap()  # 직접 구현한 해시맵. 키는 str, 값은 LRU 리스트의 Node
        self._lru = DoublyLinkedList()
        self._used_memory = 0

    def _entry_size(self, key: str, value: str) -> int:
        """키와 값의 UTF-8 바이트 수 합계를 반환한다."""
        if (type(key) is not str) or (type(value) is not str):
            pass # 처리를 해줘야 할까?

        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def set(self, key: str, value: str) -> None:
        """키에 값을 저장한다. 새 키면 추가하고, 기존 키면 값을 덮어쓴다."""
        lru_node = self._data.get(key)

        if lru_node is None:
            entry = StoreEntry(key, value)
            lnode = self._lru.insert_front(entry)
            self._data.put(key, lnode)
            self._used_memory += self._entry_size(key, value)
        else:
            old_value = lru_node.data.value
            lru_node.data.value = value
            self._used_memory += (self._entry_size(key, value) - self._entry_size(key, old_value))
            self._lru.move_to_front(lru_node)

    def get(self, key: str) -> Optional[str]:
        """키의 값을 반환한다. 존재하면 값 문자열, 없으면 None을 반환한다."""
        lru_node = self._data.get(key)

        if lru_node is None:
            return None
        else:
            self._lru.move_to_front(lru_node)
            return lru_node.data.value

    def del_key(self, key: str) -> bool:
        """키를 삭제한다. 삭제 성공 시 True, 없는 키이면 False를 반환한다."""
        lru_node = self._data.get(key)

        if lru_node is None:
            return False
        else:
            entry_size = self._entry_size(lru_node.data.key, lru_node.data.value)

            if self._data.remove(key) is False:
                # 위쪽에서 이미 검사했으니 이 분기로 빠질 일은 없을 듯..??
                return False
            else:
                lru_node_deleted = self._lru.remove_node(lru_node) # 반환받은 객체는 어쩌지? 일단 들고는 있어보자
                self._used_memory -= entry_size
                return True

    def exists(self, key: str) -> bool:
        """키의 존재 여부를 반환한다. 값의 내용과 관계없이 존재하면 True를 반환한다."""
        if self._data.contains(key) is False:
            return False
        else:
            return True

    def dsize(self) -> int:
        """현재 저장된 키의 개수를 반환한다."""
        return self._data.size()

    def keys(self) -> list:
        """저장된 키를 문자열 목록으로 반환한다. 순서·패턴 매칭은 요구하지 않는다."""
        return self._data.keys()
