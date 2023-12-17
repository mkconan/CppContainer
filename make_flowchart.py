from jinja2 import Template, Environment, FileSystemLoader
from util import calc_indent_depth

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


def read_analysis_file(file_path: str):
    with open(file_path, mode="r") as f:
        return f.readlines()


start_id = 2


def make_chart_xml(template_dict: dict, analysys_result):
    with open("out/automake.xml", mode="w") as f:
        render_param = {"x": 80, "y": 40}
        f.write(template_dict["flow_start"].render(render_param))

        render_param = {"id": 3, "text": "for start", "x": 80, "y": 100}
        f.write(template_dict["for_loop_start"].render(render_param))

        render_param = {"id": 4, "source_id": start_id, "target_id": 3}
        f.write(template_dict["arrow"].render(render_param))

        render_param = {"id": 5, "text": "process", "x": 80, "y": 200}
        f.write(template_dict["process"].render(render_param))

        render_param = {"id": 6, "text": "for end", "x": 80, "y": 240}
        f.write(template_dict["for_loop_end"].render(render_param))

        render_param = {"id": 7, "x": 80, "y": 300}
        f.write(template_dict["flow_end"].render(render_param))


def main():
    template_dict = load_templates()
    analysis_result = read_analysis_file("./result_analysis.yaml")
    make_chart_xml(template_dict, analysis_result)


if __name__ == "__main__":
    main()
