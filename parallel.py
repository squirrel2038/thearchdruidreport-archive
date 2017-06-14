import multiprocessing
import sys
import threading

import image_compressor
import parallel_locking


# win32 has the multiprocessing module, but it's not clear to me how
# to get the locks shared between all the workers, so use
# single-threaded processing instead.  (Use UNIX for speed.)
_is_single_threaded = sys.platform == "win32"
_image_compressor = None


class _ImageCompressorManager(multiprocessing.managers.BaseManager):
    pass

_ImageCompressorManager.register("ImageCompressor", image_compressor.ImageCompressor, exposed=[
    "start_compress_async",
    "compress",
    "has_cached",
])


def init_image_compressor():
    # This initialization must be delayed until all modules' locks have been
    # constructed.
    global _image_compressor
    assert _image_compressor is None
    if parallel_locking.is_single_threaded():
        _image_compressor = image_compressor.SyncImageCompressor()
    else:
        compressor_mgr = _ImageCompressorManager()
        compressor_mgr.start()
        _image_compressor = compressor_mgr.ImageCompressor()
    return _image_compressor


def image_compressor():
    assert _image_compressor is not None
    return _image_compressor


def _main_single(main):
    global _image_compressor
    _image_compressor = image_compressor.SyncImageCompressor()

    main(apply_=(lambda func, args: func(*args)),
         flush=(lambda: None))


def _main_parallel(main):
    # We must have a "fork" start method so that locks are inherited.
    # Otherwise, each child will create its own independent locks, and there
    # will be no actual mutual exclusion.
    global _image_compressor
    compressor_mgr = _ImageCompressorManager()
    compressor_mgr.start()
    _image_compressor = compressor_mgr.ImageCompressor()
    assert multiprocessing.get_start_method() == "fork"
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        tasks = []
        main(apply_=(lambda func, args: tasks.append(pool.apply_async(func, args))),
             flush=(lambda: [t.get() for t in tasks] and None))
        for t in tasks:
            t.get()


def run_main(main):
    if parallel_locking.is_single_threaded():
        _main_single(main)
    else:
        _main_parallel(main)
