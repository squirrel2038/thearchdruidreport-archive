import math
import os


def get_file_data(path):
    with open(path, "rb") as fp:
        return fp.read()


def get_file_text(path):
    return get_file_data(path).decode("utf8")


def set_file_data(path, data):
    path_dir = os.path.dirname(path)
    if path_dir != "":
        makedir(path_dir)
    with open(path, "wb") as fp:
        fp.write(data)


def set_file_text(path, text):
    set_file_data(path, text.encode("utf8"))


def makedir(path):
    try:
        os.makedirs(path)
    except:
        if not os.path.isdir(path):
            raise


def mtime(path):
    try:
        return os.stat(path).st_mtime
    except:
        return -math.inf
