# CLI 기반 Mini Redis

Python의 내장 Key-Value 컬렉션으로 저장소를 대신하지 않고, 이중 연결 리스트·체이닝 해시맵·최소 힙을 직접 구현해 조합한 인메모리 문자열 저장소다. Redis의 기본 문자열 명령, LRU 기반 메모리 제거, TTL 만료와 Redis 스타일 CLI 출력을 지원한다.

이 프로젝트의 학습 목표는 구현 코드를 근거로 해시 함수와 체이닝 충돌 해결, 해시맵과 이중 연결 리스트를 결합한 평균 O(1) LRU 갱신, 최소 힙을 이용한 TTL 후보 관리, 메모리 집계부터 LRU 제거와 누적 카운트까지의 흐름을 설명하는 것이다.

## 실행 환경

- 과제 기준: Python 3.8 이상
- 실제 검증 환경: Python 3.14.6
- 외부 패키지 없음

```bash
python3 main.py
```

실행하면 `mini-redis>` 프롬프트가 나타난다. `exit` 또는 `quit`을 입력하면 종료된다. 입력 대기 중 `Ctrl+C`와 `Ctrl+D`도 traceback 없이 프로그램을 종료한다.

## 지원 명령

### 문자열 명령

| 명령 | 설명 | 주요 결과 |
| --- | --- | --- |
| `SET key value` | 문자열 키와 값을 저장한다. 기존 키는 덮어쓰고 TTL을 초기화한다. | 성공 `OK`, 단일 엔트리 초과 시 OOM |
| `GET key` | 유효한 값을 조회하고 성공한 조회만 LRU를 갱신한다. | `"value"` 또는 `(nil)` |
| `DEL key` | 키와 연관된 데이터·LRU·TTL 효력을 제거한다. | `(integer) 1` 또는 `(integer) 0` |
| `EXISTS key` | 유효한 키의 존재 여부를 확인한다. | `(integer) 1` 또는 `(integer) 0` |
| `DBSIZE` | 만료 항목을 정리한 뒤 현재 키 수를 반환한다. | `(integer) N` |
| `KEYS` | 만료 항목을 정리한 뒤 전체 키를 반환한다. 패턴 매칭과 정렬은 지원하지 않는다. | 번호가 붙은 키 목록 또는 `(empty array)` |

### 메모리 명령

| 명령 | 설명 | 주요 결과 |
| --- | --- | --- |
| `CONFIG SET maxmemory bytes` | 0 이상의 바이트 제한을 설정한다. 0은 무제한이다. | `OK` 또는 정수 오류 |
| `INFO memory` | 현재 사용량, 제한, LRU 제거 누적 횟수를 반환한다. | `used_memory`, `maxmemory`, `evicted_keys` |

### TTL 명령

| 명령 | 설명 | 주요 결과 |
| --- | --- | --- |
| `EXPIRE key seconds` | 존재하는 키에 초 단위 TTL을 설정한다. 0 이하는 즉시 만료한다. | `(integer) 1` 또는 `(integer) 0` |
| `TTL key` | 키의 남은 TTL을 정수 초로 반환한다. | 남은 초, TTL 없음 `-1`, 키 없음 `-2` |

키 기반 명령은 본 동작 전에 대상 키의 만료 여부를 확인한다. 만료된 키는 삭제한 뒤 없는 키처럼 처리한다.

## 입력과 출력 규칙

- 명령어와 고정 하위 키워드는 대소문자를 구분하지 않는다.
- 키와 값의 원래 대소문자는 유지한다.
- 공백 없는 값과 큰따옴표로 감싼 값을 지원한다.
- 구분용 큰따옴표는 저장 값이나 메모리 사용량에 포함하지 않는다.
- 빈 입력은 출력 없이 다음 프롬프트로 넘어간다.
- 닫히지 않은 따옴표는 명령을 실행하지 않고 문법 오류로 처리한다.

```text
mini-redis> SET greeting "안녕 세상"
OK
mini-redis> GET greeting
"안녕 세상"
```

표준 오류 형식은 다음과 같다.

```text
(error) ERR unknown command '<cmd>'
(error) ERR wrong number of arguments for '<cmd>' command
(error) ERR value is not an integer or out of range
(error) OOM command not allowed when used_memory > 'maxmemory'
(error) ERR syntax error
```

## 자료구조

### 이중 연결 리스트

