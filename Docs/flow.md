# B5-1 Mini Redis 명령별 호출 흐름

이 문서는 사용자가 `mini-redis>`에 명령을 입력한 뒤 어떤 함수가 호출되고, 어떤 객체와 값이 바뀌며, 어떤 문자열이 출력되는지를 현재 구현 기준으로 정리한다.

기준:

- 요구사항: `Docs/Subject.txt`
- 평가 항목: `Docs/Evaluate.txt`
- 현재 코드: Git `16ce6e5` 이후 작업 트리
- 보너스 기능은 포함하지 않는다.

---

## 0. 전체 구조

```text
사용자 입력
  │
  ▼
main.py
  run_repl()
  ├─ parse_input()
  └─ execute_command()
       │
       ▼
store.py
  Store
  ├─ _data: HashMap
  ├─ _lru: DoublyLinkedList
  ├─ _expiry_heap: MinHeap
  ├─ _used_memory: int
  ├─ _maxmemory: int
  └─ _evicted_keys: int
       │
       ├─ hash_map.py
       ├─ doubly_linked_list.py
       └─ min_heap.py
```

`run_repl()`은 반복문 밖에서 `Store()`를 한 번만 만든다. 따라서 한 REPL 세션에서 성공한 명령의 상태가 다음 명령으로 이어진다. 프로그램을 종료하고 다시 실행하면 새 Store가 만들어지며, 파일 저장 기능은 없다.

---

## 1. 같은 키를 나타내는 객체 관계

키 `"a"`, 값 `"A"`를 저장한 뒤의 핵심 관계는 다음과 같다.

```text
HashMap._buckets[index]
└─ 해시맵 버킷 Node
   └─ data: HashEntry
      ├─ key: "a"                  # str
      └─ value: lru_node            # LRU 리스트의 Node
           └─ data: StoreEntry
              ├─ key: "a"          # str
              ├─ value: "A"        # str
              └─ expire_at: None    # Optional[float]
```

구분해야 할 객체:

| 이름 | 실제 타입 | 역할 |
| --- | --- | --- |
| 해시맵 버킷 Node | `doubly_linked_list.Node` | 한 버킷의 체이닝 연결을 담당한다. |
| `HashEntry` | `hash_map.HashEntry` | 해시 키와 LRU Node 참조를 묶는다. |
| LRU Node | `doubly_linked_list.Node` | 전체 키의 최근 사용 순서를 연결한다. |
| `StoreEntry` | `store.StoreEntry` | 실제 문자열 key/value와 현재 expire_at을 가진다. |
| 저장 값 | `str` | 예시에서는 `"A"`다. |

두 Node는 같은 `Node` 클래스로 만들지만 서로 다른 객체이고 서로 다른 리스트에 속한다. 해시맵 체인의 `prev`/`next`와 LRU 순서의 `prev`/`next`는 공유되지 않는다.

`HashMap.get("a")`가 반환하는 것은 문자열 `"A"`가 아니라 LRU Node다. 실제 값은 `lru_node.data.value`로 읽는다.

---

## 2. 공통 REPL 흐름

입력 예시:

```text
SET greeting "안녕 세상"
```

호출 흐름:

```text
main.py: run_repl()
  │
  ├─ input("mini-redis> ")
  │    ├─ Ctrl+C → KeyboardInterrupt 처리 → 줄바꿈 → 종료
  │    └─ Ctrl+D → EOFError 처리 → 줄바꿈 → 종료
  │
  ├─ parse_input(line)
  │    └─ shlex.split(line)
  │         └─ ["SET", "greeting", "안녕 세상"]
  │
  ├─ 빈 토큰이면 다음 입력으로 이동
  │
  ├─ 첫 토큰이 EXIT 또는 QUIT이면 반복 종료
  │
  ├─ execute_command(store, tokens)
  │    ├─ command = tokens[0].upper()
  │    ├─ 인자 개수와 고정 하위 명령 검사
  │    ├─ 필요한 Store 메서드 호출
  │    └─ 출력할 문자열 반환
  │
  └─ 반환값이 None이 아니면 print(result)
```

`shlex.split()`이 닫히지 않은 따옴표 때문에 `ValueError`를 내면 `run_repl()`은 `(error) ERR syntax error`를 출력하고 다음 입력을 받는다. `execute_command()`에서 지원하지 않는 명령은 unknown command 문자열을 반환한다.

