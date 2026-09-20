# 자료구조를 조합해 키·값 저장소와 LRU·메모리·TTL 관리를 구현한다.

from typing import Optional

from hash_map import HashMap


class Store:
    """문자열 키·값을 보관하는 저장소. 해시맵을 내부 저장소로 사용한다."""

    def __init__(self) -> None:
        """빈 저장소를 만든다. 내부 해시맵이 키·값의 저장·조회를 담당한다."""
        self._data = HashMap()  # 직접 구현한 해시맵. 키는 str, 값은 str

    def set(self, key: str, value: str) -> None:
        """키에 값을 저장한다. 새 키면 추가하고, 기존 키면 값을 덮어쓴다."""
        self._data.put(key, value)

    def get(self, key: str) -> Optional[str]:
        """키의 값을 반환한다. 존재하면 값 문자열, 없으면 None을 반환한다."""
        result = self._data._find_node(key)

        if result == None:
            return None
        else:
            return result.data.value

    def del_key(self, key: str) -> bool:
        """키를 삭제한다. 삭제 성공 시 True, 없는 키이면 False를 반환한다."""
        if self._data.remove(key) is False:
            return False
        else:
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
