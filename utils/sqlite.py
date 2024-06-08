import os
import sqlite3

from config.settings import NUM_GPU, SERVER_NAME
from feature.monitor import TaskState
from feature.monitor.info.sql_task_info import TaskInfoForSQL
from utils.logs import get_logger

logger = get_logger()


class SQLite:
    def __init__(self, db_file_path: str = "task_info.db") -> None:
        self.table_name_header = "gpu_"
        self.connect(db_file_path)

    def connect(self, db_file_path):
        try:
            # TODO: 安全的多线程连接数据库
            self.conn = sqlite3.connect(db_file_path, check_same_thread=False)
            self.cur = self.conn.cursor()
        except sqlite3.Error as e:
            logger.error(f"连接数据库失败: {e}")

    def create_table(self, gpu_id: int):
        table_name = self.table_name_header + str(gpu_id)
        try:
            self.cur.execute(f"SELECT * FROM {table_name}")
        except sqlite3.OperationalError:
            sql_text = """
            CREATE TABLE IF NOT EXISTS {}(
                task_id INTEGER PRIMARY KEY,
                process_id INTEGER,
                gpu_id INTEGER,
                username TEXT,
                task_state TEXT,
                create_timestamp INTEGER,
                finish_timestamp INTEGER,
                running_time_in_seconds INTEGER,
                gpu_mem_usage_max TEXT,
                is_debug BOOLEAN,
                is_multi_gpu BOOLEAN,
                screen_session_name TEXT,
                conda_env TEXT,
                project_name TEXT,
                python_file TEXT
            );
            """
            self.cur.execute(sql_text.format(table_name))

    def insert_task_data(self, task_info: TaskInfoForSQL):
        table_name = self.table_name_header + str(task_info.gpu_id)
        self.cur.execute(
            f"SELECT * FROM {table_name} WHERE task_id = ?", (task_info.task_idx,)
        )
        if self.cur.fetchone():
            self.update_task_data(task_info)
            return
        insert_sql_text = """
            INSERT INTO {} (
                task_id,
                process_id,
                gpu_id,
                username,
                task_state,
                create_timestamp,
                finish_timestamp,
                running_time_in_seconds,
                gpu_mem_usage_max,
                is_debug,
                is_multi_gpu,
                screen_session_name,
                conda_env,
                project_name,
                python_file
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """
        self.cur.execute(
            insert_sql_text.format(table_name),
            (
                task_info.task_idx,
                task_info.pid,
                task_info.gpu_id,
                task_info.user,
                task_info.task_state.value,
                task_info.create_timestamp,
                task_info.finish_timestamp,
                task_info.running_time_in_seconds,
                task_info.gpu_mem_usage_max,
                task_info.is_debug,
                task_info.is_multi_gpu,
                task_info.screen_session_name,
                task_info.conda_env,
                task_info.project_name,
                task_info.python_file,
            ),
        )
        self.conn.commit()

    def update_task_data(self, task_info: TaskInfoForSQL):
        update_sql_text = (
            "UPDATE {} "
            "SET task_state = ?, "
            "running_time_in_seconds = ?, "
            "gpu_mem_usage_max = ? "
            "WHERE task_id = ?;"
        )
        self.cur.execute(
            update_sql_text.format(self.table_name_header + str(task_info.gpu_id)),
            (
                task_info.task_state.value,
                task_info.running_time_in_seconds,
                task_info.gpu_mem_usage_max,
                task_info.task_idx,
            ),
        )
        self.conn.commit()

    def update_finish_task_data(self, task_info: TaskInfoForSQL):
        update_sql_text = (
            "UPDATE {} "
            "SET task_state = ?, "
            "finish_timestamp = ?, "
            "running_time_in_seconds = ?, "
            "gpu_mem_usage_max = ? "
            "WHERE task_id = ?;"
        )
        self.cur.execute(
            update_sql_text.format(self.table_name_header + str(task_info.gpu_id)),
            (
                task_info.task_state.value,
                task_info.finish_timestamp,
                task_info.running_time_in_seconds,
                task_info.gpu_mem_usage_max,
                task_info.task_idx,
            ),
        )
        self.conn.commit()

    def get_running_task_data(self, gpu_id):
        try:
            self.cur.execute(
                f"SELECT * FROM {self.table_name_header + str(gpu_id)} "
                f"WHERE finish_timestamp = 0 AND task_state != '{TaskState.DEATH}'"
            )
            return self.cur.fetchall()
        except Exception as e:
            logger.error(e)
            raise

    def check_finish_task(self, all_task_info: dict, gpu_id: int):
        unfinished_task_datas = self.get_running_task_data(gpu_id)
        running_task_pids = all_task_info.keys()

        for unfinished_task_data in unfinished_task_datas:
            if (
                unfinished_task_data[1] not in running_task_pids
                and unfinished_task_data[6] == 0
            ):
                update_sql_text = (
                    "UPDATE {} "
                    "SET task_state = '{}' "
                    "WHERE process_id = ? AND gpu_id = ? AND finish_timestamp= 0;"
                )
                self.cur.execute(
                    update_sql_text.format(
                        self.table_name_header + str(gpu_id), TaskState.DEATH.value
                    ),
                    (unfinished_task_data[1], gpu_id),
                )
                self.conn.commit()

    def select_data(self):
        pass

    def disconnect(self):
        self.cur.close()
        self.conn.close()


task_sql_dir = os.path.join("./sqlite_data")

# Check SQLite Directory
if not os.path.exists(path=task_sql_dir):
    os.mkdir(task_sql_dir)

# Permission Check
try:
    test_file = os.path.join(task_sql_dir, "test.db")
    with open(test_file, "w") as f:
        f.write(str(test_file))
    os.remove(test_file)
except Exception as e:
    print("Cannot write to SQLite directory.")
    print(e)
    exit(1)


task_sql = SQLite(os.path.join(task_sql_dir, f"{SERVER_NAME}_task_info.db"))

for gpu_id in range(NUM_GPU):
    task_sql.create_table(gpu_id)


def get_sql():
    return task_sql
