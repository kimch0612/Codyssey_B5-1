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

    elif command == "DEL":
        if len(tokens) != 2:
            return "(error) ERR wrong number of arguments for 'del' command"

        deleted = store.del_key(tokens[1])
        if deleted:
            return "(integer) 1"

        return "(integer) 0"

    elif command == "EXISTS":
        if len(tokens) != 2:
            return "(error) ERR wrong number of arguments for 'exists' command"

        exists = store.exists(tokens[1])
        if exists:
            return "(integer) 1"

        return "(integer) 0"

    elif command == "DBSIZE":
        if len(tokens) != 1:
            return "(error) ERR wrong number of arguments for 'dbsize' command"

        return f"(integer) {store.dsize()}"

    elif command == "KEYS":
        if len(tokens) != 1:
            return "(error) ERR wrong number of arguments for 'keys' command"

        keys = store.keys()
        if not keys:
            return "(empty array)"

        lines = []
        for index, key in enumerate(keys, start=1):
            lines.append(f'{index}. "{key}"')

        return "\n".join(lines)

    elif command == "CONFIG":
        if len(tokens) != 4:
            return "(error) ERR wrong number of arguments for 'config' command"

        if tokens[1].upper() != "SET" or tokens[2].upper() != "MAXMEMORY":
            return "(error) ERR syntax error"

        try:
            maxmemory = int(tokens[3])
        except ValueError:
            return "(error) ERR value is not an integer or out of range"

        if not store.set_maxmemory(maxmemory):
            return "(error) ERR value is not an integer or out of range"

        return "OK"

    elif command == "INFO":
        if len(tokens) != 2:
            return "(error) ERR wrong number of arguments for 'info' command"

        if tokens[1].upper() != "MEMORY":
            return "(error) ERR syntax error"

        used_memory, maxmemory, evicted_keys = store.info_memory()
        return (
            f"used_memory:{used_memory}\n"
            f"maxmemory:{maxmemory}\n"
            f"evicted_keys:{evicted_keys}"
        )

    elif command == "EXPIRE":
        if len(tokens) != 3:
            return "(error) ERR wrong number of arguments for 'expire' command"

        try:
            seconds = int(tokens[2])
        except ValueError:
            return "(error) ERR value is not an integer or out of range"

        expired = store.expire(tokens[1], seconds)
        if expired:
            return "(integer) 1"

        return "(integer) 0"

    elif command == "TTL":
        if len(tokens) != 2:
            return "(error) ERR wrong number of arguments for 'ttl' command"

        return f"(integer) {store.ttl(tokens[1])}"

    return f"(error) ERR unknown command '{tokens[0]}'"

def run_repl() -> None:
    """프롬프트에서 입력을 받아 명령 실행과 결과 출력을 반복한다."""
    store = Store()

    while True:
        try:
            line = input("mini-redis> ")
        except KeyboardInterrupt:
            print()
            break
        except EOFError:
            print()
            break

        try:
            tokens = parse_input(line)
        except ValueError:
            print("(error) ERR syntax error")
            continue

        if not tokens:
            continue

        if tokens[0].upper() in ("EXIT", "QUIT"):
            break

        result = execute_command(store, tokens)
        if result is not None:
            print(result)

if __name__ == "__main__":
    run_repl()