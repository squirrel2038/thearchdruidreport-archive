import PIL.Image
import io
import hashlib
import multiprocessing
import os
import subprocess
import threading

import util
import web_cache


IMG_CACHE_DIR = os.path.dirname(__file__) + "/img_cache"
_fs_lock = None


def set_fs_lock(lock):
    global _fs_lock
    _fs_lock = lock


def _multiproc_init(lock):
    set_fs_lock(lock)
    web_cache.set_fs_lock(lock)


def _exists_locked(path):
    with _fs_lock:
        return os.path.exists(path)


def _compress_image(job, dont_block):
    name, url, resample_size, guetzli_quality = job

    # guetzli_quality should evaluate to False to disable guetzli.  If the
    # image file has an alpha channel, it must not be converted to JPEG,
    # because JPEG conversion would destroy the channel.

    urlhash = "-" + web_cache.urlhash(url)

    # First store the original, uncompressed file, in case we fall back to it.
    orig_bytes = web_cache.get(url)
    orig_ext = util.image_extension(orig_bytes)
    orig_path = util.abspath(os.path.join(IMG_CACHE_DIR, name + urlhash + orig_ext))
    with _fs_lock:
        if not os.path.exists(orig_path):
            if dont_block:
                return None
            util.set_file_data(orig_path, orig_bytes)
    cur_path = orig_path

    # Save as PNG format.
    name_extra = ""
    if resample_size or (guetzli_quality and orig_ext not in [".png", ".jpg"]):
        if resample_size:
            name_extra += "-%dx%d" % resample_size
        new_path = util.abspath(os.path.join(IMG_CACHE_DIR, name + urlhash + name_extra + ".png"))
        if not _exists_locked(new_path):
            if dont_block:
                return None
            img = PIL.Image.open(cur_path)
            if resample_size:
                img = img.resize(resample_size, PIL.Image.LANCZOS)
            with _fs_lock:
                img.save(new_path, "png")
        cur_path = new_path
        del new_path

    if guetzli_quality:
        name_extra += "-g%d" % guetzli_quality
        new_path = util.abspath(os.path.join(IMG_CACHE_DIR, name + urlhash + name_extra + ".jpg"))
        if not _exists_locked(new_path):
            if dont_block:
                return None
            tmp_path = os.path.join(IMG_CACHE_DIR, "tmp-%d-%d.jpg" % (os.getpid(), threading.get_ident()))
            output = subprocess.check_output([
                "guetzli", "--quality", str(guetzli_quality), cur_path, tmp_path
            ], stderr=subprocess.STDOUT)
            guetzli_output = output.decode().strip()
            if guetzli_output != "":
                print("WARNING: guetzli output on file '%s': %s" % (cur_path, guetzli_output))
            with _fs_lock:
                os.rename(tmp_path, new_path)
        cur_path = new_path
        del new_path

    new_bytes = util.get_file_data(cur_path)

    return (cur_path, name_extra, len(new_bytes))


def _compress_image_super(job, dont_block=False):
    name, url, resample_size, guetzli_quality, force_resampling = job

    ret = _compress_image((name, url, resample_size, guetzli_quality), dont_block)
    if ret is None:
        return None

    if force_resampling:
        assert resample_size
    else:
        # Reuse the original image if it's smaller.
        orig = _compress_image((name, url, None, 0), dont_block)
        assert orig is not None

        if orig[2] <= ret[2] and resample_size and guetzli_quality:
            # If the original file was smaller, we'll prefer it to the
            # resampled-and-compressed file.  First, though, try simply compressing
            # the unmodified original.
            ret = _compress_image((name, url, None, guetzli_quality), dont_block)
            if ret is None:
                return None

        if orig[2] <= ret[2]:
            ret = orig

    return (ret[0], ret[1])


# This class is responsible for coordinating the image compressor tasks.
class ImageCompressor:
    def __init__(self):
        assert _fs_lock
        self._pool = multiprocessing.Pool(processes=multiprocessing.cpu_count(),
                                          initializer=_multiproc_init, initargs=(_fs_lock,))
        self._jobs = {}
        self._jobs_lock = threading.Lock()

    def start_compress_async(self, job):
        self._start_compress_async(job)

    def compress(self, job):
        return self._start_compress_async(job).get()

    def has_cached(self, job):
        # Performance hack
        return _compress_image_super(job, dont_block=True) is not None

    # Returns a multiprocessing.pool.AsyncResult
    def _start_compress_async(self, job):
        with self._jobs_lock:
            if job not in self._jobs:
                self._jobs[job] = self._pool.apply_async(_compress_image_super, (job,))
            return self._jobs[job]


# This class does the same thing as ImageCompressor, but does not use workers.
class SyncImageCompressor:
    def __init__(self):
        self._jobs = {}

    def start_compress_async(self, job):
        self._compress(job)

    def compress(self, job):
        return self._compress(job)

    def has_cached(self, job):
        # Performance hack
        return _compress_image_super(job, dont_block=True) is not None

    def _compress(self, job):
        if job not in self._jobs:
            self._jobs[job] = _compress_image_super(job)
        return self._jobs[job]
