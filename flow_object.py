from enum import Enum
from io import TextIOWrapper
from typing import List
import uuid
from abc import ABC, abstractmethod


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


class FlowShape(ABC):
    def __init__(self) -> None:
        super().__init__()
        self._id: int = uuid.uuid4().int

    @abstractmethod
    def draw(self, template_dict: dict, f: TextIOWrapper):
        raise NotImplementedError

    @property
    def id(self):
        return self._id


class FlowNode(FlowShape):
    cur_if_root_id_stack: List[int] = []
    cur_depth_stack: List[dict] = []
    cur_flow_depth: int = 0
    cur_if_depth: int = 0

    def __init__(self, flow_type, text, line_no) -> None:
        super().__init__()
        self._flow_type: FlowType = flow_type
        self._text: str = text
        self._flow_depth: int = FlowNode.cur_flow_depth
        self._if_depth: int = FlowNode.cur_if_depth
        if self._flow_type == FlowType.IF:
            FlowNode.push_if_root_id_stack(self._id)
        self._if_root_id_stack: List[int] = FlowNode.cur_if_root_id_stack.copy()
        self._line_no: int = line_no
        self._is_draw_flow: bool = False

    @classmethod
    def push_if_root_id_stack(cls, id: int):
        cls.cur_if_root_id_stack.append(id)

    @classmethod
    def pop_if_root_id_stack(cls):
        cls.cur_if_root_id_stack.pop()

    @classmethod
    def push_depth_stack(cls, d: dict):
        cls.cur_depth_stack.append(d)

    @classmethod
    def pop_depth_stack(cls):
        cls.cur_depth_stack.pop()

    @classmethod
    def add_if_depth(cls, depth: int):
        cls.cur_if_depth += depth

    @classmethod
    def add_flow_depth(cls, depth: int):
        cls.cur_flow_depth += depth

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
    def is_draw_flow(self):
        return self._is_draw_flow

    def set_position(self, x: int, y: int):
        self.x = x
        self.y = y

    def draw(self, template_dict: dict, f: TextIOWrapper):
        if self._is_draw_flow == False:
            render_param = {
                "id": self._id,
                # "text": f"{self._id} {self.text}  L{self._line_no} FLOW{self.flow_depth} IF{self.if_depth}\n{self._if_root_id_stack}",
                "text": f"{self._text} L{self._line_no}",
                "x": self.x,
                "y": self.y,
            }
            f.write(template_dict[f"{self._flow_type.name.lower()}"].render(render_param))
            # 描画済であることを記録する
            self._is_draw_flow = True


def contains_if_root(target_flow: FlowNode, ref_flow: FlowNode) -> bool:
    return set(target_flow._if_root_id_stack) >= set(ref_flow._if_root_id_stack)


class Arrow(FlowShape):
    def __init__(self, id, source_id, target_id) -> None:
        self._id = id
        self._source_id = source_id
        self._target_id = target_id

    def draw(self, template_dict: dict, f: TextIOWrapper):
        render_param = {"id": self._id, "source_id": self._source_id, "target_id": self._target_id}
        f.write(template_dict["arrow"].render(render_param))
        return self._id + 1
