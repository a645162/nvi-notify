import sqlite3
import threading
from enum import Enum
from pathlib import Path
from queue import Empty, Queue

from src.config import settings
from src.entity import task_info
from src.monitor import enums
from src.utils import common_utils, logs

logger = logs.get_logger()


class SQLAction(Enum):
    INSERT = 0
    UPDATE = 1
    UPDATE_FINISH = 2
    CHECK_FINISH = 3
    DISCONNECT = 4


class SQLite:
    _queue = Queue()
    _thread = None

    def __init__(self, db_file_path: Path) -> None:
        self.table_name_header = "gpu_"
        self.db_file_path: Path = db_file_path
        self._start_worker_thread()

    def connect(self) -> None:
        try:
            self.conn = sqlite3.connect(self.db_file_path)
            self.cur = self.conn.cursor()
        except sqlite3.Error as e:
            logger.error(f"连接数据库失败: {e}")

    def create_table(self, gpu_id: int) -> None:
        table_name: str = self.table_name_header + str(gpu_id)
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

    def insert_task_data(self, task_info: task_info.TaskInfoForSql) -> None:
        self._queue.put((SQLAction.INSERT, task_info))

    def update_task_data(self, task_info: task_info.TaskInfoForSql) -> None:
        self._queue.put((SQLAction.UPDATE, task_info))

    def update_finish_task_data(self, task_info: task_info.TaskInfoForSql) -> None:
        self._queue.put((SQLAction.UPDATE_FINISH, task_info))

    def get_running_task_data(self, gpu_id: int) -> list:
        try:
            self.cur.execute(
                f"SELECT * FROM {self.table_name_header + str(gpu_id)} "
                f"WHERE finish_timestamp = 0 AND task_state != '{enums.TaskState.DEATH}'"
            )
            return self.cur.fetchall()
        except Exception as e:
            logger.error(e)
            raise RuntimeError(e)

    def check_finish_task(self, all_task_info: dict, gpu_id: int) -> None:
        self._queue.put((SQLAction.CHECK_FINISH, (all_task_info, gpu_id)))

    def select_data(self) -> None:
        pass

    def disconnect(self) -> None:
        self._queue.put((SQLAction.DISCONNECT, None))
        if self._thread is not None:
            self._thread.join()
        self.cur.close()
        self.conn.close()

    def _worker(self) -> None:
        self.connect()
        for gpu_id in range(settings.NUM_GPU):
            self.create_table(gpu_id)
        while True:
            try:
                action, data = self._queue.get()
                if action == SQLAction.INSERT:
                    self._insert_task_data(data)
                elif action == SQLAction.UPDATE:
                    self._update_task_data(data)
                elif action == SQLAction.UPDATE_FINISH:
                    self._update_finish_task_data(data)
                elif action == SQLAction.CHECK_FINISH:
                    self._check_finish_task(*data)
                elif action == SQLAction.DISCONNECT:
                    break
            except Empty:
                continue
            finally:
                self._queue.task_done()

    def _insert_task_data(self, task_info: task_info.TaskInfoForSql) -> None:
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

    def _update_task_data(self, task_info: task_info.TaskInfoForSql) -> None:
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

    def _update_finish_task_data(self, task_info: task_info.TaskInfoForSql) -> None:
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

    def _check_finish_task(self, all_task_info: dict, gpu_id: int) -> None:
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
                        self.table_name_header + str(gpu_id),
                        enums.TaskState.DEATH.value,
                    ),
                    (unfinished_task_data[1], gpu_id),
                )
                self.conn.commit()

    def _start_worker_thread(self) -> None:
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()


def setup_sqlit() -> SQLite:
    task_sql_dir = Path.resolve(Path("./sqlite_data"))
    common_utils.try_write_file(task_sql_dir)
    task_sql = SQLite(Path(task_sql_dir / f"{settings.SERVER_NAME}_task_info.db"))
    return task_sql


def get_sql() -> SQLite:
    return sqlite


sqlite = setup_sqlit()
