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

## 확장 설계와 평가 관점

다음 내용은 현재 프로그램에 추가로 구현한 기능이 아니라, 조건이 달라졌을 때 필요한 자료구조와 비용을 분석한 것이다. 자세한 설명은 [Docs/Study.md](Docs/Study.md)의 12절에 정리되어 있다.

### LRU를 LFU로 바꾼다면

LFU는 마지막 사용 시점이 아니라 사용 횟수가 가장 적은 키를 제거한다. `StoreEntry`에 `frequency`만 추가하면 횟수는 기록할 수 있지만, 제거 때마다 모든 엔트리를 순회해 최솟값을 찾으므로 O(n)이 된다.

평균 O(1) 갱신과 제거를 목표로 한다면 다음 상태가 필요하다.

- `key → LFUEntry` 또는 빈도 리스트 노드를 찾는 키 조회용 해시맵
- `frequency → DoublyLinkedList` 관계를 관리하는 빈도 버킷
- 현재 가장 작은 빈도인 `min_frequency`
- 같은 빈도 안에서 제거 순서를 결정할 LRU 순서

새 키는 빈도 1 리스트에 넣고 `min_frequency`를 1로 만든다. 성공한 `GET`과 기존 키 `SET`은 노드를 빈도 `f` 리스트에서 O(1)로 분리해 `f + 1` 리스트로 이동한다. eviction은 최소 빈도 리스트의 `tail`을 선택한다. `DEL`과 TTL 만료도 키 맵뿐 아니라 빈도 리스트와 최소 빈도를 함께 정리해야 한다.

접근으로 최소 빈도 리스트가 비었다면 방금 이동한 `f + 1`로 갱신할 수 있지만, 임의 삭제로 비었다면 다음 빈도가 연속적이라는 보장이 없다. 이 경우 빈도 숫자를 탐색하거나, 비어 있지 않은 빈도 버킷끼리 정렬된 연결을 별도로 유지해야 한다.

동률에서는 같은 빈도 안의 LRU 키를 제거할 수 있다. 또한 누적 횟수만 사용하면 과거에 인기 있던 키가 계속 남는 문제가 있으므로 주기적 절반 감소, 접근 시 지연 감쇠, 최대·로그형 카운터 같은 노화 정책도 결정해야 한다.

| LFU 구조 | 접근 갱신 | 제거 후보 선택 | 대가 |
| --- | --- | --- | --- |
| 엔트리에 횟수만 저장 | 평균 O(1) | O(n) | 단순하지만 eviction이 느리다. |
| 빈도 최소 힙 | O(log m) | O(log m) | 갱신 전의 무효 기록이 누적될 수 있다. |
| 키 맵 + 빈도별 리스트 + 최소 빈도 | 평균 O(1) | 평균 O(1) | 빈도 버킷 순서와 모든 삭제 경로의 일관성을 관리해야 한다. |

### 데이터가 10만 건이라면

현재 구현에서 예상되는 병목은 다음과 같다.

- 해시 충돌이 한 버킷에 몰리면 `_find_node`의 체인 순회가 길어진다.
- `_resize`는 모든 엔트리를 한 번에 재해싱하므로 특정 `SET`에 O(n) 지연이 집중된다.
- 초기 용량 8과 0.75 임계값에서는 98,305번째 키에서 버킷이 262,144개로 늘어난다. 현재는 각 버킷에 빈 `DoublyLinkedList`를 미리 만들어 빈 버킷 오버헤드가 커질 수 있다.
- `KEYS`는 모든 버킷과 키를 순회하고 결과 목록과 출력 문자열을 만들어 시간 O(B+n), 추가 메모리 O(n)이 든다.
- TTL 재설정·삭제 뒤 남은 무효 힙 기록이 유효 TTL 키보다 많아질 수 있다.
- 많은 키가 동시에 만료되면 한 명령의 `_purge_expired`에 O(k log m) 작업이 집중된다.
- 큰 `SET`으로 여러 키를 제거하면 `_evict_lru`가 k번 반복된다.
- 현재 REPL은 명령을 직렬로 처리한다. 동시 요청을 추가하면서 전역 쓰기 락 하나만 사용하면 재해싱·만료 정리·`KEYS` 동안 다른 요청도 모두 대기한다.

