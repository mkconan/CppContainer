from jinja2 import Template, Environment, FileSystemLoader
from util import calc_indent_depth
import re
from enum import Enum
from pprint import pprint

DEFAULT_DEPTH = 3
IF_FLOW_W = 240
IF_FLOW_H = 80
ARROW_L = 40
MARGIN = 40


class FlowType(Enum):
    FLOW_START = 0
    FLOW_END = 1
    FOR_LOOP_START = 2
    FOR_LOOP_END = 3
    IF = 4
    ARROW = 5
    DEFINED_PROCESS = 6


template_flow_list = [
    "flow_start",
    "flow_end",
    "for_loop_start",
    "for_loop_end",
    "if",
    "arrow",
    "process",
    "defined_process",
]


def load_templates():
    env = Environment(loader=FileSystemLoader("templates"))

    template_dict = {}
    for flow in template_flow_list:
        template = env.get_template(f"{flow}.j2")
        template_dict[flow] = template

    return template_dict


def read_analysys_file(file_path: str):
    with open(file_path, mode="r") as f:
        return f.readlines()


def get_depth(analysis: str):
    head_space = re.search(r"\s*", analysis).group()
    depth = len(head_space) // 2
    return depth


def make_chart_structure(analysys_result: list[str], func_name="main"):
    chart_struct_dict_list = []
    is_detect_func = False
    for_loop_start_depth_stack = []
    if_branch_start_depth_stack = []
    else_branch_start_depth_stack = []
    is_if_branch_finish = None
    is_branch_start = None
    brach_root_id = None
    id = 3
    prev_id = -1
    flow_depth = -1
    for line in analysys_result:
        can_find_process = False
        if "FUNCTION_DECL: main" in line:
            is_detect_func = True
        if is_detect_func:
            flow_type = line.split()[0].removesuffix(":")
            depth = get_depth(line)

            # forループの終端
            if len(for_loop_start_depth_stack):
                if depth <= for_loop_start_depth_stack[-1]:
                    for_loop_start_depth_stack.pop()
                    chart_struct = {}
                    chart_struct["type"] = FlowType.FOR_LOOP_END
                    chart_struct["val"] = "for loop end"
                    can_find_process = True

            # forループの始端
            if "FOR_STMT" in flow_type:
                for_loop_start_depth_stack.append(depth)
                chart_struct = {}
                chart_struct["type"] = FlowType.FOR_LOOP_START
                chart_struct["val"] = "for loop start"
                can_find_process = True

            # 関数呼び出し
            if "CALL_EXPR" in flow_type:
                chart_struct = {}
                chart_struct["type"] = FlowType.DEFINED_PROCESS
                chart_struct["val"] = line.split()[1]
                can_find_process = True

            # IF分岐の始端
            if "IF_STMT" in flow_type:
                flow_depth += 1
                if_branch_start_depth_stack.append(depth)
                chart_struct = {}
                chart_struct["type"] = FlowType.IF
                chart_struct["val"] = "xxx = yyy?"
                can_find_process = True

            # IF分岐の終端
            elif len(if_branch_start_depth_stack):
                if depth <= if_branch_start_depth_stack[-1]:
                    flow_depth -= 1
                    if_branch_start_depth_stack.pop()
                    is_if_branch_finish = True
                    brach_root_id = id

            # ELSE節の最初のプロセス
            if "ELSE_STMT" in flow_type:
                is_branch_start = True
                flow_depth += 1
                else_branch_start_depth_stack.append(depth)

            # ELSE節の終端
            elif len(else_branch_start_depth_stack):
                if depth <= if_branch_start_depth_stack[-1]:
                    flow_depth -= 1
                    else_branch_start_depth_stack.pop()

            if can_find_process:
                can_find_process = False
                chart_struct["flow_depth"] = flow_depth
                chart_struct["source_id"] = brach_root_id if brach_root_id is not None else None
                chart_struct["id"] = id
                id += 1
                chart_struct["if_branch_finish"] = True if is_if_branch_finish else False
                chart_struct["else_start"] = True if is_branch_start else False
                chart_struct_dict_list.append(chart_struct)

    return chart_struct_dict_list


