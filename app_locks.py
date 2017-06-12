import threading
import multiprocessing


class AppLocks:
    def __init__(self, is_single_threaded):
        assert isinstance(is_single_threaded, bool)
        self._is_single_threaded = is_single_threaded
        self.web_cache_lock = self._make_lock()
        self.img_cache_lock = self._make_lock()
        self.output_image_lock = self._make_lock()

    def _make_lock(self):
        return threading.Lock() if self._is_single_threaded else multiprocessing.Lock()