개선안으로는 점진적 재해싱, 실제 사용 시점에만 버킷 리스트를 만드는 지연 생성, `KEYS`의 커서·페이지화, 무효 TTL 비율에 따른 힙 재구성, 명령당 만료 정리 작업량 제한을 고려할 수 있다.

더 큰 규모에서는 키 해시를 기준으로 여러 Store 샤드에 분산할 수 있다. 샤드마다 해시맵·LRU·TTL 힙·메모리 카운터를 두면 병렬 처리가 가능하지만, 전역 메모리 예산과 전역 LRU를 정확히 유지하기 어려워 샤드별 예산이나 후보 샘플링 같은 근사 정책이 필요하다. `KEYS`, `DBSIZE`, `INFO memory`도 모든 샤드의 결과를 합쳐야 하며 인기 키가 한 샤드에 몰릴 수 있다.

점진적 재해싱과 만료 정리를 작은 작업으로 나눠 이벤트 루프나 백그라운드 작업으로 처리하면 긴 정지를 줄일 수 있다. 다만 비동기 I/O만으로 CPU 중심의 해시 계산·재해싱이 빨라지는 것은 아니며, Python 스레드의 GIL이나 프로세스 간 통신 비용도 함께 고려해야 한다. 개선 전에는 p95·p99 명령 지연, 최대 체인 길이, 재해싱 시간, 유효 TTL 수 대비 힙 기록 수와 실제 프로세스 메모리를 먼저 측정한다.

### `used_memory`에 자료구조 오버헤드를 포함한다면

현재 모델은 키와 값의 UTF-8 payload만 세기 때문에 구현 환경과 관계없이 같은 데이터에 같은 결과가 나온다. 실제 오버헤드까지 포함하려면 다음 항목도 계산해야 한다.

- `StoreEntry`, `HashEntry`, 해시 버킷 Node와 LRU Node
- 노드의 `prev`, `next`, `data` 참조
- 버킷 배열 슬롯과 미리 생성한 빈 연결 리스트
- 최소 힙 배열, `(expire_at, key)` 튜플과 무효 TTL 기록
- 배열의 여유 용량과 재해싱 중 이전·새 버킷이 함께 존재하는 최대 순간 사용량

같은 문자열이나 LRU Node를 여러 구조가 참조하므로 객체 본체는 정체성 기준으로 한 번만 세어야 한다. 반대로 `sys.getsizeof`는 얕은 크기만 반환하므로 자식 객체를 별도로 순회해야 하고, 문자열 객체 크기에 payload가 이미 포함된다면 UTF-8 바이트를 다시 더하지 않아야 한다.

보정 방법은 두 가지로 나눌 수 있다.

1. 모든 제출물에 엔트리·노드·버킷 슬롯·TTL 기록의 동일한 가상 단가표를 적용한다. 실제 메모리와는 다르지만 재현 가능한 채점이 가능하다.
2. 동일한 Python·OS·아키텍처에서 `Store`가 소유한 객체 그래프를 순회해 실제 크기를 잰다. 객체 정체성으로 중복을 제거하고 빈 저장소 기준값을 포함할지 또는 뺄지 통일한다.

공정한 비교를 위해서는 동일한 데이터뿐 아니라 TTL 재설정·삭제·재해싱을 포함한 명령 이력, garbage collection 여부, 측정 시점, 평균값과 최대 순간값, 반복 횟수와 허용 오차까지 같아야 한다. `logical_used_memory`와 `physical_or_estimated_memory`를 별도로 보고하면 정책 결과와 구현 효율을 구분할 수 있다.

오버헤드를 실제 제한에 포함하면 짧은 키도 노드 비용 때문에 더 일찍 제거되고, 버킷 확장이나 무효 TTL 기록만으로 OOM·LRU 시점이 달라질 수 있다. 따라서 이는 단순 표시 공식 변경이 아니라 모든 할당·해제·재해싱·힙 변경 경로의 메모리 갱신과 eviction 정책을 다시 설계하는 변경이다.

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
