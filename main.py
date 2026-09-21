# 프로그램을 시작하고 CLI의 입력 해석·명령 실행·결과 출력을 반복한다.

import shlex

from typing import List


def parse_input(line: str) -> List[str]:
    """입력 한 줄을 명령어와 인자 토큰 목록으로 나눈다."""
    return shlex.split(line)