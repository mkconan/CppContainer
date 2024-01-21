from jinja2 import Template, Environment, FileSystemLoader
from util import calc_indent_depth
import re
from enum import Enum
from pprint import pprint
from io import TextIOWrapper
from typing import Tuple, List

DEFAULT_DEPTH = 3
IF_FLOW_W = 240
IF_FLOW_H = 80
NORMAL_FLOW_H = 40
NORMAL_FLOW_W = 240
ARROW_L = 40
MARGIN = 40


class FlowType(Enum):
    FLOW_START = 0
    FLOW_END = 1
    FOR_LOOP_START = 2
    FOR_LOOP_END = 3
    IF = 4
    ARROW = 5
    ELSE_START_ARROW = 6
    ELSE_END_ARROW = 7
    DEFINED_PROCESS = 8


template_dict = {}

template_flow_list = [
    "flow_start",
    "flow_end",
    "for_loop_start",
    "for_loop_end",
    "if",
    "arrow",
    "else_start_arrow",
    "else_end_arrow",
    "process",
    "defined_process",
]


def load_templates():
    """フローのテンプレートの読み込み"""
    global template_dict
    env = Environment(loader=FileSystemLoader("templates"))

    for flow in template_flow_list:
        template = env.get_template(f"{flow}.j2")
        template_dict[flow] = template

    return


def read_analysys_file(file_path: str):
    with open(file_path, mode="r") as f:
        return f.readlines()


def get_depth(analysis: str):
    head_space = re.search(r"\s*", analysis).group()
    depth = len(head_space) // 2
    return depth


def get_line_no(analysis: str):
    line = re.search(r"@[0-9]*", analysis).group()
    line = int(line[1:])
    return line


def make_chart_structure(analysys_result: List[str], func_name: str = "main"):
    chart_struct_dict_list = []
    is_detect_func = False
    for_loop_start_depth_stack = []
    if_branch_start_depth_stack = []
    else_branch_start_depth_stack = []
    id = 3
    flow_depth = -1
    for line in analysys_result:
        depth = get_depth(line)
        can_find_process = False
        if f"FUNCTION_DECL: {func_name}" in line:
            is_detect_func = True
            func_depth = depth

        elif is_detect_func:
            # 探した関数名から抜ければ終了
            if depth <= func_depth:
                break

            flow_type = line.split()[0].removesuffix(":")
            chart_struct = {}

            # forループの終端
            if len(for_loop_start_depth_stack):
                if depth <= for_loop_start_depth_stack[-1]:
                    for_loop_start_depth_stack.pop()
                    chart_struct["type"] = FlowType.FOR_LOOP_END
                    chart_struct["val"] = "for loop end"
                    can_find_process = True

            # forループの始端
            if "FOR_STMT" in flow_type:
                for_loop_start_depth_stack.append(depth)
                chart_struct["type"] = FlowType.FOR_LOOP_START
                chart_struct["val"] = "for loop start"
                can_find_process = True

            # 関数呼び出し
            if "CALL_EXPR" in flow_type:
                chart_struct["type"] = FlowType.DEFINED_PROCESS
                chart_struct["val"] = line.split()[1]
                can_find_process = True

            # IF分岐の始端
            if "IF_STMT" in flow_type:
                if len(else_branch_start_depth_stack) > 0 and else_branch_start_depth_stack[-1] == depth - 1:
                    flow_depth += 1
                elif len(if_branch_start_depth_stack) == 0:
                    flow_depth += 1
                else:
                    flow_depth += 2
                    # TODO: else ifとelse { if {..をうまく設定させる
                    if_branch_start_depth_stack.append(depth)

                if_branch_start_depth_stack.append(depth)
                chart_struct["type"] = FlowType.IF
                chart_struct["val"] = "xxx = yyy?"
                can_find_process = True

            # IF分岐の終端
            elif len(if_branch_start_depth_stack):
                for d in reversed(if_branch_start_depth_stack):
                    if depth <= d:
                        flow_depth -= 1
                        if_branch_start_depth_stack.pop()

            # ELSE節の最初のプロセス
            if "ELSE_STMT" in flow_type:
                flow_depth += 1
                else_branch_start_depth_stack.append(depth)

            # ELSE節の終端
            elif len(else_branch_start_depth_stack):
                for d in reversed(else_branch_start_depth_stack):
                    if depth <= d:
                        flow_depth -= 1
                        else_branch_start_depth_stack.pop()

            if can_find_process:
                can_find_process = False
                chart_struct["flow_depth"] = flow_depth
                chart_struct["id"] = id
                chart_struct["line"] = get_line_no(line)
                id += 1
                chart_struct["is_draw_flow"] = False
                chart_struct_dict_list.append(chart_struct)

    return chart_struct_dict_list


