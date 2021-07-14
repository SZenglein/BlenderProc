from src.main.Module import Module
from src.utility.FileLock import FileLock
from src.utility.Utility import Utility


class MutexModule(Module):
    """
    Wraps a list of Modules that will not be run at the same time in case multiple scripts are running.
    The intended purpose is to be able to do setup work ahead of time while giving exclusive access to limited
    Resources.
    This ensures more optimal usage of these resources.

    **Configuration**:

    .. list-table::
        :widths: 25 100 10
        :header-rows: 1

        * - Parameter
          - Description
          - Type
        * - lock_file
          - Path to the file acting as the lock. Default: "./mutex.lck"
          - str
    """

    def __init__(self, config):
        Module.__init__(self, config)
        self._lock_file = Utility.resolve_path(config.get_string('lock_file', './mutex.lck'))

    def run(self):
        print("locking file " + self._lock_file)
        with FileLock(self._lock_file):
            module_list = self.config.get_list("modules")
            modules = Utility.initialize_modules(module_list)
            for module in modules:
                with Utility.BlockStopWatch("Running module " + module.__class__.__name__):
                    module.run()

