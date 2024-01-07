def is_contain_keyword(text: str, keywords: list):
    for keyword in keywords:
        compare_keyword = keyword.lower().strip()
        if compare_keyword in text.lower():
            return True

    return False


def find_user_by_path(user_list: list, path: str):
    for user in user_list:
        keywords_list = user['keywords']
        if is_contain_keyword(path, keywords_list):
            return user

    return None

def is_debug_process(process_cmdline_list: list):
    for line in process_cmdline_list:
        if line.split('/')[-1] == 'python' or line == 'python':
            process_cmdline_list.remove(line)

    if any(keyword in process_cmdline_list[0] for keyword in ['vscode-server', 'debugpy']):
        return True
    else:
        return None