명령어와 `CONFIG SET MAXMEMORY`, `INFO MEMORY`의 고정 단어만 대문자로 바꾸어 비교한다. key와 value의 원래 대소문자는 보존된다.

---

## 3. 이중 연결 리스트의 O(1) 연산

`DoublyLinkedList`는 `head`, `tail`을 가지고 각 Node는 `prev`, `next`를 가진다.

```text
head                                               tail
 ↓                                                   ↓
[Node A | prev=None | next=B] ⇄ [Node B] ⇄ [Node C | next=None]
```

- `insert_front(data)`: 새 Node를 만들고 기존 head 앞에 연결한다.
- `insert_back(data)`: 새 Node를 만들고 기존 tail 뒤에 연결한다.
- `remove_front()`, `remove_back()`: 끝점 참조를 이용해 해당 Node를 분리한다.
- `remove_node(node)`: 전달받은 Node의 양옆 참조만 다시 연결한다.
- `move_to_front(node)`: 전달받은 같은 Node를 현재 위치에서 분리해 head로 옮긴다.

`remove_node()`와 `move_to_front()`가 O(1)인 이유는 노드를 찾기 위한 순회가 함수 안에 없기 때문이다. 호출자가 정확한 Node 참조를 이미 전달한다. LRU에서는 HashMap이 이 Node 참조를 제공한다.

---

## 4. 체이닝 HashMap 흐름

### 4.1 해시 인덱스

`HashMap._hash(key)`는 문자열을 왼쪽부터 읽는다.

```text
result = 0
각 문자 letter에 대해:
    result = (result * 37 + ord(letter)) % capacity
```

예를 들어 같은 문자로 구성된 `"ab"`와 `"ba"`라도 앞선 결과에 37을 곱하므로 문자 순서가 계산에 반영된다. 반환값은 항상 `0 <= index < capacity`다.

### 4.2 조회와 충돌 해결

```text
HashMap.get(key)
  └─ _find_node(key)
       ├─ index = _hash(key)
       ├─ bucket = _buckets[index]
       └─ bucket.head부터 next로 이동
            ├─ current.data는 HashEntry
            ├─ current.data.key == key이면 현재 버킷 Node 반환
            └─ 끝까지 없으면 None
```

서로 다른 키가 같은 index를 가져도 같은 버킷 연결 리스트에 함께 저장한다. 이것이 체이닝이다. 찾을 때 해시값만 믿지 않고 `HashEntry.key` 문자열을 다시 비교한다.

### 4.3 추가와 확장

```text
HashMap.put(key, value)
  ├─ _find_node(key)
  ├─ 기존 키이면 HashEntry.value만 교체
  └─ 새 키이면
       ├─ HashEntry(key, value) 생성
       ├─ 해당 버킷의 뒤에 삽입
       ├─ _size += 1
       └─ _load_factor() > 0.75이면 _resize()
```

초기 capacity는 8이다. 여섯 개 저장 시 `6 / 8 == 0.75`이므로 확장하지 않고, 일곱 번째 새 키에서 `7 / 8 > 0.75`가 되어 16으로 확장한다.

`_resize()`는 capacity를 먼저 2배로 바꾸고 새 버킷들을 만든다. 모듈러 연산의 기준이 달라졌으므로 기존 모든 `HashEntry`를 새 index로 다시 계산해 재배치한다. `_size`는 그대로 유지한다.

평균 조회는 O(1)이지만 충돌이 한 버킷에 집중되면 체인 길이에 비례한다. 확장 한 번은 현재 엔트리 수에 비례한다.

---

## 5. 최소 힙 흐름

`MinHeap._items`는 `(expire_at, key)` 튜플을 담는 Python 리스트이며, 비교 기준은 튜플의 첫 원소인 절대 만료 시각이다.

```text
index i의 부모       = (i - 1) // 2
왼쪽 자식            = 2 * i + 1
오른쪽 자식          = 2 * i + 2
```

- `push(item)`: 배열 끝에 넣고 `_heapify_up()`으로 부모와 비교한다. O(log n).
- `peek()`: 루트인 `_items[0]`을 읽는다. O(1).
- `pop()`: 루트와 마지막 항목을 바꾸고 마지막 항목을 제거한 뒤 `_heapify_down()`한다. O(log n).