def make_if_chart_xml(
    flows: List[dict], if_depth: int, start_x: int, start_y: int, start_arrow_id: int, f: TextIOWrapper
) -> Tuple[int, int, int]:
    if_x, if_y = start_x, start_y
    else_x = start_x + IF_FLOW_W + MARGIN
    else_y = start_y + IF_FLOW_H // 2 + ARROW_L
    arrow_id = start_arrow_id
    is_else_process = False

    # リストの先頭はIF
    if_start_flow = flows[0]
    draw_node(if_start_flow, if_x, if_y, f)

    if_prev_id: int = if_start_flow["id"]
    else_prev_id = None
    if_y += IF_FLOW_H + ARROW_L
    arrow_id += 1

    for f_i, if_flow in enumerate(flows):
        # 最初はifの親なのでなし
        if f_i == 0:
            continue

        if if_flow["is_draw_flow"] == True:
            continue

        # ifルートの作成
        if if_flow["flow_depth"] == if_depth:
            # IFが出てきた場合は再帰的にフロー図を作る
            if if_flow["type"] == FlowType.IF:
                # 最初のifフローは入れる
                if_child_flows = []
                # if文の中にあるフローのリストを作成する
                for if_child_flow in flows[f_i:]:
                    if if_child_flow["flow_depth"] >= if_depth + 1:
                        if_child_flows.append(if_child_flow)

                if_y, arrow_id, if_prev_id = make_if_chart_xml(
                    if_child_flows, if_depth + 1, if_x, if_y, arrow_id + 1, f
                )

            else:
                draw_node(if_flow, if_x, if_y, f)

            # 矢印を描画する
            arrow_id = draw_arrow(arrow_id, if_prev_id, if_flow["id"], f)

            if_prev_id = if_flow["id"]
            if_y += NORMAL_FLOW_H + ARROW_L

        # elseルートの作成
        elif if_flow["flow_depth"] >= if_depth + 1:
            # IFが出てきた場合は再帰的にフロー図を作る
            if if_flow["type"] == FlowType.IF:
                # 最初のifフローは入れる
                if_child_flows = []
                # if文の中にあるフローのリストを作成する
                for if_child_flow in flows[f_i:]:
                    if if_child_flow["flow_depth"] >= if_depth + 2:
                        if_child_flows.append(if_child_flow)
                else_y, arrow_id, else_prev_id = make_if_chart_xml(
                    if_child_flows, if_depth + 2, else_x, else_y, arrow_id, f
                )
            else:
                draw_node(if_flow, else_x, else_y, f)

            # 矢印を描画する
            # 最初のelse節の場合
            if is_else_process == False:
                is_else_process = True
                render_param = {
                    "id": arrow_id,
                    "source_id": if_start_flow["id"],
                    "target_id": if_flow["id"],
                    "x": start_x + IF_FLOW_W + MARGIN + NORMAL_FLOW_W // 2,
                    "y": start_y + IF_FLOW_H // 2,
                }
                f.write(template_dict["else_start_arrow"].render(render_param))
                arrow_id += 1
            else:
                arrow_id = draw_arrow(arrow_id, else_prev_id, if_flow["id"], f)

            if if_flow["type"] != FlowType.IF:
                else_prev_id = if_flow["id"]
            else_y += NORMAL_FLOW_H + ARROW_L

    # ifルートとelseルートでyが長い方を矢印の終端とする
    end_y = if_y if if_y > else_y else else_y

    # elseルートから戻る矢印を描画する
    if else_prev_id is not None:
        render_param = {
            "id": arrow_id,
            "source_id": else_prev_id,
            "target_x": start_x + NORMAL_FLOW_W // 2,
            "target_y": end_y - 20,
        }
        f.write(template_dict["else_end_arrow"].render(render_param))
        arrow_id += 1

    end_arrow_id = arrow_id

    return end_y, end_arrow_id, if_prev_id


