from jinja2 import Template, Environment, FileSystemLoader
from util import calc_indent_depth

template_flow_list = [
    "flow_start",
    "flow_end",
    "for_start",
    "for_end",
    "if",
    "arrow",
    "process",
    "defined_process",
]

def load_templates():
    env = Environment(loader=FileSystemLoader('templates'))
    
    template_dict = {}
    for flow in template_flow_list:
        template = env.get_template(f"{flow}.j2")
        template_dict[flow] = template
        
    return template_dict

def read_analysis_file(file_path: str):
    with open(file_path, mode='r') as f:
        return f.readlines()
    
def make_chart_xml(template_dict, analysys_result):
    
    with open("out/automake.xml", mode='w') as f:
        f.write(template_dict["flow_start"].render())
        
        process_param = {"id": 5, "text": "process", "x": 120, "y": 200}
        f.write(template_dict["process"].render(process_param))
        
        flow_end_param = {"id": 7, "y": 240}
        f.write(template_dict["flow_end"].render(flow_end_param))
    
    

def main():
    template_dict = load_templates()
    analysis_result = read_analysis_file("./result_analysis.yaml")
    make_chart_xml(template_dict, analysis_result)
    
    
if __name__ == "__main__":
    main()