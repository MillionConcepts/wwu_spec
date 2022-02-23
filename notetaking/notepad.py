import atexit
import time
from multiprocessing.shared_memory import ShareableList, SharedMemory
from random import randint, randbytes
from typing import Any

from notetaking.codecs import json_pickle_encoder, json_pickle_decoder
from notetaking.memutilz import create_block


# TODO: we could have the index stored at some other randomized address, but
#  i very much like the idea of these classes being portable between processes
#  by referencing only a single string
class Paper:
    """parent class for notes. defines only index methods."""

    def __init__(self, prefix):
        super().__init__()
        self.prefix = prefix
        self._index_cache = []
        self._index_length = 0

    def _address(self, key):
        return f"{self.prefix}_{key}"

    def _index_memory(self):
        return ShareableList(name=self._address("index"))

    def index(self, sync=True):
        if sync is True:
            # TODO: optimize all this stuff with lookahead and lookbehind
            #  for speed, etc.
            self._index_cache = []
            ix = 0
            for ix, key in enumerate(self._index_memory()):
                if key == b"":
                    break
                self._index_cache.append(key)
            self._index_length = ix
        return self._index_cache

    def __str__(self):
        return f"{self.__class__.__name__} with keys {self.index()}"

    def __repr__(self):
        return self.__str__()


# TODO: dumb version without an index for faster assignment


class NoteViewer(Paper):
    """read-only notepad"""

    def __init__(self, prefix, decoder=json_pickle_decoder):
        super().__init__(prefix)
        self.decoder = decoder

    def get_raw(self, key):
        try:
            block = SharedMemory(self._address(key))
        except FileNotFoundError:
            return None
        stream = block.buf.tobytes()
        return stream

    # TODO: should I raise errors instead of returning none for missing keys
    #  when accessed with slice notation? that is more 'standard'
    def __getitem__(self, key, decoder=json_pickle_decoder):
        stream = self.get_raw(key)
        if stream is None:
            return stream
        return json_pickle_decoder(stream)

    def get(self, key):
        return self.__getitem__(key)

    def keys(self):
        return self.index()

    def iterkeys(self):
        for key in self.index():
            yield key

    def itervalues(self):
        """return an iterator over entries in the cache"""
        for key in self.index():
            yield self[key]

    def iteritems(self):
        """return an iterator over key / value pairs in the cache"""
        for key in self.index():
            yield key, self[key]

    def dump(self, key, fn=None, mode="wb"):
        if fn is None:
            fn = f"{self.prefix}_{key}".replace(".", "_")
        with open(fn, mode) as file:
            # noinspection PyTypeChecker
            file.write(self.get_raw(key))


