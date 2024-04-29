import os
import glob
from typing import List


def get_files_with_extension(
    directory: str, extension: str, recursive: bool = False
) -> List[str]:
    files = []
    if recursive:
        search_path = os.path.join(directory, f"**/*.{extension}")
    else:
        search_path = os.path.join(directory, f"*.{extension}")
    for file_path in glob.glob(search_path, recursive=recursive):
        files.append(os.path.abspath(file_path))
    return files


if __name__ == "__main__":

    files_list = get_files_with_extension("../../users", "yaml", True)

    # 打印文件列表
    for file_path in files_list:
        print(file_path)