가장 이른 만료 후보가 항상 루트에 있으므로 `Store._purge_expired()`는 전체 키를 순회하지 않고 현재 시각 이전 후보만 연속해서 처리할 수 있다.

---

## 6. SET

입력 예시:

```text
SET a A
```

CLI 호출 흐름:

```text
run_repl()
  └─ parse_input("SET a A")
       └─ ["SET", "a", "A"]
            └─ execute_command(store, tokens)
                 ├─ 인자 3개 확인
                 ├─ store.set("a", "A")
                 ├─ True  → "OK"
                 └─ False → OOM 오류 문자열
```

### 6.1 새 키 SET

```text
Store.set("a", "A")
  ├─ _expire_if_needed("a")
  ├─ entry_size = _entry_size("a", "A")       # 2
  ├─ 단일 엔트리 OOM 검사
  ├─ lru_node = _data.get("a")                 # None
  ├─ entry = StoreEntry("a", "A")
  ├─ lnode = _lru.insert_front(entry)           # 새 LRU Node
  ├─ _data.put("a", lnode)                     # key → LRU Node
  ├─ _used_memory += 2
  ├─ 필요하면 _evict_lru() 반복
  └─ True
```

빈 Store에서 실행한 직후:

```text
_data.get("a") is lnode
_lru.head is lnode
_lru.tail is lnode
lnode.data.key == "a"
lnode.data.value == "A"
lnode.data.expire_at is None
_used_memory == 2
```

### 6.2 기존 키 SET

```text
Store.set("a", "NEW")
  ├─ 기존 lru_node 조회
  ├─ old_value = lru_node.data.value
  ├─ lru_node.data.value = "NEW"
  ├─ _used_memory += new_size - old_size
  ├─ lru_node.data.expire_at = None
  ├─ _lru.move_to_front(lru_node)
  ├─ 필요하면 _evict_lru() 반복
  └─ True
```

기존 LRU Node를 재사용하므로 같은 키를 여러 번 SET해도 노드가 중복되지 않는다. 성공한 덮어쓰기는 과거 TTL을 초기화한다. 과거 최소 힙 튜플은 즉시 제거하지 않고 나중에 무효 기록으로 판별한다.

### 6.3 단일 엔트리 OOM

`maxmemory == 4`에서 `SET a 1234`의 엔트리 크기는 `1 + 4 == 5`다.

```text
entry_size > _maxmemory
  └─ False 반환
```

이 검사는 값이나 TTL을 바꾸기 전에 수행된다. 따라서 기존 키를 덮어쓰려던 경우에도 기존 값과 TTL, LRU 순서, used_memory가 보존된다.

---

## 7. GET

입력 예시:

```text
GET a
```

전체 호출 흐름:

```text
execute_command()
  ├─ 인자 2개 확인
  ├─ value = Store.get("a")
  │    ├─ _expire_if_needed("a")
  │    │    ├─ 키 없음 → False
  │    │    ├─ TTL 없음/미도래 → False
  │    │    └─ 만료됨 → del_key("a") → True
  │    ├─ 만료되었으면 None
  │    ├─ lru_node = _data.get("a")
  │    ├─ 없으면 None
  │    └─ 있으면
  │         ├─ _lru.move_to_front(lru_node)
  │         └─ lru_node.data.value
  ├─ None이면 "(nil)"
  └─ 문자열이면 큰따옴표를 붙여 반환
```

핵심 순서는 `TTL 확인 → 필요하면 삭제 → 값 조회 → 성공한 경우만 LRU 갱신 → 값 반환`이다.

예시 상태 변화:

```text
GET 전  MRU → c → b → a ← LRU
GET a
GET 후  MRU → a → c → b ← LRU
```

없는 키와 만료된 키는 LRU를 갱신하지 않는다.

---

## 8. DEL

입력 예시:

```text
DEL a
```

호출 흐름:

```text
execute_command()
  ├─ 인자 2개 확인
  └─ Store.del_key("a")
       ├─ lru_node = _data.get("a")
       ├─ 없으면 False
       ├─ entry_size 계산
       ├─ _data.remove("a")
       │    └─ 해당 해시맵 버킷 Node 분리, HashMap._size -= 1
       ├─ _lru.remove_node(lru_node)
       ├─ _used_memory -= entry_size
       ├─ 이미 만료된 키였다면 False
       └─ 그 외에는 True
```

