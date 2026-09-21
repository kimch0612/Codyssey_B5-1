# 자료구조를 조합해 키·값 저장소와 LRU·메모리·TTL 관리를 구현한다.

import time

from typing import Optional

from hash_map import HashMap
from doubly_linked_list import DoublyLinkedList
from min_heap import MinHeap


class StoreEntry:
    """문자열 키·값과 현재 만료 시각을 묶는 저장소 엔트리. LRU Node의 data에 보관된다."""

    def __init__(self, key: str, value: str) -> None:
        """전달받은 키와 값을 보관한다."""
        self.key = key
        self.value = value
        self.expire_at: Optional[float] = None


class Store:
    """문자열 키·값을 보관하는 저장소. 해시맵과 LRU 이중 연결 리스트를 내부 저장소로 사용한다."""

    def __init__(self) -> None:
        """빈 저장소를 만든다."""
        self._data = HashMap()  # 직접 구현한 해시맵. 키는 str, 값은 LRU 리스트의 Node
        self._lru = DoublyLinkedList()
        self._used_memory = 0
        self._maxmemory = 0
        self._evicted_keys = 0
        self._expiry_heap = MinHeap()

    def _entry_size(self, key: str, value: str) -> int:
        """키와 값의 UTF-8 바이트 수 합계를 반환한다."""
        if (type(key) is not str) or (type(value) is not str):
            pass # 처리를 해줘야 할까?

        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def set_maxmemory(self, maxmemory: int) -> bool:
        """0 이상의 메모리 제한을 저장하고 성공 여부를 반환한다."""
        if maxmemory < 0:
            return False        # 음수는 받지 않는다
        elif maxmemory == 0:
            self._maxmemory = 0 # 메모리에 제한을 두지 않는다
        else:                   # 내가 설정한 값으로 적용
            self._maxmemory = maxmemory

        return True

    def info_memory(self) -> tuple[int, int, int]:
        """현재 사용량, 메모리 제한, 제거된 키 수를 순서대로 반환한다."""
        self._purge_expired()

        return self._used_memory, self._maxmemory, self._evicted_keys

    def expire(self, key: str, seconds: int) -> bool:
        """키에 만료 시간을 설정하면 True를, 키가 없으면 False를 반환한다."""
        lnode = self._data.get(key)
        if lnode is None:
            return False

        if seconds <= 0:
            if self.del_key(key) is True:
                return True
        else:
            timer = time.time() + seconds
            lnode.data.expire_at = timer
            self._expiry_heap.push((timer, key))
            return True

    def ttl(self, key: str) -> int:
        """키의 남은 TTL을 정수 초로 반환한다."""
        expired = self._expire_if_needed(key)
        if expired is True:
            return -2 # 방금 만료되어 삭제된 키다
        
        lru_node = self._data.get(key)
        if lru_node is None:
            return -2 # 원래부터 없는 키다

        expire_at = lru_node.data.expire_at
        if expire_at is None:
            return -1 # TTL이 없는 키다

        remaining = expire_at - time.time()
        if remaining <= 0:
            self.del_key(key)
            return -2 # 첫 번째 만료 검사 직후에 만료된 키이므로 제거한다

        return int(remaining)

    def _purge_expired(self) -> None:
        """현재 시각까지 만료된 힙 기록과 유효한 엔트리를 정리한다."""
        current = time.time()
        while True:
            heap_item = self._expiry_heap.peek()
            if heap_item is None:
                return

            rec_expire_at = heap_item[0]
            key = heap_item[1]

            if rec_expire_at > current:
                return # 미래의 기록이다
            else:
                del_heap = self._expiry_heap.pop() # 일단 값을 받아두긴 하는데, 쓰지는 않을듯

            lru_node = self._data.get(key)
            if lru_node is None:
                continue # 이미 삭제된 키의 오래된 힙 기록이다
            
            current_expire_at = lru_node.data.expire_at
            if rec_expire_at != current_expire_at:
                continue # TTL을 다시 설정하기 전의 오래된 힙 기록이다
            else:
                self.del_key(key)

    def _expire_if_needed(self, key: str) -> bool:
        """키가 현재 만료되었다면 삭제하고 True를, 아니면 False를 반환한다."""
        lru_node = self._data.get(key)
        if lru_node is None:
            return False
        
        expire_at = lru_node.data.expire_at
        if expire_at is None:
            return False # TTL이 없는 데이터다
        
        current = time.time()
        if expire_at > current:
            return False # 아직 만료되지 않았다
        
        return self.del_key(key)

    def _evict_lru(self) -> bool:
        """가장 오래 사용하지 않은 키 하나를 제거하고 성공 여부를 반환한다."""
        lru_tail = self._lru.tail
        if lru_tail is None:
            return False

        if self.del_key(lru_tail.data.key) is True:
            self._evicted_keys += 1
            return True
        else:
            # _evict_lru와 del_key에서 False가 나올 분기를 미리 처리하므로, 이 분기로 빠질 일은 없다
            return False

    def set(self, key: str, value: str) -> bool:
        """키에 값을 저장하면 True를, 단일 엔트리 OOM이면 False를 반환한다."""
        entry_size = self._entry_size(key, value)

        if (self._maxmemory > 0) and (entry_size > self._maxmemory): # Out Of Memory 발생 조건인가?
            return False

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

        if self._maxmemory > 0:
            while self._used_memory > self._maxmemory:
                self._evict_lru() # 설정한 최대 메모리를 초과하지 않을 때까지 가장 오래 사용하지 않은 키를 하나씩 제거한다

        return True

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
        self._purge_expired()

        return self._data.size()

    def keys(self) -> list:
        """저장된 키를 문자열 목록으로 반환한다. 순서·패턴 매칭은 요구하지 않는다."""
        self._purge_expired()

        return self._data.keys()
