# 이중 연결 리스트의 노드와 삽입·삭제·이동 연산을 구현한다.
from typing import Optional


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

    def insert_front(self, data: object) -> Node:
        """데이터를 담은 새 노드를 맨 앞에 삽입하고 해당 노드를 반환한다."""
        new_node = Node(data)

        if (self.head is None) and (self.tail is None):
            self.head = new_node
            self.tail = new_node
        else:
            self.head.prev = new_node
            new_node.next = self.head
            self.head = new_node

        return new_node

    def insert_back(self, data: object) -> Node:
        """데이터를 담은 새 노드를 맨 뒤에 삽입하고 해당 노드를 반환한다."""
        new_node = Node(data)

        if (self.head is None) and (self.tail is None):
            self.head = new_node
            self.tail = new_node
        else:
            self.tail.next = new_node
            new_node.prev = self.tail
            self.tail = new_node
        
        return new_node

    def remove_front(self) -> Optional[Node]:
        """맨 앞 노드를 분리해 반환하고, 빈 리스트이면 None을 반환한다."""
        if self.head is None:
            return None
        
        del_node = self.head
        if del_node == self.tail:
            self.head = None
            self.tail = None
        else:
            self.head = del_node.next
            self.head.prev = None
            
            del_node.prev = None
            del_node.next = None

        return del_node

    def remove_back(self) -> Optional[Node]:
        """맨 뒤 노드를 분리해 반환하고, 빈 리스트이면 None을 반환한다."""
        if self.head is None:
            return None

        del_node = self.tail
        if del_node == self.head:
            self.head = None
            self.tail = None
        else:
            self.tail = del_node.prev
            self.tail.next = None

            del_node.prev = None
            del_node.next = None
        
        return del_node