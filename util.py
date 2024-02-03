from typing import List
import re
import html

INDENT = "  "
INDENT_SIZE = len(INDENT)


def calc_indent_depth(line: str) -> int:
    """文字列からインデントの深さを求める（※スペースの数ではない）

    Args:
        line (str): 求めたい文字列

    Returns:
        int: インデントの深さ
    """
    for num, char in enumerate(line):
        if char != " ":
            break
    return int(num / INDENT_SIZE)


def read_file(file_path: str):
    with open(file_path, mode="r") as f:
        return f.readlines()


def get_depth(analysis: str):
    head_space = re.search(r"\s*", analysis).group()
    depth = len(head_space) // 2
    return depth


def get_line_no(analysis: str) -> int:
    search = re.search(r"@[0-9]*", analysis)
    if search:
        line_no = int(search.group()[1:])
        return line_no
    else:
        return None


def get_if_text(line_no: int, source_code: List[str]):
    # ifの中身が複数行の場合があるため
    if_lines = "".join(source_code[line_no - 1 : line_no + 2])
    match = re.match(r"\s*if \((.*)\)", if_lines)
    if match:
        # 不等号記号をHTML形式に合うように変換
        if_text = html.escape(match.group(1))
        return if_text
    else:
        return None


def get_for_text(line_no: int, source_code: List[str]):
    # forの中身が複数行の場合があるため
    for_lines = "".join(source_code[line_no - 1 : line_no + 2])
    match = re.match(r"\s*for \((.*)\)", for_lines)
    if match:
        # 不等号記号をHTML形式に合うように変換
        for_2nd_text = html.escape(match.group(1).split(";")[1][1:])
        return for_2nd_text
    else:
        return None
