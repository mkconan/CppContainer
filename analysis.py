import sys
import os
import clang.cindex
from util import calc_indent_depth, INDENT

print_node_kind = [
    "TRANSLATION_UNIT",
    "FUNCTION_DECL",
    "COMPOUND_STMT",
    "FOR_STMT",
    "IF_STMT",
    "CALL_EXPR",
    "BINARY_OPERATOR",
    "DECL_REF_EXPR",
    "RETURN_STMT",
]

output_yaml_file = "result_analysis.yaml"


def visit_node(file_path: str, node: clang.cindex.Cursor = None, indent=0):
    """構文解析木のノードを探索する

    Args:
        node (_type_, optional): 構文解析木のノード. Defaults to None.
        indent (int, optional): 深さ. Defaults to 0.
    """
    print(f"{'  '*indent}{node.kind.name}: {node.spelling} {node.type.spelling} @{node.location.line}")

    # if (node.kind.name in print_node_kind) and (str(node.location.file) == filspellinge_path):
    if str(node.location.file) == file_path:
        with open(output_yaml_file, mode="a") as f:
            f.write(f"{INDENT * indent}{node.kind.name}: {node.spelling} {node.type.spelling} @{node.location.line}\n")

    for c in node.get_children():
        visit_node(file_path, c, indent=indent + 1)


def modify_else():
    """clangの構文解析以外の手法でelse節を見つける"""
    # Read
    read_lines = []
    with open(output_yaml_file, mode="r") as f:
        read_lines = f.readlines()

    for l, line in enumerate(read_lines):
        line_indent_size = calc_indent_depth(line)

        # if節を見つける
        if "IF_STMT" in line:
            if_depth = line_indent_size
            compound_stmt_cnt = 0

            _l = l
            # 深さがifより1つ下、COMPOUND_STMTが2回目のときelse判定する
            while True:
                _l += 1
                _line = read_lines[_l]
                _line_indent_size = calc_indent_depth(_line)

                if _line_indent_size == if_depth:
                    break

                if _line_indent_size != if_depth + 1:
                    continue

                # 深さがifより1つ下のifのときelse if判定する
                if "IF_STMT" in _line and _line_indent_size == if_depth + 1:
                    read_lines[_l] = read_lines[_l].replace("IF_STMT", "ELSE_IF_STMT")

                if "COMPOUND_STMT" in _line:
                    compound_stmt_cnt += 1

                if compound_stmt_cnt == 2:
                    read_lines[_l] = f"{INDENT*_line_indent_size}ELSE_STMT: \n"
                    break

    # Modify
    with open(output_yaml_file, mode="w") as f:
        f.writelines(read_lines)


def remove_included_func():
    # Read
    read_lines = []
    with open(output_yaml_file, mode="r") as f:
        read_lines = f.readlines()

    # Remove line if included function
    for l, line in enumerate(read_lines):
        if "FUNCTION_DECL" in line and "COMPOUND_STMT" not in read_lines[l + 1]:
            read_lines[l] = ""

    # Modify
    with open(output_yaml_file, mode="w") as f:
        f.writelines(read_lines)


def main():
    if os.path.exists(output_yaml_file):
        os.remove(output_yaml_file)

    with open(output_yaml_file, mode="w"):
        pass

    index = clang.cindex.Index.create()
    file_path = sys.argv[1]
    tree = index.parse(file_path, args=["-analyze"])
    visit_node(file_path, tree.cursor)
    remove_included_func()
    modify_else()


if __name__ == "__main__":
    main()