def make_chart_xml(analysys_result: List[str]):
    flows = make_chart_structure(analysys_result)
    # pprint(flows)

    with open("out/automake.xml", mode="w") as f:
        start_x, start_y = 80, 40
        start_id, end_id = 2, 10000
        prev_id = -1
        x = start_x
        y = start_y + NORMAL_FLOW_H + ARROW_L
        start_arrow_id = 1000
        arrow_id = start_arrow_id

        # flow図の最初の部分を描画
        render_param = {"x": start_x, "y": start_y}
        f.write(template_dict["flow_start"].render(render_param))
        arrow_id = draw_arrow(arrow_id, start_id, flows[0]["id"], f)

        for f_i, flow in enumerate(flows):
            # プロセスを描画する

            # 描画済みのものはskipする
            if flow["is_draw_flow"] == True:
                continue

            # IFが出てきた場合は再帰的にフロー図を作る
            if flow["type"] == FlowType.IF and flow["flow_depth"] == 0:
                if_child_flows = []
                # if文の中にあるフローのリストを作成する
                for if_child_flow in flows[f_i:]:
                    if if_child_flow["flow_depth"] >= 0:
                        if_child_flows.append(if_child_flow)

                arrow_id = draw_arrow(arrow_id, prev_id, flow["id"], f)
                y, arrow_id, prev_id = make_if_chart_xml(if_child_flows, 0, x, y, arrow_id, f)

            elif flow["flow_depth"] == -1:
                draw_node(flow, x, y, f)

                # 矢印を描画する
                arrow_id = draw_arrow(arrow_id, prev_id, flow["id"], f)

                prev_id = flow["id"]
                y += NORMAL_FLOW_H + ARROW_L

        # flow図の最後の部分を描画
        _ = draw_arrow(arrow_id, flows[-1]["id"], end_id, f)
        render_param = {"id": end_id, "x": x, "y": y}
        f.write(template_dict["flow_end"].render(render_param))


def draw_node(flow, x: int, y: int, f: TextIOWrapper):
    """Node（フローの要素）を描画する

    Args:
        flow (_type_): フローの辞書
        x (int): 描画位置の左上x座標
        y (int): 描画位置の左上y座標
        f (TextIOWrapper): ファイルストリーム
    """
    if flow["is_draw_flow"] != True:
        render_param = {
            "id": flow["id"],
            "text": flow["val"],
            "x": x,
            "y": y,
        }
        f.write(template_dict[f"{flow['type'].name.lower()}"].render(render_param))
        # 描画済であることを記録する
        flow["is_draw_flow"] = True


def draw_arrow(arrow_id: int, source_id: int, target_id: int, f: TextIOWrapper) -> int:
    """矢印を描画する

    Args:
        arrow_id (int): 矢印のID
        source_id (int): 矢元のノードID
        target_id (int): 矢先のノードID
        f (TextIOWrapper): ファイルストリーム

    Returns:
        int: インクリメントした矢印ID
    """
    render_param = {"id": arrow_id, "source_id": source_id, "target_id": target_id}
    f.write(template_dict["arrow"].render(render_param))
    return arrow_id + 1


def main():
    load_templates()
    analysys_result = read_analysys_file("./result_analysis.yaml")
    make_chart_xml(analysys_result)


if __name__ == "__main__":
    main()
