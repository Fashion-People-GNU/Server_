import yaml
from easydict import EasyDict


def read_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        cfg = yaml.safe_load(file)
    return EasyDict(cfg)


# 설정 파일 경로
yaml_file_path = rf'clothes_kmodes\config\config.yaml'

# YAML 파일 읽기
config = read_yaml(yaml_file_path)
kproto_model_path = config.paths.kproto_model_path
final_result_path = config.paths.final_result_path
final_result_with_cluster_path = config.paths.final_result_with_cluster_path
json_path = config.paths.json_path