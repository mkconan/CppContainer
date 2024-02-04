from jinja2 import Environment, FileSystemLoader
from pprint import pprint
from io import TextIOWrapper
from typing import Tuple, List
import sys
from flow_object import FlowNode, FlowType, Arrow, contains_if_root
import util

DEFAULT_DEPTH = 3
IF_FLOW_W = 240
IF_FLOW_H = 80
NORMAL_FLOW_H = 40
NORMAL_FLOW_W = 240
ARROW_L = 40
MARGIN = 40

template_dict = {}
source_code = []


def load_templates():
    """フローのテンプレートの読み込み"""
    global template_dict
    env = Environment(loader=FileSystemLoader("templates"))

    for flow_type in FlowType:
        flow_type = flow_type.name.lower()
        template = env.get_template(f"{flow_type}.j2")
        template_dict[flow_type] = template

    return


def laod_source_code(c_file_path: str):
    global source_code
    with open(c_file_path, mode="r") as f:
        source_code = f.readlines()


def make_flow_list(analysys_result: List[str], func_name: str = "main") -> List[FlowNode]:
    flow_list: List[FlowNode] = []
    is_detect_func = False
    for line in analysys_result:
        depth = util.get_depth(line)
        line_no = util.get_line_no(line)
        if f"FUNCTION_DECL: {func_name}" in line:
            is_detect_func = True
            func_depth = depth

        elif is_detect_func:
            # 探した関数名から抜ければ終了
            if depth <= func_depth:
                break

            flow_type = line.split()[0].removesuffix(":")

            # depthスタック確認
            if len(FlowNode.cur_depth_stack):
                for d in reversed(FlowNode.cur_depth_stack):
                    if depth <= d["depth"]:
                        FlowNode.pop_depth_stack()
                        if d["name"] == "for_start":
                            flow = FlowNode(
                                FlowType.FOR_LOOP_END,
                                "for loop end",
                                line_no,
                            )
                            flow_list.append(flow)
                        elif d["name"] == "if_start":
                            FlowNode.add_if_depth(-1)
                            FlowNode.pop_if_root_id_stack()
                        elif d["name"] == "else_if_start":
                            FlowNode.add_if_depth(-1)
                            FlowNode.add_flow_depth(-1)
                            FlowNode.pop_if_root_id_stack()
                        elif d["name"] == "else_start":
                            FlowNode.add_if_depth(-1)
                            FlowNode.add_flow_depth(-1)
                        else:
                            KeyError(f"Invalid keys. {d.keys()}")

            # forループの始端
            if flow_type == "FOR_STMT":
                d = {"name": "for_start", "depth": depth}
                FlowNode.push_depth_stack(d)
                flow = FlowNode(
                    FlowType.FOR_LOOP_START,
                    util.get_for_text(line_no, source_code),
                    line_no,
                )
                flow_list.append(flow)

            # 関数呼び出し
            elif flow_type == "CALL_EXPR":
                flow = FlowNode(FlowType.DEFINED_PROCESS, line.split()[1], line_no)
                flow_list.append(flow)

            # IF分岐の始端
            elif flow_type == "IF_STMT":
                depth_dict = {"name": "if_start", "depth": depth}
                FlowNode.push_depth_stack(depth_dict)
                FlowNode.add_if_depth(1)
                flow = FlowNode(
                    FlowType.IF,
                    util.get_if_text(line_no, source_code),
                    line_no,
                )
                flow_list.append(flow)

            # ELSE IF節の始端
            elif flow_type == "ELSE_IF_STMT":
                FlowNode.add_if_depth(2)
                FlowNode.add_flow_depth(1)
                depth_dict = {"name": "else_if_start", "depth": depth}
                FlowNode.push_depth_stack(depth_dict)
                flow = FlowNode(
                    FlowType.IF,
                    util.get_if_text(line_no, source_code),
                    line_no,
                )
                flow_list.append(flow)

            # ELSE節の始端
            elif flow_type == "ELSE_STMT":
                FlowNode.add_if_depth(1)
                FlowNode.add_flow_depth(1)
                d = {"name": "else_start", "depth": depth}
                FlowNode.push_depth_stack(d)

    return flow_list


