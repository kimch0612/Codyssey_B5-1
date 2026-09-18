# 이중 연결 리스트의 노드와 삽입·삭제·이동 연산을 구현한다.


class Node:
    """데이터와 이전·다음 노드의 참조를 보관한다."""

    def __init__(self, data: object) -> None:
        """전달받은 데이터와 아직 연결되지 않은 양쪽 참조를 초기화한다."""
        self.data = data
        self.prev = None
        self.next = None


class DoublyLinkedList:
    """첫 노드와 마지막 노드를 관리하는 이중 연결 리스트다."""

    def __init__(self) -> None:
        """head와 tail이 빈 상태인 리스트를 초기화한다."""
        self.head = None
        self.tail = None