CLI는 True를 `(integer) 1`, False를 `(integer) 0`으로 바꾼다.

TTL 힙에서 해당 튜플을 임의 위치 검색해 즉시 삭제하지 않는다. 데이터가 사라진 뒤 남은 튜플은 `_purge_expired()`가 꺼냈을 때 `_data.get(key) is None`으로 판별해 버린다. 따라서 TTL의 효력은 데이터 삭제와 함께 사라지지만 힙 기록의 물리적 정리는 지연될 수 있다.

---

## 9. EXISTS

```text
execute_command()
  └─ Store.exists(key)
       ├─ _expire_if_needed(key)
       ├─ 만료되어 삭제됐으면 False
       └─ _data.contains(key)
            └─ HashMap._find_node(key)의 결과로 존재 여부 판단
```

True는 `(integer) 1`, False는 `(integer) 0`이다. 값이 빈 문자열이나 `"0"`인지가 아니라 HashEntry가 실제로 존재하는지를 확인한다. EXISTS는 성공해도 LRU 순서를 바꾸지 않는다.

---

## 10. DBSIZE

```text
execute_command()
  └─ Store.dsize()
       ├─ _purge_expired()
       └─ _data.size()
```

`_purge_expired()`가 현재 시각까지의 유효한 만료 엔트리를 먼저 삭제하므로 이미 만료된 키는 개수에 포함되지 않는다. 결과는 `(integer) N` 형식이다.

---

## 11. KEYS

```text
execute_command()
  └─ Store.keys()
       ├─ _purge_expired()
       └─ HashMap.keys()
            ├─ 크기 _size인 결과 리스트 준비
            ├─ 모든 버킷을 순회
            └─ 각 HashEntry.key를 한 번씩 기록
```

키가 없으면 `(empty array)`다. 키가 있으면 `1. "key"` 형식의 여러 줄 문자열을 만든다. 버킷 순회 순서에 따른 결과이며 정렬은 요구하지 않는다.

시간 복잡도는 버킷 수를 B, 키 수를 n이라 할 때 O(B+n)이다. 모든 키를 결과에 담으므로 추가 메모리와 출력 비용도 n에 비례한다.

---

## 12. CONFIG SET maxmemory

입력 예시:

```text
CONFIG SET maxmemory 30
```

호출 흐름:

```text
execute_command()
  ├─ 토큰 4개 확인
  ├─ tokens[1] == SET, tokens[2] == MAXMEMORY 확인
  ├─ int(tokens[3])
  └─ Store.set_maxmemory(30)
       ├─ 음수 → False
       └─ 0 이상 → _maxmemory 갱신 → True
```

- `0`: 무제한
- 양수: 바이트 단위 제한
- 음수 또는 정수 변환 실패: `(error) ERR value is not an integer or out of range`

현재 구현은 제한값을 낮추는 CONFIG 자체에서는 기존 키를 즉시 제거하지 않는다. 다음 성공한 SET 뒤 전체 사용량이 제한을 넘으면 LRU 제거를 수행한다. Subject가 CONFIG 시점의 즉시 제거 여부를 고정하지 않았기 때문에 선택한 내부 정책이다.

---

## 13. INFO memory

```text
execute_command()
  └─ Store.info_memory()
       ├─ _purge_expired()
       └─ (_used_memory, _maxmemory, _evicted_keys)
```

CLI 출력:

```text
used_memory:<number>
maxmemory:<number>
evicted_keys:<number>
```

공식 메모리 모델:

```text
entry_size = len(key.encode("utf-8")) + len(value.encode("utf-8"))
used_memory = 현재 모든 엔트리 entry_size의 합
```

Node, HashEntry, StoreEntry, 버킷, 참조와 힙 튜플의 오버헤드는 현재 공식 값에서 제외한다. 한글은 글자 수가 아니라 UTF-8 바이트 수로 센다.

---

## 14. LRU 자동 제거

`maxmemory > 0`인 성공한 SET 뒤 `used_memory > maxmemory`이면 다음 흐름을 반복한다.

```text
Store.set()
  └─ while _used_memory > _maxmemory
       └─ _evict_lru()
            ├─ lru_tail = _lru.tail
            ├─ key = lru_tail.data.key
            ├─ del_key(key)
            │    ├─ HashMap에서 제거
            │    ├─ LRU Node 제거
            │    └─ used_memory 감소
            └─ 정상 LRU 제거이면 _evicted_keys += 1
```

