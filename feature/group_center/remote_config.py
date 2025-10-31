import json

from group_center.core.feature.remote_config import get_env_json_str

from feature.utils.logs import get_logger

logger = get_logger()


def init_remote_env_list() -> None:
    from config.settings import EnvironmentManager

    try:
        json_str = get_env_json_str()
        
        # 检查是否为空字符串或None
        if not json_str or json_str.strip() == "":
            logger.warning("Remote config returned empty string, skipping remote environment configuration")
            return
            
        env_dict = json.loads(json_str)
        if isinstance(env_dict, dict):
            logger.info("-" * 20)
            logger.info("Remote Env")
            logger.info("-" * 20)
            for key in env_dict.keys():
                logger.info(f"{key}: {env_dict[key]}")
            logger.info("-" * 20)

            EnvironmentManager.all_env_dict.update(env_dict)
            
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse remote config JSON: {e}. Using local configuration only.")
    except Exception as e:
        logger.warning(f"Failed to get remote configuration: {e}. Using local configuration only.")


if __name__ == "__main__":
    json_text = get_env_json_str()
    print(json_text)

    print()
