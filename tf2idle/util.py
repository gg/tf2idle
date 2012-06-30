import ctypes
import os
import re
import time


def wait_until(predicate, timeout, poll_interval=1, exception=None):
    mustend = time.time() + timeout
    while time.time() < mustend:
        if predicate():
            return True
        time.sleep(poll_interval)
    if exception is not None:
        raise exception
    return False


class WindowSnapshot(object):
    def __init__(self, window):
        self.hwnd = window.hwnd
        self.title = window.title
        self.pid = window.pid

    def __repr__(self):
        return 'WindowSnapshot(hwnd={0:#x}, title="{1}", pid={2})'.format(
            self.hwnd, self.title, self.pid)


class Window(object):
    def __init__(self, hwnd):
        self.hwnd = hwnd

    @property
    def title(self):
        return GetWindowText(self.hwnd)

    @property
    def pid(self):
        return GetWindowThreadProcessId(self.hwnd)

    def activate(self):
        return bool(SetActiveWindow(self.hwnd))

    def close(self):
        return bool(DestroyWindow(self.hwnd))

    def exists(self):
        return bool(IsWindow(self.hwnd))

    def __repr__(self):
        return 'Window<{hwnd:#x}>'.format(hwnd=self.hwnd)


def top_level_windows():
    """Returns an iterator of all top-level window handles."""
    toplevel_windows = []

    def callback(hwnd, lparam):
        toplevel_windows.append(Window(hwnd))
        return True

    EnumWindowProc = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_long,
                                        ctypes.c_long)
    proc = EnumWindowProc(callback)

    ctypes.windll.user32.EnumWindows(proc, 0)

    return iter(toplevel_windows)


def get_process_windows(pid):
    """Returns a generator of WindowSnapshot instances."""
    for window in top_level_windows():
        if window.pid == pid:
            yield window


def IsWindow(hwnd):
    return ctypes.windll.user32.IsWindow(hwnd)


def GetWindowThreadProcessId(hwnd):
    pid = ctypes.c_ulong()
    try:
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd,
                                                      ctypes.pointer(pid))
    except WindowsError:
        pid = 0
    return pid.value


def GetWindowText(hwnd):
    max_count = GetWindowTextLength(hwnd) + 1  # For the null character.
    buf = ctypes.create_unicode_buffer(max_count)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, max_count)
    return ctypes.wstring_at(buf)


def GetWindowTextLength(hwnd):
    return ctypes.windll.user32.GetWindowTextLengthW(hwnd)


def DestroyWindow(hwnd):
    return ctypes.windll.user32.DestroyWindow(hwnd)


def SetActiveWindow(hwnd):
    return ctypes.windll.user32.SetActiveWindow(hwnd)


def grep(regex_pattern, fileobj):
    """Returns a generator of (line_number, line) tuples that match
    `regex_pattern`."""
    for line_number, line in enumerate(fileobj):
        if re.search(regex_pattern, line):
            yield (line_number, line)


def tail(fileobj, start=os.SEEK_END, poll_interval=1):
    """Returns a generator of lines from `fileobj`, similar to
    Unix's tail -f."""
    fileobj.seek(0, start)
    while True:
        for line in iter(fileobj.readline, ''):
            yield line[:-1]  # remove '\n' character
        time.sleep(poll_interval)
