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
        if maxmemory < 0:       # 음수는 받지 않는다
            return False
        elif maxmemory == 0:    # 메모리에 제한을 두지 않는다
            self._maxmemory = 0
        else:                   # 내가 설정한 값으로 적용
            self._maxmemory = maxmemory

        return True

    def info_memory(self) -> tuple[int, int, int]:
        """현재 사용량, 메모리 제한, 제거된 키 수를 순서대로 반환한다."""
        self._purge_expired() # 값 반환 전에 만료된 데이터를 정리하자

        return self._used_memory, self._maxmemory, self._evicted_keys

    def expire(self, key: str, seconds: int) -> bool:
        """키에 만료 시간을 설정하면 True를, 키가 없으면 False를 반환한다."""
        if self._expire_if_needed(key): # 이미 만료된 키를 삭제하려고 했으므로 존재하지 않는 것 취급한다
            return False

        lnode = self._data.get(key)     # 해당 key로 조회한 노드값을 가져온다
        if lnode is None:               # 없는 key에 만료 시간을 설정하려고 했으므로 돌려보낸다
            return False

        if seconds <= 0:                # 만료 시간이 0초보다 작거나 같은 경우 즉시 삭제한다
            self.del_key(key)
            return True                 # del_key 메서드의 결과가 어떻던지간에 무조건 삭제한 것으로 취급할 것이므로 True로 고정함
        else:
            timer = time.time() + seconds           # 현재 시간에 만료시간을 더해서 최종 만료일을 구한다
            lnode.data.expire_at = timer            # 구한 값을 해당 노드에 저장하고
            self._expiry_heap.push((timer, key))    # 힙에 기록만 해두고, 실제 삭제는 나중에 _purge_expired()가 처리한다
            return True

    def ttl(self, key: str) -> int:
        """키의 남은 TTL을 정수 초로 반환한다."""
        expired = self._expire_if_needed(key)
        if expired is True:     # 방금 만료되어 삭제된 키다
            return -2
        
        lru_node = self._data.get(key)
        if lru_node is None:    # 원래부터 없는 키다
            return -2

        expire_at = lru_node.data.expire_at
        if expire_at is None:   # TTL이 없는 키다
            return -1

        remaining = expire_at - time.time()
        if remaining <= 0:      # 첫 번째 만료 검사 직후에 만료된 키이므로 제거한다
            self.del_key(key)
            return -2

        return int(remaining)

    def _purge_expired(self) -> None:
        """현재 시각까지 만료된 힙 기록과 유효한 엔트리를 정리한다."""
        current = time.time()
        while True:
            heap_item = self._expiry_heap.peek() # 만료 시간이 담긴 힙에서 가장 앞에 있는 (빨리 끝나는) 데이터를 가져온다
            if heap_item is None:                # 이게 없다는 건, 현재 유효한 TTL 설정이 단 하나도 없다는 말이다 (더 돌 이유가 없음)
                return

            rec_expire_at = heap_item[0]         # 만료 시간과
            key = heap_item[1]                   # 키를 복사해온다

            if rec_expire_at > current:          # 만료 시간이 지금보다 미래라면 조기 반환한다 (더 정리할 데이터가 없음)
                return
            else:                                # 아니라면, 최소 항목을 제거한다
                del_heap = self._expiry_heap.pop()

            lru_node = self._data.get(key)       # LRU 노드를 key를 통해 가져오고는데
            if lru_node is None:                 # 해당 노드가 없다면, 과거에 정리되고 만료시간 힙에 garbage 데이터가 남은 것이므로 넘어간다
                continue
            
            current_expire_at = lru_node.data.expire_at
            if rec_expire_at != current_expire_at: # EXPIRE 재설정 등으로 TTL이 변경되어 힙의 기록이 구버전이므로 건너뛴다
                continue
            else:
                self.del_key(key)                  # 노드를 삭제한다

        # rec_expire_at != current_expire_at이 발생하는 이유
        # EXPIRE 재설정을 하거나 SET으로 값을 덮어쓰면 기존에 있었던 데이터는 삭제하지 않고, 새로 힙에 만료 데이터를 넣는다
        # 이는 기존 데이터를 삭제하려고 하면 힙에서 해당 데이터를 발견할 때까지 순회를 해야 하기 때문이며, 이는 시간복잡도 측면에서 손해이다
        # 그러므로 Lazy Deletion과 결합해서 힙을 탐색할 때 불일치하는 항목은 그냥 건너뛰게 설계했다

    def _expire_if_needed(self, key: str) -> bool:
        """키가 현재 만료되었다면 삭제하고 True를, 아니면 False를 반환한다."""
        lru_node = self._data.get(key)
        if lru_node is None:
            return False
        
        expire_at = lru_node.data.expire_at
        if expire_at is None:   # TTL이 없는 데이터다
            return False
        
        current = time.time()
        if expire_at > current: # 아직 만료되지 않았다
            return False
        
        self.del_key(key)       # 삭제 후 날라온 값과 상관 없이 항상 True 반환
        return True

    def _evict_lru(self) -> bool:
        """가장 오래 사용하지 않은 키 하나를 제거하고 성공 여부를 반환한다."""
        lru_tail = self._lru.tail
        if lru_tail is None:
            return False

        if self.del_key(lru_tail.data.key) is True: # 삭제에 성공했다면 _evicted_keys에 1을 더한다
            self._evicted_keys += 1
            return True
        else:                                       # _evict_lru와 del_key에서 False가 나올 분기를 미리 처리하므로, 이 분기로 빠질 일은 없다
            return False

    def set(self, key: str, value: str) -> bool:
        """키에 값을 저장하면 True를, 단일 엔트리 OOM이면 False를 반환한다."""
        expired = self._expire_if_needed(key)
        entry_size = self._entry_size(key, value)

        if (self._maxmemory > 0) and (entry_size > self._maxmemory): # Out Of Memory 발생 조건인가?
            return False

        lru_node = self._data.get(key) # 이미 저장된 key인가? (갱신인지 신규 추가인지)

        if lru_node is None:           # 신규 추가라면
            entry = StoreEntry(key, value)                    # 데이터를 새로 만들고
            lnode = self._lru.insert_front(entry)             # 만든 데이터로 노드도 생성해서 맨 앞에 삽입한다 (LRU 추적 업데이트)
            self._data.put(key, lnode)                        # 만든 노드를 등록하고 (우체국 등기 전산)
            self._used_memory += self._entry_size(key, value) # 사용 중인 메모리에 이번에 등록한 데이터만큼 추가한다
        else:                          # 갱신이라면
            old_value = lru_node.data.value                   # StoreEntry의 현재 value 값을 old_value에 복사
            lru_node.data.value = value                       # 새로 받은 값으로 value 갱신
            self._used_memory += (self._entry_size(key, value) - self._entry_size(key, old_value)) # 이전에 쓴 값이랑 새로 갱신한 값의 차만큼 사용 메모리를 업데이트 한다
            lru_node.data.expire_at = None                    # 데이터를 갱신한 경우 만료 시간을 제거한다
            self._lru.move_to_front(lru_node)                 # 새로 갱신했으므로 맨 앞으로 이동

        if self._maxmemory > 0:
            while self._used_memory > self._maxmemory:
                self._evict_lru()                             # 설정한 최대 메모리를 초과하지 않을 때까지 가장 오래 사용하지 않은 키를 하나씩 제거한다

        return True

    def get(self, key: str) -> Optional[str]:
        """키의 값을 반환한다. 존재하면 값 문자열, 없으면 None을 반환한다."""
        # 버킷 Node
        # └─ .data → HashEntry
        #             └─ .value → LRU Node        ← HashMap.get()이 여기까지 꺼내줌
        #                             └─ .data → StoreEntry
        #                                         └─ .value → "Alice"
        expired = self._expire_if_needed(key)
        if expired is True: # 해당 키가 이미 만료되었는가?
            return None

        lru_node = self._data.get(key)

        if lru_node is None:
            return None                         # 데이터가 비어있다면 보여줄 데이터 또한 없다
        else:
            self._lru.move_to_front(lru_node)   # 접근했으므로 맨 앞으로 옮기고
            return lru_node.data.value          # key로 조회한 value를 반환한다

    def del_key(self, key: str) -> bool:
        """키를 삭제한다. 삭제 성공 시 True, 없는 키이면 False를 반환한다."""
        lru_node = self._data.get(key)
        if lru_node is not None:
            expire_at = lru_node.data.expire_at # 만료 시간 임시 복사
            was_expired = True if (expire_at is not None) and (expire_at <= time.time()) else False # 만료됐는지 여부 저장

        if lru_node is None:
            return False # 없는 key를 삭제하려고 했다
        else:
            entry_size = self._entry_size(lru_node.data.key, lru_node.data.value) # 삭제하려는 데이터 크기 저장

            if self._data.remove(key) is False:
                # 위쪽에서 이미 검사했으니 이 분기로 빠질 일은 없을 듯..??
                return False
            else:
                lru_node_deleted = self._lru.remove_node(lru_node) # 반환받은 객체는 어쩌지? 일단 들고는 있어보자
                self._used_memory -= entry_size # 삭제하려는 데이터 크기만큼 메모리 크기 비우기
                if was_expired:
                    return False # 내가 삭제하지 않아도 만료돼서 이미 삭제됐을 친구였다 (즉, 없는 키를 삭제하려고 했다)
                else:
                    return True  # 정상적으로 삭제됐다

    def exists(self, key: str) -> bool:
        """키의 존재 여부를 반환한다. 값의 내용과 관계없이 존재하면 True를 반환한다."""
        expired = self._expire_if_needed(key)
        if expired is True: # 해당 키가 이미 만료되었는가?
            return False

        if self._data.contains(key) is False: # 해시맵에 검색하려고 하는 key가 없다
            return False
        else:                                 # 키가 존재한다
            return True

    def dsize(self) -> int:
        """현재 저장된 키의 개수를 반환한다."""
        self._purge_expired()    # 사이즈를 측정하기 전에 만료된 데이터를 정리하자

        return self._data.size() # 해시맵 사이즈 반환

    def keys(self) -> list:
        """저장된 키를 문자열 목록으로 반환한다. 순서·패턴 매칭은 요구하지 않는다."""
        self._purge_expired()    # 키 목록을 출력하기 전에 만료된 데이터를 정리하자

        return self._data.keys() # 키 목록 반환
