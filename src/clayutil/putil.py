import contextlib
import ctypes
import inspect
import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable, Generator
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Optional, TypeAlias

import orjson

WorkerReturn: TypeAlias = tuple[int, int, bool]


__all__ = ("BatchProcessor", "LifetimeError", "LifetimeScope")


@dataclass
class TaskMeta(object):
    """任务函数元信息"""

    func: Callable[..., int]
    max_retries: int
    retry_wait: float
    success_codes: frozenset[int] = field(default_factory=lambda: frozenset([0]))
    source_gen: Optional[Callable] = None
    func_name: str = ""

    def __post_init__(self):
        self.func_name = self.func.__name__


class BatchProcessor(object):
    """批量处理工具类

    Parameters
    ---
    checkpoint_path
        断点记录文件路径（JSON）。
    log_name
        logger 名称。
    log_level
        日志级别，默认 logging.INFO。
    success_codes
        全局默认成功状态码列表，默认 [0]。可在 task 装饰器中覆盖。
    """

    def __init__(
        self,
        checkpoint_path: str = "./batch_checkpoint.json",
        log_name: str = "BatchProcessor",
        log_level: int = logging.INFO,
        success_codes: Optional[frozenset[int]] = None,
    ):
        self.checkpoint_path = checkpoint_path
        self._default_success_codes = success_codes if success_codes is not None else frozenset([0])

        # --- 日志 ---
        self.logger = logging.getLogger(log_name)
        self.logger.setLevel(log_level)
        # 防止重复添加 handler
        if not self.logger.handlers:
            _sh = logging.StreamHandler()
            _sh.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s"))
            self.logger.addHandler(_sh)
            _fh = logging.FileHandler(checkpoint_path + ".log")
            _fh.setFormatter(logging.Formatter("[%(asctime)s] [%(name)s/%(levelname)s]: %(message)s"))
            self.logger.addHandler(_fh)

        # --- 任务注册表 ---
        self._tasks: dict[str, TaskMeta] = {}

        # --- 断点文件锁 ---
        # 注：原本有并行设计，但是考虑到并行应该使用 all-or-nothing 的错误处理模型，因此放弃了这一块的内容。但是锁的设计被遗留下来，不影响结果。
        self._ckpt_lck = threading.Lock()
        self._checkpoint_data: dict[str, dict] = {}  # {task_name: {param_key: status_dict}}
        self._load_checkpoint()

    def task(
        self,
        max_retries: int = 3,
        retry_wait: float = 1.5,
        success_codes: Optional[frozenset[int]] = None,
    ):
        """
        将一个函数注册为批量任务

        Parameters
        ---
        max_retries
            单个任务最大重试次数，不含首次执行。
        retry_wait
            重试前等待秒数。
        success_codes
            成功状态码，为 None 时使用全局默认 [0]。
        """

        def decorator(func: Callable[..., int]) -> Callable[..., int]:
            sc = success_codes if success_codes is not None else self._default_success_codes
            meta = TaskMeta(
                func=func,
                max_retries=max_retries,
                retry_wait=retry_wait,
                success_codes=sc,
            )
            self._tasks[meta.func_name] = meta
            return func

        return decorator

    def source(self, task_func: Callable[..., int]):
        """
        将一个 generator 工厂注册为指定任务的参数来源

        ```
        @bp.source(my_task_func)
        def my_gen():
            yield ...
        ```
        """

        def decorator(gen_func: Callable[..., Generator[dict[str, Any]]]) -> Callable[..., Generator[dict[str, Any]]]:
            task_name = getattr(task_func, "__name__", str(task_func))
            if task_name not in self._tasks:
                raise ValueError(f"任务 '{task_name}' 尚未注册")
            self._tasks[task_name].source_gen = gen_func
            self.logger.debug(f"已为任务 '{task_name}' 绑定参数生成器 '{gen_func.__name__}'")
            return gen_func

        return decorator

    @staticmethod
    def _make_param_key(params: dict) -> str:
        """把参数 dict 序列化为稳定的字符串 key（为了便于查看此处不使用哈希算法）"""
        return json.dumps(params, sort_keys=True, default=str)

    def _load_checkpoint(self):
        if os.path.exists(self.checkpoint_path):
            try:
                with open(self.checkpoint_path, "rb") as fi_b:
                    self._checkpoint_data = orjson.loads(fi_b.read())
                self.logger.info(f"已加载断点文件: {self.checkpoint_path} ({sum(len(v) for v in self._checkpoint_data.values())} 条记录)")
            except (orjson.JSONDecodeError, IOError, OSError) as e:
                self.logger.warning(f"断点文件读取失败，将重新创建: {e}")
                self._checkpoint_data = {}
        else:
            self._checkpoint_data = {}

    def _save_checkpoint(self):
        """全量写入断点文件（调用方应已持有锁）"""
        tmp_path = self.checkpoint_path + ".tmp"
        with open(tmp_path, "wb") as fo_b:
            fo_b.write(orjson.dumps(self._checkpoint_data))
        os.replace(tmp_path, self.checkpoint_path)

    def _record_status(self, task_name: str, param_key: str, status_code: int, attempts: int, success: bool):
        """记录单个任务执行结果到断点文件（线程安全）"""
        with self._ckpt_lck:
            if task_name not in self._checkpoint_data:
                self._checkpoint_data[task_name] = {}
            self._checkpoint_data[task_name][param_key] = {
                "status_code": status_code,
                "attempts": attempts,
                "success": success,
                "timestamp": time.strftime(r"%Y-%m-%d %H:%M:%S"),
            }
            self._save_checkpoint()

    def _is_completed(self, task_name: str, param_key: str) -> bool:
        """检查某参数是否已成功完成（用于断点续跑跳过）"""
        with self._ckpt_lck:
            rec = self._checkpoint_data.get(task_name, {}).get(param_key)
            return rec is not None and rec.get("success", False)

    def _execute_single(self, meta: TaskMeta, params: dict) -> WorkerReturn:
        func = meta.func

        max_retries = meta.max_retries
        retry_wait = meta.retry_wait
        success_codes = meta.success_codes

        attempt = 0
        code = -1

        while attempt <= max_retries:
            attempt += 1
            try:
                code = func(**params)
                success = code in success_codes

                if success:
                    return code, attempt, True
                else:
                    self.logger.warning(f"[{meta.func_name}] 任务返回非成功状态: {code}  参数={params}  第{attempt}/{max_retries + 1}次")
            except Exception as e:
                code = -1
                self.logger.error(f"[{meta.func_name}] 任务异常  参数={params}  第{attempt}/{max_retries + 1}次  错误: {e!r}")

            if attempt <= max_retries:
                self.logger.info(f"[{meta.func_name}] 等待 {retry_wait}s 后重试...")
                time.sleep(retry_wait)

        return code, attempt, False

    def run_sequential(self, interval: float = 0.0, task_name: Optional[str] = None):
        """顺序执行"""
        for meta in self._get_runnable_tasks(task_name):
            self._run_sequential_one(meta, interval)

    def _run_sequential_one(self, meta: TaskMeta, interval: float):
        if meta.source_gen is None:
            raise ValueError(f"任务 '{meta.func_name}' 未绑定参数生成器")

        gen = meta.source_gen()

        done = 0
        skipped = 0
        total_seen = 0
        failed_list: list[tuple[dict, int]] = []

        self.logger.info(f"[{meta.func_name}] 惰性顺序模式启动，间隔 {interval}s")

        for params in gen:
            total_seen += 1
            if interval > 0:
                time.sleep(interval)

            pk = self._make_param_key(params)

            # 断点跳过已成功的
            if self._is_completed(meta.func_name, pk):
                skipped += 1
                self.logger.debug(f"[{meta.func_name}] 跳过已完成: {pk}")
                continue

            code, attempts, success = self._execute_single(meta, params)
            self._record_status(meta.func_name, pk, code, attempts, success)

            if success:
                done += 1
                self.logger.info(f"[{meta.func_name}] ✔ 成功  done={done}  skipped={skipped}")
            else:
                failed_list.append((params, code))
                self.logger.error(f"[{meta.func_name}] ✗ 彻底失败  params={params}  code={code}")

        self.logger.info(f"[{meta.func_name}] 已完成: 成功={done} 跳过={skipped} 失败={len(failed_list)} 总计={total_seen}")

    def _get_runnable_tasks(self, task_name: Optional[str] = None) -> list[TaskMeta]:
        """获取可执行的任务列表。"""
        if task_name:
            if task_name not in self._tasks:
                raise ValueError(f"任务 '{task_name}' 未注册。")
            meta = self._tasks[task_name]
            if meta.source_gen is None:
                raise ValueError(f"任务 '{task_name}' 未绑定参数生成器。")
            return [meta]
        else:
            result = []
            for name, meta in self._tasks.items():
                if meta.source_gen is None:
                    self.logger.warning(f"任务 '{name}' 未绑定参数生成器，跳过。")
                    continue
                result.append(meta)
            if not result:
                raise ValueError("没有可执行的任务（未注册或未绑定参数生成器）。")
            return result

    def report(self, task_name: Optional[str] = None):
        """打印断点文件中的任务执行状态报告。"""
        with self._ckpt_lck:
            data = deepcopy(self._checkpoint_data)

        names = [task_name] if task_name else list(data.keys())
        self.logger.info("=" * 60)
        self.logger.info("批量任务执行报告")
        self.logger.info("=" * 60)

        for name in names:
            records = data.get(name, {})
            total = len(records)
            success = sum(1 for r in records.values() if r.get("success"))
            failed = total - success

            self.logger.info(f"\n任务: {name}")
            self.logger.info(f"  总记录: {total}  成功: {success}  失败: {failed}")

            # 按状态码分组统计
            code_stats: dict[int, int] = {}
            for r in records.values():
                c = r.get("status_code", -1)
                code_stats[c] = code_stats.get(c, 0) + 1

            for code, cnt in sorted(code_stats.items()):
                self.logger.info(f"    状态码 {code}: {cnt} 次")

            # 列出失败的详细记录
            if failed > 0:
                self.logger.info("  失败记录:")
                for pk, r in records.items():
                    if not r.get("success"):
                        self.logger.info(f"    参数={pk}  状态={r.get('status_code')}  尝试={r.get('attempts')}  时间={r.get('timestamp')}")

        self.logger.info("=" * 60)

    def clear_checkpoint(self, task_name: Optional[str] = None):
        """清除断点记录。task_name 为 None 时清除全部"""
        with self._ckpt_lck:
            if task_name:
                self._checkpoint_data.pop(task_name, None)
            else:
                self._checkpoint_data = {}
            self._save_checkpoint()
        self.logger.info(f"已清除断点记录 ({task_name=})")