def make_if_flow_list(
    flows: List[FlowNode],
    if_depth: int,
    flow_depth: int,
    start_x: int,
    start_y: int,
    start_arrow_id: int,
    f: TextIOWrapper,
) -> Tuple[int, int, int, int]:
    if_x, if_y = start_x, start_y
    else_x = start_x + IF_FLOW_W + MARGIN
    else_y = start_y + IF_FLOW_H // 2 + ARROW_L
    arrow_id = start_arrow_id
    exists_else_process = False
    # このフロー塊の最大flow深さ
    max_flow_depth = flow_depth
    # ifルートの時のflowの深さ elseの開始位置xを決める時に用いる
    if_route_max_flow_depth = flow_depth

    # リストの先頭はIF
    if_start_flow = flows[0]
    if_start_flow.set_position(if_x, if_y)
    if_start_flow.draw(template_dict, f)

    if_prev_id: int = if_start_flow.id
    else_prev_id = None
    if_y += IF_FLOW_H + ARROW_L
    arrow_id += 1

    for f_i, if_flow in enumerate(flows):
        # 最初はifの親なのでなし
        if f_i == 0:
            continue

        if if_flow.is_draw_flow == True:
            continue

        # ifルートの作成
        if if_flow.flow_depth == flow_depth:
            # 矢印を描画する
            arrow = Arrow(arrow_id, if_prev_id, if_flow.id)
            arrow_id = arrow.draw(template_dict, f)

            # IFが出てきた場合は再帰的にフロー図を作る
            if if_flow.flow_type == FlowType.IF:
                # 最初のifフローは入れる
                if_child_flows = []
                # if文の中にあるフローのリストを作成する
                for if_child_flow in flows[f_i:]:
                    if contains_if_root(if_child_flow, if_flow):
                        if_child_flows.append(if_child_flow)
                    else:
                        break

                if_y, arrow_id, if_prev_id, if_route_max_flow_depth = make_if_flow_list(
                    if_child_flows, if_depth + 1, flow_depth, if_x, if_y, arrow_id + 1, f
                )
                max_flow_depth = max(max_flow_depth, if_route_max_flow_depth)

            else:
                if_flow.set_position(if_x, if_y)
                if_flow.draw(template_dict, f)
                if_prev_id = if_flow.id
            if_y += NORMAL_FLOW_H + ARROW_L

        # elseルートの作成
        elif if_flow.flow_depth >= flow_depth + 1:
            # 矢印を描画する
            # 最初のelse節の場合
            if exists_else_process == False:
                exists_else_process = True
                render_param = {
                    "id": arrow_id,
                    "source_id": if_start_flow.id,
                    "target_id": if_flow.id,
                    "x": start_x
                    + IF_FLOW_W
                    + MARGIN
                    + NORMAL_FLOW_W // 2
                    + (if_route_max_flow_depth - flow_depth) * (MARGIN + NORMAL_FLOW_W),
                    "y": start_y + IF_FLOW_H // 2,
                }
                f.write(template_dict["else_start_arrow"].render(render_param))
                arrow_id += 1
            else:
                arrow = Arrow(arrow_id, else_prev_id, if_flow.id)
                arrow_id = arrow.draw(template_dict, f)

            # IFが出てきた場合は再帰的にフロー図を作る
            if if_flow.flow_type == FlowType.IF:
                # 最初のifフローは入れる
                if_child_flows = []
                # if文の中にあるフローのリストを作成する
                for if_child_flow in flows[f_i:]:
                    if contains_if_root(if_child_flow, if_flow):
                        if_child_flows.append(if_child_flow)
                    else:
                        break
                else_y, arrow_id, else_prev_id, _ = make_if_flow_list(
                    if_child_flows,
                    if_depth + 2,
                    flow_depth + 1,
                    else_x + (if_route_max_flow_depth - flow_depth) * (MARGIN + NORMAL_FLOW_W),
                    else_y,
                    arrow_id,
                    f,
                )
            else:
                # 初めてelseが出た場合
                if else_prev_id is None:
                    else_y += IF_FLOW_H - NORMAL_FLOW_H
                if_flow.set_position(else_x + (if_route_max_flow_depth - flow_depth) * (MARGIN + NORMAL_FLOW_W), else_y)
                if_flow.draw(template_dict, f)
                else_y += NORMAL_FLOW_H + ARROW_L
                else_prev_id = if_flow.id
            max_flow_depth = if_route_max_flow_depth + 1

    # ifルートとelseルートでyが長い方を矢印の終端とする
    end_y = if_y if if_y > else_y else else_y

    # elseルートが何もなかった場合
    if exists_else_process == False:
        render_param = {
            "id": arrow_id,
            "source_id": flows[0].id,
            "source_y": start_y + IF_FLOW_H // 2,
            "turn_x": start_x
            + NORMAL_FLOW_W
            + MARGIN // 2
            + (if_route_max_flow_depth - flow_depth) * (MARGIN + NORMAL_FLOW_W),
            "target_x": start_x + NORMAL_FLOW_W // 2,
            "target_y": end_y - 20,
        }
        f.write(template_dict["else_none_arrow"].render(render_param))
        arrow_id += 1

    # elseルートから戻る矢印を描画する
    else:
        render_param = {
            "id": arrow_id,
            "source_id": else_prev_id,
            "target_x": start_x + NORMAL_FLOW_W // 2,
            "target_y": end_y - 20,
            "arrow_back_width": (if_route_max_flow_depth - flow_depth + 1) * (MARGIN + NORMAL_FLOW_W),
        }
        f.write(template_dict["else_end_arrow"].render(render_param))
        arrow_id += 1

    end_arrow_id = arrow_id

    return end_y, end_arrow_id, if_prev_id, max_flow_depth


