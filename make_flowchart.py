from jinja2 import Template, Environment, FileSystemLoader
from util import calc_indent_depth
import re
from enum import Enum
from pprint import pprint
from io import TextIOWrapper
from typing import Tuple, List
import sys
import html

DEFAULT_DEPTH = 3
IF_FLOW_W = 240
IF_FLOW_H = 80
NORMAL_FLOW_H = 40
NORMAL_FLOW_W = 240
ARROW_L = 40
MARGIN = 40

template_dict = {}
source_code = []


class FlowType(Enum):
    FLOW_START = 0
    FLOW_END = 1
    FOR_LOOP_START = 2
    FOR_LOOP_END = 3
    IF = 4
    ARROW = 5
    ELSE_START_ARROW = 6
    ELSE_END_ARROW = 7
    ELSE_NONE_ARROW = 8
    DEFINED_PROCESS = 9
    NORMAL_PROCESS = 10


class FlowNode:
    def __init__(self, id, flow_type, text, flow_depth, if_depth, if_root_id_stack, line) -> None:
        self._id: int = id
        self._flow_type: FlowType = flow_type
        self._next_id: int = self.get_next_id()
        self.text: str = text
        self._flow_depth: int = flow_depth
        self._if_depth: int = if_depth
        self._if_root_id_stack: List[int] = if_root_id_stack.copy()
        self._line_no: int = get_line_no(line)
        self._is_draw_flow: bool = False

    @property
    def id(self):
        return self._id

    @property
    def next_id(self):
        return self._next_id

    @property
    def flow_type(self):
        return self._flow_type

    @property
    def flow_depth(self):
        return self._flow_depth

    @property
    def if_depth(self):
        return self._if_depth

    @property
    def if_root_id_stack(self):
        return self._if_root_id_stack

    @property
    def is_draw_flow(self):
        return self._is_draw_flow

    def set_position(self, x: int, y: int):
        self.x = x
        self.y = y

    def draw_node(self, f: TextIOWrapper):
        if self._is_draw_flow == False:
            render_param = {
                "id": self._id,
                # "text": f"{self._id} {self.text}  L{self._line_no} FLOW{self.flow_depth} IF{self.if_depth}\n{self._if_root_id_stack}",
                "text": f"{self.text} L{self._line_no}",
                "x": self.x,
                "y": self.y,
            }
            f.write(template_dict[f"{self._flow_type.name.lower()}"].render(render_param))
            # 描画済であることを記録する
            self._is_draw_flow = True

    def get_next_id(self):
        if self._flow_type == FlowType.IF:
            return self._id + 3
        else:
            return self._id + 1


class Arrow:
    def __init__(self, id, source_id, target_id) -> None:
        self._id = id
        self._source_id = source_id
        self._target_id = target_id

    def draw_arrow(self, f: TextIOWrapper):
        render_param = {"id": self._id, "source_id": self._source_id, "target_id": self._target_id}
        f.write(template_dict["arrow"].render(render_param))
        return self._id + 1


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


def get_if_text(line_no: int):
    # ifの中身が複数行の場合があるため
    if_lines = "".join(source_code[line_no - 1 : line_no + 2])
    match = re.match(r"\s*if \((.*)\)", if_lines)
    if match:
        # 不等号記号をHTML形式に合うように変換
        if_text = html.escape(match.group(1))
        return if_text
    else:
        return None


def get_for_text(line_no: int):
    # forの中身が複数行の場合があるため
    for_lines = "".join(source_code[line_no - 1 : line_no + 2])
    match = re.match(r"\s*for \((.*)\)", for_lines)
    if match:
        # 不等号記号をHTML形式に合うように変換
        for_2nd_text = html.escape(match.group(1).split(";")[1][1:])
        return for_2nd_text
    else:
        return None


def make_chart_structure(analysys_result: List[str], func_name: str = "main") -> List[FlowNode]:
    flow_list: List[FlowNode] = []
    is_detect_func = False
    depth_stack = []
    id = 3
    flow_depth = 0
    if_depth = 0
    if_root_id_stack = []
    for line in analysys_result:
        depth = get_depth(line)
        if f"FUNCTION_DECL: {func_name}" in line:
            is_detect_func = True
            func_depth = depth

        elif is_detect_func:
            # 探した関数名から抜ければ終了
            if depth <= func_depth:
                break

            flow_type = line.split()[0].removesuffix(":")

            # depthスタック確認
            if len(depth_stack):
                for d in reversed(depth_stack):
                    if depth <= d["depth"]:
                        depth_stack.pop()
                        if d["name"] == "for_start":
                            flow = FlowNode(
                                id, FlowType.FOR_LOOP_END, "for loop end", flow_depth, if_depth, if_root_id_stack, line
                            )
                            flow_list.append(flow)
                            id = flow.next_id
                        elif d["name"] == "if_start":
                            if_depth -= 1
                            if_root_id_stack.pop()
                        elif d["name"] == "else_if_start":
                            if_depth -= 2
                            flow_depth -= 1
                            if_root_id_stack.pop()
                        elif d["name"] == "else_start":
                            if_depth -= 1
                            flow_depth -= 1
                        else:
                            KeyError(f"Invalid keys. {d.keys()}")

            # forループの始端
            if flow_type == "FOR_STMT":
                d = {"name": "for_start", "depth": depth}
                depth_stack.append(d)
                flow = FlowNode(
                    id,
                    FlowType.FOR_LOOP_START,
                    get_for_text(get_line_no(line)),
                    flow_depth,
                    if_depth,
                    if_root_id_stack,
                    line,
                )
                flow_list.append(flow)
                id = flow.next_id

            # 関数呼び出し
            elif flow_type == "CALL_EXPR":
                flow = FlowNode(
                    id, FlowType.DEFINED_PROCESS, line.split()[1], flow_depth, if_depth, if_root_id_stack, line
                )
                flow_list.append(flow)
                id = flow.next_id

            # IF分岐の始端
            elif flow_type == "IF_STMT":
                depth_dict = {"name": "if_start", "depth": depth}
                depth_stack.append(depth_dict)
                if_root_id_stack.append(id)
                if_depth += 1
                flow = FlowNode(
                    id, FlowType.IF, get_if_text(get_line_no(line)), flow_depth, if_depth, if_root_id_stack, line
                )
                flow_list.append(flow)
                id = flow.next_id

            # ELSE IF節の始端
            elif flow_type == "ELSE_IF_STMT":
                if_depth += 2
                flow_depth += 1
                if_root_id_stack.append(id)
                depth_dict = {"name": "else_if_start", "depth": depth}
                depth_stack.append(depth_dict)
                flow = FlowNode(
                    id, FlowType.IF, get_if_text(get_line_no(line)), flow_depth, if_depth, if_root_id_stack, line
                )
                flow_list.append(flow)
                id = flow.next_id

            # ELSE節の始端
            elif flow_type == "ELSE_STMT":
                if_depth += 1
                flow_depth += 1
                d = {"name": "else_start", "depth": depth}
                depth_stack.append(d)

    return flow_list