class LifetimeError(NameError):
    pass


class BuriedVariable(object):
    def __init__(self, name):
        object.__setattr__(self, "name", name)

    def __getattribute__(self, item):
        raise LifetimeError(f"cannot access dead variable {(object.__getattribute__(self, 'name'))!r}")

    def __repr__(self):
        raise LifetimeError(f"cannot access dead variable {self.name!r}")

    def __setattr__(self, key, value):
        raise LifetimeError(f"cannot access dead variable {self.name!r}")

    __str__ = __repr__


class LifetimeScope(object):
    """简易变量生命周期"""

    def __init__(self, *args, label="", print_result=False):
        """简易变量生命周期

        :param args: 预定义生命周期变量名
        :param label: 生命周期标签名
        :param print_result: 是否打印销毁结果
        """
        self.label = label
        self.print_result = print_result
        self._unbind = set(args)
        self._caller_frame = None

    def track(self, name, value=None):
        if name in self._unbind:
            raise ValueError(f"variable name {name!r} already tracked")
        self._unbind.add(name)
        return value

    def __enter__(self):
        self._caller_frame = sys._getframe(1)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        caller_frame = self._caller_frame
        current_locals = caller_frame.f_locals

        buried = []
        for var in self._unbind:
            if var in current_locals:
                # del current_locals[var]
                current_locals[var] = BuriedVariable(var)
                buried.append(var)

        with contextlib.suppress(Exception):
            ctypes.pythonapi.PyFrame_LocalsToFast(ctypes.py_object(caller_frame), ctypes.c_int(1))

        if self.print_result:
            label_str = f"({self.label})" if self.label else ""
            print(f"  [scope{label_str}]: unbound {', '.join(buried)}")

        return False
