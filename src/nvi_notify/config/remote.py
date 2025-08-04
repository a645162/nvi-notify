import json

from group_center.core.feature import remote_config

from nvi_notify.utils import logs

logger = logs.get_logger()


def load_remote_config() -> None:
    from nvi_notify.config import settings  # noqa: PLC0415

    json_str = remote_config.get_env_json_str()

    env_dict = json.loads(json_str)
    if isinstance(env_dict, dict):
        logger.info("-" * 20)
        logger.info("Remote Env")
        logger.info("-" * 20)
        for key in env_dict.keys():
            logger.info(f"{key}: {env_dict[key]}")
        logger.info("-" * 20)

        settings.EnvironmentManager.all_env_dict.update(env_dict)


if __name__ == "__main__":
    json_text = remote_config.get_env_json_str()
    print(json_text)

    print()
