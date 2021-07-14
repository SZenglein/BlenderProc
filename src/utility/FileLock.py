import fcntl


class FileLock:

    def __init__(self, lock_path):
        self._lock_path = lock_path

    def __enter__(self):
        self.lock = open(self._lock_path, 'w')
        fcntl.flock(self.lock, fcntl.LOCK_EX)

    def __exit__(self, exc_type, exc_val, exc_tb):
        fcntl.flock(self.lock, fcntl.LOCK_UN)
        self.lock.close()
