import math
import os
import re
import sys


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


# Use \\?\C:\path\file syntax to: (a) avoid path length limits and (b) avoid device files.
def abspath(path):
    if sys.platform != "win32":
        return os.path.abspath(path)
    else:
        path = os.path.abspath(path)
        if re.match(r"[a-zA-Z]:\\", path[0:3]):
            return "\\\\?\\" + path[0].upper() + path[1:]
        elif re.match(r"\\\\[^\\]+\\"):
            return "\\\\UNC\\" + path[2:]
        else:
            raise RuntimeError("ERROR: unrecognized Windows path: " + path)


def image_extension(data):
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    elif data[:3] == b"GIF":
        return ".gif"
    elif data[:2] == b"\xff\xd8" and data[-2:] == b"\xff\xd9":
        return ".jpg"
    elif data[:4].lower() == b"<svg":
        return ".svg"
    else:
        return None