def make_if_chart_xml(template_dict, if_chiild_flows, if_depth, start_x, start_y, start_arrow_id, file_stream):
    if_x, if_y = start_x, start_y
    else_x = start_x + IF_FLOW_W + MARGIN
    else_y = start_y + IF_FLOW_H // 2 + ARROW_L
    prev_id = -1
    arrow_id = start_arrow_id

    # リストの先頭はIF
    if_flow = if_chiild_flows[0]
    render_param = {"id": if_flow["id"], "text": if_flow["val"], "x": if_x, "y": if_y}
    file_stream.write(template_dict[f"{if_flow['type'].name.lower()}"].render(render_param))

    prev_id = if_flow["id"]
    if_y += 120
    arrow_id += 1

    for f_i, if_flow in enumerate(if_chiild_flows):
        # 最初はifの親なのでなし
        if f_i == 0:
            continue

        # IFが出てきた場合は再帰的にフロー図を作る
        if if_flow["type"] == FlowType.IF:
            # 最初のifフローは入れる
            if_child_flows = []
            # if文の中にあるフローのリストを作成する
            for if_child_flow in if_chiild_flows[f_i:]:
                if if_child_flow["flow_depth"] >= if_depth + 1:
                    if_child_flows.append(if_child_flow)
                    if_chiild_flows.remove(if_child_flow)

            # if側に出てきた場合
            if if_flow["flow_depth"] == if_depth:
                if_y, arrow_id = make_if_chart_xml(
                    template_dict, if_child_flows, if_depth + 1, if_x, if_y, arrow_id + 1, file_stream
                )
            # else側に出てきた場合
            elif if_flow["flow_depth"] == if_depth + 1:
                if_y, arrow_id = make_if_chart_xml(
                    template_dict, if_child_flows, if_depth + 1, else_x, else_y, arrow_id + 1, file_stream
                )

        # if側の作成
        elif if_flow["flow_depth"] == if_depth:
            render_param = {
                "id": if_flow["id"],
                "text": if_flow["val"],
                "x": if_x,
                "y": if_y,
            }
            file_stream.write(template_dict[f"{if_flow['type'].name.lower()}"].render(render_param))

            # 矢印を描画する
            if if_flow["source_id"] is not None:
                render_param = {"id": arrow_id, "source_id": if_flow["source_id"], "target_id": if_flow["id"]}
            else:
                render_param = {"id": arrow_id, "source_id": prev_id, "target_id": if_flow["id"]}
            file_stream.write(template_dict["arrow"].render(render_param))

            prev_id = if_flow["id"]
            if_y += 80
            arrow_id += 1

        # else側の作成
        elif if_flow["flow_depth"] == if_depth + 1:
            render_param = {
                "id": if_flow["id"],
                "text": if_flow["val"],
                "x": else_x,
                "y": else_y,
            }
            file_stream.write(template_dict[f"{if_flow['type'].name.lower()}"].render(render_param))

            # 矢印を描画する
            if if_flow["source_id"] is not None:
                render_param = {"id": arrow_id, "source_id": if_flow["source_id"], "target_id": if_flow["id"]}
            else:
                render_param = {"id": arrow_id, "source_id": prev_id, "target_id": if_flow["id"]}
            file_stream.write(template_dict["arrow"].render(render_param))

            prev_id = if_flow["id"]
            else_y += 80
            arrow_id += 1

    end_y = if_y if if_y > else_y else else_y
    end_arrow_id = arrow_id

    return end_y, end_arrow_id


def make_chart_xml(template_dict: dict, analysys_result):
    flows = make_chart_structure(analysys_result)
    pprint(flows)

    start_id = 2
    with open("out/automake.xml", mode="w") as f:
        start_x, start_y = 80, 40
        render_param = {"x": start_x, "y": start_y}
        f.write(template_dict["flow_start"].render(render_param))

        prev_id = -1
        x = start_x
        y = start_y + 80
        arrow_id = 1000
        for f_i, flow in enumerate(flows):
            # プロセスを描画する
            # IFが出てきた場合は再帰的にフロー図を作る
            if flow["type"] == FlowType.IF and flow["flow_depth"] == 0:
                if_child_flows = []
                # if文の中にあるフローのリストを作成する
                for if_child_flow in flows[f_i:]:
                    if if_child_flow["flow_depth"] >= 0:
                        if_child_flows.append(if_child_flow)
                        flows.remove(if_child_flow)

                y, arrow_id = make_if_chart_xml(template_dict, if_child_flows, 0, x, y, arrow_id + 1, f)

            elif flow["flow_depth"] == -1:
                render_param = {"id": flow["id"], "text": flow["val"], "x": x, "y": y}
                f.write(template_dict[f"{flow['type'].name.lower()}"].render(render_param))

                # 矢印を描画する
                if flow["source_id"] is not None:
                    render_param = {"id": arrow_id, "source_id": flow["source_id"], "target_id": flow["id"]}
                else:
                    render_param = {"id": arrow_id, "source_id": prev_id, "target_id": flow["id"]}
                f.write(template_dict["arrow"].render(render_param))

                prev_id = flow["id"]
                y += 80
                arrow_id += 1

        # flow図の最後の部分を描画
        render_param = {"id": arrow_id, "source_id": flows[-1]["id"], "target_id": 10000}
        f.write(template_dict["arrow"].render(render_param))
        render_param = {"id": 10000, "x": x, "y": y}
        f.write(template_dict["flow_end"].render(render_param))


def main():
    template_dict = load_templates()
    analysys_result = read_analysys_file("./result_analysis.yaml")
    make_chart_xml(template_dict, analysys_result)


if __name__ == "__main__":
    main()