`doubly_linked_list.py`의 `Node`는 `prev`, `next`, `data`를 보관한다. `DoublyLinkedList`는 다음 연산을 제공하며, 이미 연결된 노드의 참조를 이용하는 삽입·삭제·이동은 전체 순회 없이 O(1)로 처리한다.

- `insert_front`
- `insert_back`
- `remove_front`
- `remove_back`
- `remove_node`
- `move_to_front`

### 체이닝 해시맵

`hash_map.py`의 `HashMap`은 버킷마다 별도의 이중 연결 리스트를 두어 충돌을 체이닝으로 해결한다. 문자열의 각 문자를 읽어 직접 버킷 인덱스를 계산하며, 동일한 버킷에 들어온 키도 실제 문자열 키를 다시 비교한다.

- 공개 연산: `put`, `get`, `remove`, `contains`, `keys`, `size`
- 초기 버킷 수: 8
- 로드 팩터: `저장된 키 수 / 버킷 수`
- 새 키 추가 결과 로드 팩터가 0.75를 초과하면 버킷 수를 2배로 늘린다.
- 확장 시 기존 엔트리를 새 버킷 수에 맞게 다시 해싱한다.

해시 조회는 평균 O(1)이며, 충돌이 한 버킷에 집중된 최악의 경우에는 체인의 길이에 비례한다. 버킷 확장은 기존 엔트리 수에 비례한다.

### 최소 힙

`min_heap.py`의 `MinHeap`은 `(expire_at, key)` 튜플을 배열 기반 완전 이진 트리 형태로 보관한다. 만료 시각을 기준으로 `_heapify_up`과 `_heapify_down`을 직접 수행한다.

- `push`: O(log n)
- `peek`: O(1)
- `pop`: O(log n)
- `size`: O(1)

가장 이른 만료 후보가 루트에 있으므로 전체 키를 순회하지 않고 다음 만료 후보를 확인할 수 있다.

## Store 내부 구조와 LRU

`store.py`의 `Store`는 해시맵, LRU 이중 연결 리스트, 최소 힙을 함께 관리한다.

```text
해시맵 버킷 Node
└─ data: HashEntry
   ├─ key: "a"
   └─ value: LRU Node
      └─ data: StoreEntry
         ├─ key: "a"
         ├─ value: "A"
         └─ expire_at: None 또는 절대 시각
```

해시맵 버킷의 `Node`와 LRU 리스트의 `Node`는 서로 다른 객체다. 해시맵은 `key → LRU Node` 관계를 저장하므로 키를 찾은 뒤 LRU 리스트를 다시 순회하지 않고 같은 노드를 이동하거나 삭제할 수 있다.

- LRU 리스트의 `head`: 가장 최근에 사용한 항목(MRU)
- LRU 리스트의 `tail`: 가장 오래 사용하지 않은 항목(LRU)
- 새 키 `SET`: 새 `StoreEntry`를 리스트 앞에 삽입하고 반환된 LRU 노드를 해시맵에 저장
- 기존 키 `SET`: 값을 변경하고 TTL을 초기화한 뒤 기존 LRU 노드를 앞으로 이동
- 성공한 `GET`: 기존 LRU 노드를 앞으로 이동
- 없는 키 또는 만료된 키의 `GET`: LRU 순서를 변경하지 않음
- `DEL`: 해시맵과 LRU에서 같은 항목을 제거하고 TTL 효력을 없앰

해시맵의 평균 O(1) 조회와 이중 연결 리스트의 O(1) 노드 이동을 조합해 평균 O(1) LRU 갱신을 수행한다.

## 메모리 관리와 자동 제거

메모리 사용량은 문자열 키와 값의 UTF-8 바이트 수만 합산한다. 노드, 포인터, 버킷, Python 객체 등의 자료구조 오버헤드는 포함하지 않는다.

```text
used_memory = Σ(len(key.encode("utf-8")) + len(value.encode("utf-8")))
```

- 초기 `maxmemory`는 0이며 무제한을 뜻한다.
- 새 키 저장은 엔트리 크기를 더한다.
- 덮어쓰기는 이전 크기와 새 크기의 차이를 반영한다.
- 일반 삭제, TTL 만료와 LRU 제거는 삭제된 엔트리 크기를 뺀다.
- 양수 제한과 정확히 같은 크기의 엔트리는 허용한다.
- 단일 키·값 엔트리 자체가 양수 제한보다 크면 저장하지 않고 OOM을 반환한다.
- 성공한 `SET` 뒤 전체 사용량이 제한을 초과하면 `tail`의 LRU 항목부터 제한 이하가 될 때까지 반복 제거한다.
- 메모리 제한 때문에 제거한 항목만 `evicted_keys`를 증가시킨다. 일반 `DEL`과 TTL 만료는 증가시키지 않는다.