class Notepad(NoteViewer):
    """full read-write notepad"""

    def __init__(
        self,
        prefix,
        encoder=json_pickle_encoder,
        decoder=json_pickle_decoder,
    ):
        super().__init__(prefix, decoder)
        try:
            self.index()
        except FileNotFoundError:
            raise FileNotFoundError(
                "the memory space for this Notepad has not been initialized "
                "(or has been deleted). Try constructing it with "
                "Notepad.open()."
            )
        self.encoder = encoder
        self._lock_key = randbytes(4)

    def __setitem__(self, key: str, value: Any, exists_ok: bool = True):
        if key in (["index", "index_lock"]):
            raise KeyError("'index' and 'index_lock' are reserved key names")
        encoded = self.encoder(value)
        size = len(encoded)
        try:
            block = create_block(self._address(key), size, exists_ok)
        except FileExistsError:
            raise KeyError(
                f"{key} already exists in this object's cache. pass "
                f"exists_ok=True to overwrite it."
            )
        block.buf[:] = encoded
        block.close()
        if key not in self.index():
            self._add_index_key(key)

    def __delitem__(self, key):
        if key in (["index", "index_lock"]):
            raise KeyError("'index' and 'index_lock' are reserved key names")
        try:
            block = SharedMemory(self._address(key))
            block.unlink()
            block.close()
            self._remove_index_key(key)
        except FileNotFoundError:
            raise KeyError(f"{key} not apparently assigned")

    def set(self, key, value):
        return self.__setitem__(key, value)

    def close(self, dump=False):
        for key in self.index():
            if dump is True:
                self.dump(key)
            del self[key]
        for block in self._lock_memory(), self._index_memory().shm:
            block.unlink()
            block.close()
        atexit.unregister(self.close)

    def clear(self):
        for key in self.index():
            del self[key]

    def _lock_memory(self):
        return SharedMemory(self._address("index_lock"))

    def _acquire_index_lock(self, timeout=0.1, increment=0.0001):
        acquired = False
        time_waiting = 0
        while acquired is False:
            lock_memory = self._lock_memory()
            current_key = lock_memory.buf.tobytes()
            if current_key == self._lock_key:
                acquired = True
            elif current_key == b"\x00\x00\x00\x00":
                lock_memory.buf[:] = self._lock_key
            # the extra loop here is for a possibly-unnecessary double check
            # that someone else didn't write their key to the lock at the
            # exact same time.
            else:
                time_waiting += increment
                if increment > timeout:
                    raise TimeoutError("timed out waiting for index lock")
                time.sleep(increment)

    def _release_index_lock(self, release_only_mine=True):
        lock_memory = self._lock_memory()
        current_key = lock_memory.buf.tobytes()
        if (current_key != self._lock_key) and (release_only_mine is True):
            raise ConnectionRefusedError
        lock_memory.buf[:] = b"\x00\x00\x00\x00"

    def _add_index_key(self, key):
        self._acquire_index_lock()
        self.index()
        self._index_memory()[self._index_length] = key
        self._release_index_lock()

    def _remove_index_key(self, key):
        self._acquire_index_lock()
        index = self.index()
        index_memory = self._index_memory()
        iterator = enumerate(index)
        ix, item = None, None
        while item != key:
            try:
                ix, item = next(iterator)
            except StopIteration:
                raise KeyError(f"{key} not found in this Notepad's index.")
        index_memory[ix] = index_memory[len(index) - 1]
        index_memory[len(index) - 1] = b""
        self._release_index_lock()

    @classmethod
    def open(
        cls,
        prefix=None,
        index_length=256,
        max_key_characters=128,
        exists_ok=True,
        cleanup_on_exit=True,
        **init_kwargs,
    ):
        if prefix is None:
            prefix = randint(100000, 999999)
        _index_lock = create_block(
            f"{prefix}_index_lock", exists_ok=exists_ok, size=4
        )
        # TODO: handle exists_ok for ShareableList
        _index_block = ShareableList(
            [b"\x00" * max_key_characters for _ in range(index_length)],
            name=f"{prefix}_index",
        )

        notepad = Notepad(prefix, **init_kwargs)
        if cleanup_on_exit is True:
            # if SharedMemory objects are instantiated in __main__,
            # multiprocessing.util._exit_function() generally does a good job
            # of cleaning them up. however, blocks created in child processes
            # will often not be cleanly and automatically unlinked.
            atexit.register(notepad.close)
        return notepad

# TODO: cleanup
class Sticky:
    def __init__(
        self,
        address,
        decoder=json_pickle_decoder,
    ):
        self._address = address
        self.decoder = decoder
        self._value = None
        self.stuck = False

    @classmethod
    def note(
        cls,
        obj,
        address=None,
        encoder=json_pickle_encoder,
        decoder=json_pickle_decoder,
        exists_ok=False
    ):
        if address is None:
            addr = randint(100000, 999999)
            if hasattr(obj, __name__):
                address = f"{obj.__name__}_{addr}"
            else:
                address = str(addr)
        encoded = encoder(obj)
        size = len(encoded)
        block = create_block(address, size, exists_ok=exists_ok)
        block.buf[:] = encoded
        return Sticky(address, decoder)

    @property
    def value(self):
        if self.stuck is True:
            return self._value
        try:
            block = SharedMemory(self._address)
        except FileNotFoundError:
            return None
        stream = block.buf.tobytes()
        if stream is None:
            decoded = stream
        else:
            decoded = self.decoder(stream)
        self.stuck = True
        return decoded

    def close(self):
        block = SharedMemory(self._address)
        block.unlink()
        block.close()

    def __str__(self):
        if self.stuck:
            return self.value.__str__()
        else:
            return 'unstuck sticky'

    def __repr__(self):
        if self.stuck:
            return self.value.__repr__()
        else:
            return 'unstuck sticky'
