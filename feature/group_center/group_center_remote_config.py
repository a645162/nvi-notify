import json

from group_center.core.feature.remote_config import get_env_json_str

from feature.utils.logs import get_logger

logger = get_logger()


def init_remote_env_list():
    from config.settings import EnvironmentManager

    json_str = get_env_json_str()

    env_dict = json.loads(json_str)
    if isinstance(env_dict, dict):
        print("-" * 20)
        print("Remote Env")
        for key in env_dict.keys():
            print(f"{key}: {env_dict[key]}")
        print("-" * 20)

        EnvironmentManager.all_env_dict.update(env_dict)


if __name__ == "__main__":
    json_text = get_env_json_str()
    print(json_text)

    print()
