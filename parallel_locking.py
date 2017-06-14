import multiprocessing
import sys
import threading


# win32 has the multiprocessing module, but it's not clear to me how
# to get the locks shared between all the workers, so use
# single-threaded processing instead.  (Use UNIX for speed.)
_is_single_threaded = sys.platform == "win32"


def is_single_threaded():
    return _is_single_threaded


def make_lock(name):
    if _is_single_threaded:
        return theading.Lock()
    else:
        # Help to guard against children creating the same lock repeatedly.
        # Each lock should only be created once per run.
        print("DEBUG: creating multiprocessing.Lock for %s" % name)
        sys.stdout.flush()
        return multiprocessing.Lock()
