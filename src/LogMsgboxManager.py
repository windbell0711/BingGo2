import logging
import tkinter as tk
from tkinter import messagebox, simpledialog
from typing import Callable, Any, Optional

def noop(*args, **kwargs):
    pass

class MsgLog:
    def __init__(self, logger: logging.Logger, master: tk.Tk):
        self.logger = logger
        # 动态获取或创建主窗口
        self.master = master
        self.master.withdraw()  # 确保主窗口隐藏
        
    def topmost_msgbox(self, func_msg: Callable, func_log: Callable,
                       title: str, msg: str) -> Any:
        temp = tk.Toplevel(self.master)  # 使用传入的主窗口
        temp.withdraw()
        temp.attributes('-topmost', True)
        def make_topmost(event):
            if isinstance(event.widget, tk.Toplevel) and event.widget != temp:
                event.widget.attributes('-topmost', True)
        temp.bind_class('Toplevel', '<Map>', make_topmost)

        func_log(msg)
        ret = func_msg(title, msg, parent=temp)
        temp.destroy()
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
