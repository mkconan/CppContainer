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