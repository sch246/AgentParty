import os, time
import threading
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class NonBlockingWatcher(FileSystemEventHandler):
    def __init__(self):
        self._locks = {}
        self._handler = None
        # 线程池：让不同文件的 handler 可以同时跑，不被 watchdog 单线程卡住，限制最多同时8个线程
        self._executor = ThreadPoolExecutor(max_workers=8)
        # 保护 _locks 字典的并发写入
        self._dict_lock = threading.Lock()

    def set_handler(self, callback):
        """设置通用处理器：对所有 .md 文件使用同一个 handler。"""
        self._handler = callback

    def on_modified(self, event):
        # 忽略文件夹本身的变动
        if event.is_directory:
            return

        path = os.path.abspath(event.src_path)

        # 必须是字符串
        if not isinstance(path, str):
            return
        # 只处理 .md 文件
        if not path.endswith('.md'):
            return

        # 动态初始化锁：新文件或子文件夹里的文件自动配一把锁
        with self._dict_lock:
            if path not in self._locks:
                self._locks[path] = threading.Lock()

        # 尝试获取锁，绝不等待 (blocking=False)
        # 获取成功 → 进入临界区；失败 → 说明有任务正在运行，立即返回
        if self._locks[path].acquire(blocking=False):
            self._executor.submit(self._run_handler, path)

    def _run_handler(self, path):
        """在线程池中真正执行 handler，执行完释放锁。"""
        try:
            if self._handler:
                self._handler(path)
        finally:
            self._locks[path].release()

    def loop(self):
        observer = Observer()
        observer.schedule(self, path='.', recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

