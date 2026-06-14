import os, time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class NonBlockingWatcher(FileSystemEventHandler):
    def __init__(self):
        # 每个文件维护一把独立的锁
        self._locks = {}
        self._handlers = {}

    def register(self, file_path, callback):
        abs_path = os.path.abspath(file_path)
        self._handlers[abs_path] = callback
        self._locks[abs_path] = threading.Lock()

    def on_modified(self, event):
        path = os.path.abspath(event.src_path)
        if path not in self._locks:
            return

        # 核心逻辑：尝试获取锁，但绝不等待 (blocking=False)
        # 如果获取成功，则进入临界区；如果失败，说明有任务正在运行，立即返回
        if self._locks[path].acquire(blocking=False):
            try:
                self._handlers[path](path)
            finally:
                # 无论任务成功与否，必须释放锁，以便下次触发可以继续执行
                self._locks[path].release()

watcher = NonBlockingWatcher()

def loop():
    observer = Observer()
    observer.schedule(watcher, path='.', recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