현재 구현은 제한을 낮추는 `CONFIG SET maxmemory` 자체에서는 기존 데이터를 즉시 제거하지 않는다. 이후 성공한 `SET`에서 제한을 초과하면 LRU 제거를 시작한다. 이는 원문이 고정하지 않은 내부 정책이다.

## TTL 관리

각 `StoreEntry`는 현재 유효한 절대 만료 시각을 `expire_at`에 저장한다. 최소 힙에는 `(expire_at, key)` 후보를 추가한다.

TTL을 다시 설정하거나 `SET`으로 초기화하면 과거 힙 기록이 남을 수 있으므로 지연 삭제를 사용한다. 힙에서 꺼낸 시각과 현재 엔트리의 `expire_at`이 같을 때만 실제 데이터를 만료시킨다. 키가 없거나 현재 시각과 다르면 오래된 기록만 버린다.

- 키 기반 명령은 대상 키를 사용하기 전에 만료 여부를 확인한다.
- `DBSIZE`, `KEYS`, `INFO memory`는 결과를 만들기 전에 현재까지 만료된 힙 항목을 정리한다.
- 백그라운드 만료 작업은 사용하지 않는다.
- 남은 TTL은 `int(expire_at - now)`로 소수 부분을 버린다.
- `seconds <= 0`은 존재하는 키를 즉시 만료시키는 정책을 사용한다.
- 기존 키의 성공한 `SET`은 TTL을 없애며 이후 `TTL` 결과는 `-1`이다.

## 프로젝트 구조

```text
B5-1/
├── Docs/
│   ├── Subject.txt          # 과제 원문
│   ├── Evaluate.txt         # 평가 항목
│   ├── Study.md             # 개념과 구현 흐름 정리
│   └── CHECK.md             # 구현·검증 체크리스트
├── doubly_linked_list.py    # Node와 이중 연결 리스트
├── hash_map.py              # HashEntry와 체이닝 해시맵
├── min_heap.py              # TTL 후보용 최소 힙
├── store.py                 # 데이터·LRU·메모리·TTL 통합
├── main.py                  # 파싱·명령 실행·REPL
└── README.md
```

## 실행 예시

```text
mini-redis> CONFIG SET maxmemory 30
OK
mini-redis> SET user:1 Alice
OK
mini-redis> SET user:2 Bob
OK
mini-redis> SET user:3 Charlie
OK
mini-redis> GET user:1
(nil)
mini-redis> INFO memory
used_memory:22
maxmemory:30
evicted_keys:1
mini-redis> DBSIZE
(integer) 2
mini-redis> KEYS
1. "user:2"
2. "user:3"
```

키 출력 순서는 보장하지 않는다.

TTL 예시는 다음과 같다. 실제 남은 초는 명령 실행 시점에 따라 달라질 수 있다.

```text
mini-redis> EXPIRE user:2 3
(integer) 1
mini-redis> TTL user:2
(integer) 2
mini-redis> GET user:2
(nil)
mini-redis> TTL user:2
(integer) -2
```

마지막 두 명령은 설정한 시간이 지난 뒤 실행한 결과다.

## 구현 범위와 제약

- `dict`, `set`, `collections`로 해시맵이나 캐시를 대체하지 않는다.
- Python 리스트는 버킷 참조와 최소 힙의 배열 저장소처럼 제한된 용도로 사용한다.
- 네트워크 통신은 구현하지 않는다.
- 파일 저장·복구 등 데이터 영속성은 구현하지 않는다.
- Redis의 List, Set, Sorted Set 같은 복잡 자료형은 구현하지 않는다.
- 멀티스레딩과 락 같은 동시성 기능은 구현하지 않는다.
- 동적 배열, Pub/Sub 등의 보너스 과제는 포함하지 않는다.

구현과 통합 실행 검증 과정은 [Docs/CHECK.md](Docs/CHECK.md), 학습한 개념과 세부 설계 선택은 [Docs/Study.md](Docs/Study.md)에서 확인할 수 있다.
