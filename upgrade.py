import os


def get_upgrade_command(package_name: str):
    return f"pip install --upgrade {package_name}"


os.system(get_upgrade_command("nvitop"))
os.system("pip install --upgrade li-group-center -i https://pypi.python.org/simple")