def make_flow_xml(analysys_result: List[str]):
    flows: List[FlowNode] = make_flow_list(analysys_result)
    # pprint(flows)

    with open("out/automake.xml", mode="w") as f:
        start_x, start_y = 80, 40
        start_id, end_id = 2, 10000
        pre_end_id = None
        prev_id = -1
        x = start_x
        y = start_y + NORMAL_FLOW_H + ARROW_L
        start_arrow_id = 1000
        arrow_id = start_arrow_id

        # flow図の最初の部分を描画
        render_param = {"x": start_x, "y": start_y}
        f.write(template_dict["flow_start"].render(render_param))
        arrow = Arrow(arrow_id, start_id, flows[0].id)
        arrow_id = arrow.draw(template_dict, f)

        for f_i, flow in enumerate(flows):
            # プロセスを描画する

            # 描画済みのものはskipする
            if flow.is_draw_flow == True:
                continue

            # IFが出てきた場合は再帰的にフロー図を作る
            if flow.flow_type == FlowType.IF and flow.flow_depth == 0:
                if_child_flows = []
                # if文の中にあるフローのリストを作成する
                for if_child_flow in flows[f_i:]:
                    if contains_if_root(if_child_flow, flow):
                        if_child_flows.append(if_child_flow)
                    else:
                        break

                arrow = Arrow(arrow_id, prev_id, flow.id)
                arrow_id = arrow.draw(template_dict, f)
                y, arrow_id, prev_id, _ = make_if_flow_list(if_child_flows, 1, 0, x, y, arrow_id, f)

            elif flow.flow_depth == 0:
                flow.set_position(x, y)
                flow.draw(template_dict, f)

                # 矢印を描画する
                arrow = Arrow(arrow_id, prev_id, flow.id)
                arrow_id = arrow.draw(template_dict, f)

                prev_id = flow.id
                y += NORMAL_FLOW_H + ARROW_L

        # flow図の最後の部分を描画
        for flow in reversed(flows):
            if flow.flow_depth == 0:
                pre_end_id = flow.id
                break
        arrow = Arrow(arrow_id, pre_end_id, end_id)
        _ = arrow.draw(template_dict, f)
        render_param = {"id": end_id, "x": x, "y": y}
        f.write(template_dict["flow_end"].render(render_param))


def main():
    argv = sys.argv
    load_templates()
    laod_source_code(argv[1])
    analysys_result = util.read_file("./result_analysis.yaml")
    make_flow_xml(analysys_result)


if __name__ == "__main__":
    main()
