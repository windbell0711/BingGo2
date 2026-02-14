import logging
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Callable, Any, Optional

root = tk.Tk()
root.withdraw()  # 隐藏主窗口

def noop(*args, **kwargs):
    pass

class MsgLog:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def topmost_msgbox(self, func_msg: Callable, func_log: Callable,
                       title: str, msg: str) -> Any:
        temp = tk.Toplevel(root)  # 创建一个临时窗口作为容器
        temp.withdraw()
        temp.attributes('-topmost', True)
        def make_topmost(event):
            if isinstance(event.widget, tk.Toplevel) and event.widget != temp:
                event.widget.attributes('-topmost', True)
        temp.bind_class('Toplevel', '<Map>', make_topmost)

        func_log(msg)
        ret = func_msg(title, msg, parent=temp)
        temp.destroy()  # 弹窗关闭后销毁临时窗口
        return ret
    
    def debug(self, msg: str, title="调试", box=True, log=True) -> None:
        self.topmost_msgbox(messagebox.showinfo if box else noop,
                            self.logger.debug if log else noop, title, msg)

    def info(self, msg: str, title="信息", box=True, log=True) -> None:
        self.topmost_msgbox(messagebox.showinfo if box else noop,
                            self.logger.info if log else noop, title, msg)
    
    def warning(self, msg: str, title="警告", box=True, log=True) -> None:
        self.topmost_msgbox(messagebox.showwarning if box else noop,
                            self.logger.warning if log else noop, title, msg)
    
    def error(self, msg: str, title="错误", box=True, log=True) -> None:
        self.topmost_msgbox(messagebox.showerror if box else noop,
                            self.logger.error if log else noop, title, msg)
    
    def critical(self, msg: str, title="严重错误", box=True, log=True) -> None:
        self.topmost_msgbox(messagebox.showerror if box else noop,
                            self.logger.critical if log else noop, title, msg)

    def askyesno(self, msg: str, title="") -> bool:
        return self.topmost_msgbox(messagebox.askyesno, noop, title, msg)

    def askyesnocancel(self, msg: str, title="") -> Optional[bool]:
        return self.topmost_msgbox(messagebox.askyesnocancel, noop, title, msg)

    def askokcancel(self, msg: str, title="") -> bool:
        return self.topmost_msgbox(messagebox.askokcancel, noop, title, msg)

    def askretrycancel(self, msg: str, title="") -> bool:
        return self.topmost_msgbox(messagebox.askretrycancel, noop, title, msg)

    def askstring(self, msg: str, title="输入") -> Optional[str]:
        return self.topmost_msgbox(simpledialog.askstring, noop, title, msg)