`head`는 MRU, `tail`은 LRU이므로 제거 후보를 찾기 위한 리스트 순회가 필요 없다.

메모리 6바이트 예시:

```text
SET a A → [a]             used=2
SET b B → [b, a]          used=4
SET c C → [c, b, a]       used=6
GET a   → [a, c, b]       used=6
SET d D → [d, a, c, b]    used=8
evict b → [d, a, c]       used=6, evicted_keys=1
```

일반 DEL과 TTL 만료는 메모리를 줄이지만 `evicted_keys`는 늘리지 않는다. 이 값은 메모리 제한 때문에 LRU 정책으로 제거된 키의 누적 수다.

---

## 15. EXPIRE

입력 예시:

```text
EXPIRE a 10
```

호출 흐름:

```text
execute_command()
  ├─ 인자 3개 확인
  ├─ seconds = int(tokens[2])
  └─ Store.expire("a", 10)
       ├─ _expire_if_needed("a")
       ├─ lnode = _data.get("a")
       ├─ 키가 없으면 False
       ├─ seconds <= 0이면 del_key("a") 후 True
       └─ 양수이면
            ├─ timer = time.time() + seconds
            ├─ lnode.data.expire_at = timer
            ├─ _expiry_heap.push((timer, "a"))
            └─ True
```

True는 `(integer) 1`, False는 `(integer) 0`이다. EXPIRE는 LRU 사용으로 취급하지 않으므로 노드를 MRU로 옮기지 않는다.

TTL을 다시 설정하면 같은 key의 과거 튜플과 새 튜플이 힙에 함께 남을 수 있다. 실제 유효 만료 시각은 StoreEntry의 `expire_at` 하나다.

---

## 16. TTL

```text
execute_command()
  └─ Store.ttl(key)
       ├─ _expire_if_needed(key)
       ├─ 만료되어 삭제됐거나 키가 없으면 -2
       ├─ expire_at is None이면 -1
       ├─ remaining = expire_at - time.time()
       ├─ 경계 사이에 만료됐으면 삭제 후 -2
       └─ int(remaining)
```

결과 의미:

| 값 | 의미 |
| --- | --- |
| `-2` | 키가 없거나 방금 만료되어 삭제됨 |
| `-1` | 키는 있지만 TTL이 없음 |
| `0` 이상 | 정수로 내린 남은 초 |

`int()`가 소수 부분을 버리므로 `EXPIRE a 10` 직후 `TTL a`는 보통 9다. TTL 조회 자체는 LRU 순서를 바꾸지 않는다.

---

## 17. TTL 지연 삭제와 `_purge_expired()`

예시:

```text
SET a old
EXPIRE a 10       # 힙 기록 (t1, "a")
EXPIRE a 30       # 현재 expire_at=t2, 힙 기록 (t2, "a")도 추가
```

t1이 지난 뒤 힙 루트의 과거 기록을 처리하는 흐름:

```text
_purge_expired()
  ├─ current = time.time()
  ├─ heap_item = _expiry_heap.peek()
  ├─ 기록 시각이 미래이면 종료
  ├─ 도래했으면 pop()
  ├─ lru_node = _data.get(key)
  │    └─ 키가 이미 없으면 오래된 기록이므로 continue
  ├─ current_expire_at = lru_node.data.expire_at
  │    └─ 기록 시각과 다르면 오래된 기록이므로 continue
  └─ 같으면 del_key(key)
```

따라서 오래된 t1이 도래해도 현재 t2가 다르면 새 값을 삭제하지 않는다. SET 덮어쓰기로 현재 `expire_at`이 None이 된 경우도 과거 기록과 다르므로 무시한다.

`DBSIZE`, `KEYS`, `INFO memory`는 특정 key 하나가 아니라 저장소 전체 결과를 내므로 먼저 `_purge_expired()`를 호출한다. `GET`, `EXISTS`, `SET`, `EXPIRE`, `TTL`은 대상 key에 `_expire_if_needed()`를 사용한다.

---

## 18. 오류 흐름

### 18.1 인자 개수 오류

각 명령 분기에서 필요한 토큰 수를 먼저 비교한다.

