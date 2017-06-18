import multiprocessing
import multiprocessing.managers
import sys
import threading

import image_compressor
import parallel_locking


_compressor_mgr = None
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
    global _compressor_mgr
    global _image_compressor
    assert _compressor_mgr is None
    assert _image_compressor is None
    if parallel_locking.is_single_threaded():
        _image_compressor = image_compressor.SyncImageCompressor()
    else:
        _compressor_mgr = _ImageCompressorManager()
        _compressor_mgr.start()
        _image_compressor = _compressor_mgr.ImageCompressor()
    return _image_compressor


def image_compressor():
    assert _image_compressor is not None
    return _image_compressor


def _main_single(main):
    main(apply_=(lambda func, args: func(*args)),
         flush=(lambda: None))


def _main_parallel(main):
    # We must have a "fork" start method so that locks are inherited.
    # Otherwise, each child will create its own independent locks, and there
    # will be no actual mutual exclusion.
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