def make_if_chart_xml(
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
    is_else_process = False
    # このフロー塊の最大flow深さ
    max_flow_depth = flow_depth
    # ifルートの時のflowの深さ elseの開始位置xを決める時に用いる
    if_route_max_flow_depth = flow_depth

    # リストの先頭はIF
    if_start_flow = flows[0]
    if_start_flow.set_position(if_x, if_y)
    if_start_flow.draw_node(f)

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
            arrow_id = arrow.draw_arrow(f)

            # IFが出てきた場合は再帰的にフロー図を作る
            if if_flow.flow_type == FlowType.IF:
                # 最初のifフローは入れる
                if_child_flows = []
                # if文の中にあるフローのリストを作成する
                for if_child_flow in flows[f_i:]:
                    if set(if_child_flow.if_root_id_stack) >= set(if_flow.if_root_id_stack):
                        if_child_flows.append(if_child_flow)
                    else:
                        break

                if_y, arrow_id, if_prev_id, if_route_max_flow_depth = make_if_chart_xml(
                    if_child_flows, if_depth + 1, flow_depth, if_x, if_y, arrow_id + 1, f
                )
                max_flow_depth = max(max_flow_depth, if_route_max_flow_depth)

            else:
                if_flow.set_position(if_x, if_y)
                if_flow.draw_node(f)
                if_prev_id = if_flow.id
            if_y += NORMAL_FLOW_H + ARROW_L

        # elseルートの作成
        elif if_flow.flow_depth >= flow_depth + 1:
            # 矢印を描画する
            # 最初のelse節の場合
            if is_else_process == False:
                is_else_process = True
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
                arrow_id = arrow.draw_arrow(f)

            # IFが出てきた場合は再帰的にフロー図を作る
            if if_flow.flow_type == FlowType.IF:
                # 最初のifフローは入れる
                if_child_flows = []
                # if文の中にあるフローのリストを作成する
                for if_child_flow in flows[f_i:]:
                    if set(if_child_flow.if_root_id_stack) >= set(if_flow.if_root_id_stack):
                        if_child_flows.append(if_child_flow)
                    else:
                        break
                else_y, arrow_id, else_prev_id, _ = make_if_chart_xml(
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
                if_flow.draw_node(f)
                else_y += NORMAL_FLOW_H + ARROW_L
                else_prev_id = if_flow.id
            max_flow_depth = if_route_max_flow_depth + 1

    # ifルートとelseルートでyが長い方を矢印の終端とする
    end_y = if_y if if_y > else_y else else_y

    # elseルートが何もなかった場合
    if is_else_process == False:
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


def make_chart_xml(analysys_result: List[str]):
    flows: List[FlowNode] = make_chart_structure(analysys_result)
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
        arrow_id = arrow.draw_arrow(f)

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
                    if set(if_child_flow.if_root_id_stack) >= set(flow.if_root_id_stack):
                        if_child_flows.append(if_child_flow)
                    else:
                        break

                arrow = Arrow(arrow_id, prev_id, flow.id)
                arrow_id = arrow.draw_arrow(f)
                y, arrow_id, prev_id, _ = make_if_chart_xml(if_child_flows, 1, 0, x, y, arrow_id, f)

            elif flow.flow_depth == 0:
                flow.set_position(x, y)
                flow.draw_node(f)

                # 矢印を描画する
                arrow = Arrow(arrow_id, prev_id, flow.id)
                arrow_id = arrow.draw_arrow(f)

                prev_id = flow.id
                y += NORMAL_FLOW_H + ARROW_L

        # flow図の最後の部分を描画
        for flow in reversed(flows):
            if flow.flow_depth == 0:
                pre_end_id = flow.id
                break
        arrow = Arrow(arrow_id, pre_end_id, end_id)
        _ = arrow.draw_arrow(f)
        render_param = {"id": end_id, "x": x, "y": y}
        f.write(template_dict["flow_end"].render(render_param))


def main():
    argv = sys.argv
    load_templates()
    laod_source_code(argv[1])
    analysys_result = read_analysys_file("./result_analysis.yaml")
    make_chart_xml(analysys_result)


if __name__ == "__main__":
    main()
