import logging
import sqlite3
from logging.handlers import RotatingFileHandler

def setup_logging(log_file_path='system_log.log', db_file_path='system_log.db'):
    # 创建一个 logger
    logger = logging.getLogger('my_system_logger')
    logger.setLevel(logging.DEBUG)

    # 创建一个文件处理器，用于将日志写入文件
    file_handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.DEBUG)

    # 创建一个 SQLite 处理器，用于将日志写入 SQLite 数据库
    db_connection = sqlite3.connect(db_file_path)
    db_handler = logging.handlers.SQLiteHandler(db_connection)
    db_handler.setLevel(logging.INFO)

    # 创建一个控制台处理器，用于将日志输出到控制台
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建一个格式化器，定义日志的显示格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    db_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 将处理器添加到 logger
    logger.addHandler(file_handler)
    logger.addHandler(db_handler)
    logger.addHandler(console_handler)

    return logger

if __name__ == "__main__":
    # 设置日志
    logger = setup_logging()

    # 记录不同级别的日志消息
    logger.debug('Debug message')
    logger.info('Informational message')
    logger.warning('Warning message')
    logger.error('Error message')
    logger.critical('Critical message')
