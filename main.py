# 프로그램을 시작하고 CLI의 입력 해석·명령 실행·결과 출력을 반복한다.

import shlex

from typing import List, Optional

from store import Store


def parse_input(line: str) -> List[str]:
    """입력 한 줄을 명령어와 인자 토큰 목록으로 나눈다."""
    return shlex.split(line)

def execute_command(store: Store, tokens: List[str]) -> Optional[str]:
    """파싱된 토큰의 명령을 실행하고 출력할 문자열을 반환한다."""
    if not tokens:
        return None

    command = tokens[0].upper()
    if command == "SET":
        if len(tokens) != 3:
            return "(error) ERR wrong number of arguments for 'set' command"

        stored = store.set(tokens[1], tokens[2])
        if stored:
            return "OK"
        else:
            return "(error) OOM command not allowed when used_memory > 'maxmemory'"

    elif command == "GET":
        if len(tokens) != 2:
            return "(error) ERR wrong number of arguments for 'get' command"

        value = store.get(tokens[1])
        if value is None:
            return "(nil)"

        return f"\"{value}\""

    return f"(error) ERR unknown command '{tokens[0]}'"
