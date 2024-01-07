from jinja2 import Template, Environment, FileSystemLoader
from util import calc_indent_depth
import re
from enum import Enum
from pprint import pprint


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
    for line in analysys_result:
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
                    chart_struct["depth"] = depth
                    chart_struct_dict_list.append(chart_struct)

            # forループの始端
            if "FOR_STMT" in flow_type:
                for_loop_start_depth_stack.append(depth)
                chart_struct = {}
                chart_struct["type"] = FlowType.FOR_LOOP_START
                chart_struct["val"] = "for loop start"
                chart_struct["depth"] = depth
                chart_struct_dict_list.append(chart_struct)

            # 関数呼び出し
            elif "CALL_EXPR" in flow_type:
                chart_struct = {}
                chart_struct["type"] = FlowType.DEFINED_PROCESS
                chart_struct["val"] = line.split()[1]
                chart_struct["depth"] = depth
                chart_struct_dict_list.append(chart_struct)

            # IF分岐の始端
            elif "IF_STMT" in flow_type:
                if_branch_start_depth_stack.append(depth)
                chart_struct = {}
                chart_struct["type"] = FlowType.IF
                chart_struct["val"] = "xxx = yyy?"
                chart_struct["depth"] = depth
                chart_struct_dict_list.append(chart_struct)

    return chart_struct_dict_list


def make_chart_xml(template_dict: dict, analysys_result):
    flows = make_chart_structure(analysys_result)

    start_id = 2
    with open("out/automake.xml", mode="w") as f:
        start_x, start_y = 80, 40
        render_param = {"x": start_x, "y": start_y}
        f.write(template_dict["flow_start"].render(render_param))

        prev_id = start_id
        id = start_id + 1
        x = start_x
        y = start_y + 80
        arrow_id = 1000
        for flow in flows:
            render_param = {"id": id, "text": flow["val"], "x": x, "y": y}
            f.write(template_dict[f"{flow['type'].name.lower()}"].render(render_param))

            render_param = {"id": arrow_id, "source_id": prev_id, "target_id": id}
            f.write(template_dict["arrow"].render(render_param))

            prev_id = id
            if flow["type"] == FlowType.IF:
                y += 120
            else:
                y += 80
            id += 1
            arrow_id += 1

        render_param = {"id": arrow_id, "source_id": prev_id, "target_id": id}
        f.write(template_dict["arrow"].render(render_param))
        render_param = {"id": id, "x": x, "y": y}
        f.write(template_dict["flow_end"].render(render_param))


def main():
    template_dict = load_templates()
    analysys_result = read_analysys_file("./result_analysis.yaml")
    make_chart_xml(template_dict, analysys_result)


if __name__ == "__main__":
    main()