```text
GET a extra
  └─ (error) ERR wrong number of arguments for 'get' command
```

Store 메서드는 호출되지 않으므로 상태가 바뀌지 않는다.

### 18.2 정수 파싱 오류

`CONFIG SET maxmemory`와 `EXPIRE`는 `int()`의 `ValueError`를 해당 표준 오류로 바꾼다.

```text
(error) ERR value is not an integer or out of range
```

### 18.3 문법 오류

- 닫히지 않은 따옴표: `parse_input()` 단계에서 처리
- 잘못된 CONFIG/INFO 하위 명령: `execute_command()`에서 처리

둘 다 `(error) ERR syntax error`다.

### 18.4 알 수 없는 명령

어떤 지원 분기에도 해당하지 않으면 입력된 첫 토큰을 포함해 다음 문자열을 반환한다.

```text
(error) ERR unknown command 'HELLO'
```

이 오류들은 결과 문자열로 처리되므로 같은 Store를 유지한 채 다음 입력으로 진행한다.

---

## 19. 명령과 핵심 함수 대응표

| 명령 | 중심 함수 | 직접 사용하는 하위 기능 | 주요 상태 변화 |
| --- | --- | --- | --- |
| `SET` | `Store.set()` | `_expire_if_needed`, `_entry_size`, HashMap, LRU, `_evict_lru` | 데이터·LRU·TTL·메모리, 필요 시 제거 수 |
| `GET` | `Store.get()` | `_expire_if_needed`, HashMap, `move_to_front` | 성공한 경우 LRU 순서 |
| `DEL` | `Store.del_key()` | HashMap.remove, LRU.remove_node, `_entry_size` | 데이터·LRU·메모리 |
| `EXISTS` | `Store.exists()` | `_expire_if_needed`, HashMap.contains | 만료 시 삭제 가능 |
| `DBSIZE` | `Store.dsize()` | `_purge_expired`, HashMap.size | 만료 시 삭제 가능 |
| `KEYS` | `Store.keys()` | `_purge_expired`, HashMap.keys | 만료 시 삭제 가능 |
| `CONFIG SET maxmemory` | `Store.set_maxmemory()` | 정수·범위 검사 | 최대 메모리 제한 |
| `INFO memory` | `Store.info_memory()` | `_purge_expired` | 만료 시 삭제 가능 |
| `EXPIRE` | `Store.expire()` | `_expire_if_needed`, MinHeap.push | 현재 만료 시각과 힙 기록 |
| `TTL` | `Store.ttl()` | `_expire_if_needed`, time | 만료 시 삭제 가능 |
| `EXIT`, `QUIT` | `run_repl()` | 첫 토큰 비교 | 반복 종료 |

---

## 20. 평가 설명용 핵심 문장

- 이중 연결 리스트: “이미 얻은 Node 참조의 양옆 링크와 head/tail만 바꾸므로 삽입·삭제·이동이 O(1)입니다.”
- 해시 함수: “앞선 결과에 37을 곱하고 현재 문자의 코드값을 더한 뒤 capacity로 나머지를 구해 문자 내용과 순서를 index에 반영합니다.”
- 체이닝: “같은 index의 HashEntry를 버킷 연결 리스트에 저장하고 실제 key 문자열을 순회 비교합니다.”
- 확장: “새 키 추가 뒤 로드 팩터가 0.75를 초과하면 capacity를 두 배로 만들고 모든 엔트리를 새 capacity로 다시 해싱합니다.”
- LRU: “HashMap이 key로 LRU Node를 평균 O(1)에 찾고, 이중 연결 리스트가 그 Node를 O(1)에 이동하므로 평균 O(1) 갱신이 가능합니다.”
- TTL 힙: “가장 이른 만료 후보가 루트에 있어 전체 키를 훑지 않고 다음 만료 후보를 확인할 수 있습니다.”
- eviction: “SET 뒤 사용량이 제한을 넘으면 LRU tail을 데이터와 리스트에서 제거하고 크기를 뺀 뒤 evicted_keys를 증가시키는 과정을 제한 이하가 될 때까지 반복합니다.”
- GET: “대상 TTL을 먼저 검사해 만료됐으면 삭제하고 nil을 반환하며, 살아 있는 값을 찾은 경우에만 LRU Node를 앞으로 옮깁니다.”
