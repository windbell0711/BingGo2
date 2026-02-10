import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from src.engine import fen_is_invalid, is_betza

class ChessPieceSetup:
    blank_default = {
        'startFen': 'rnbk1qnbr/pppp1pppp/9/9/9/O1O1O1O1O/1A5A1/9/CMXSWSXMC w kq - 0 1',
        'customPiece1': 'j:NB2RmpRcpR', 
        'customPiece2': 'x:B2', 
        'customPiece3': 'o:fsW',
        'customPiece4': 's:K', 
        'customPiece5': 'a:mRpR', 
        'customPiece6': 'c:R',
        'customPiece7': 'w:W', 
        'customPiece8': 'm:nN', 
        'customPiece9': 'k:K',
        'customPiece10': 'q:RB', 
        'customPiece11': 'r:R', 
        'customPiece12': 'b:B',
        'customPiece13': 'n:N', 
        'customPiece14': 'p:mfWcfFimfR2',
    }
    @staticmethod
    def format_redeclares(redeclares: dict[str, str]) -> str:
        """将重声明字典格式化为字符串"""
        if not redeclares:
            return "; Nothing changed"
        return "\n".join(f"{k}={v}" for k, v in redeclares.items())
    
    def __init__(self, root, redeclares: dict[str, str]):
        self.root = root
        self.root.title("棋子走法设置器")
        self.root.geometry("750x650")
        self.running = True
        self.confirm: bool | None = None
        
        # 记录初始状态用于恢复
        self.original_redeclares = redeclares or {}
        
        # 根据redeclares初始化初始状态
        self.initial_redeclares = redeclares or {}
        
        # 创建滚动框架
        canvas = tk.Canvas(root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 内容框架
        content_frame = ttk.Frame(self.scrollable_frame, padding=10)
        content_frame.grid(sticky='wens')
        self.scrollable_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        
        # 说明与链接
        ttk.Label(content_frame, text="说明：勾选\"更改\"后修改值，预览区实时显示生效配置", wraplength=800).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0,10))
        
        # 快捷功能按钮组
        quick_frame = ttk.LabelFrame(content_frame, text="快捷功能", padding=8)
        quick_frame.grid(row=1, column=0, columnspan=3, sticky='we', pady=(0,10))
        
        # 快捷按钮
        ttk.Button(quick_frame, text="切换先手", command=self.toggle_side).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="恢复初始", command=self.reset_to_original).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="查看文档", command=lambda: webbrowser.open("https://www.gnu.org/software/xboard/Betza.html")).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_frame, text="查看教程", command=lambda: webbrowser.open("https://www.gnu.org/software/xboard/Betza.html")).pack(side=tk.LEFT, padx=5)
        
        # 主体内容（左右分栏）
        main_frame = ttk.Frame(content_frame)
        main_frame.grid(row=2, column=0, columnspan=3, sticky='we', pady=(0,10))
        
        # 左侧表格
        table_frame = ttk.Frame(main_frame)
        table_frame.grid(row=0, column=0, sticky=tk.NW, padx=(0,20))
        
        # 表头
        for col, txt in enumerate(["项目", "值", "更改"]):
            ttk.Label(table_frame, text=txt, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=col, sticky=tk.W, padx=(0,10), pady=(0,5))
        
        # 控件存储
        self.entries = {}  # key: (var, entry_widget, default_value)
        self.check_vars = {}
        
        # 创建行
        for i, (key, default) in enumerate(self.blank_default.items()):
            ttk.Label(table_frame, text=key).grid(row=i+1, column=0, sticky=tk.W, padx=(0,10), pady=2)
            
            # 根据初始重声明设置值
            initial_value = self.initial_redeclares.get(key, default)
            var = tk.StringVar(value=initial_value)
            entry = ttk.Entry(table_frame, textvariable=var, width=30, state="disabled")
            entry.grid(row=i+1, column=1, sticky=tk.W, padx=(0,10), pady=2)
            self.entries[key] = (var, entry, default)
            
            # 根据初始重声明设置复选框状态
            initial_checked = key in self.initial_redeclares
            check_var = tk.BooleanVar(value=initial_checked)
            check = ttk.Checkbutton(table_frame, variable=check_var, command=lambda k=key: self.toggle_entry(k))
            check.grid(row=i+1, column=2, sticky=tk.W, pady=2)
            self.check_vars[key] = check_var
            
            # 根据初始状态设置输入框启用状态
            if initial_checked:
                entry.config(state="normal")
        
        # 右侧预览
        preview_frame = ttk.LabelFrame(main_frame, text="规则预览 (每秒自动更新)", padding=10)
        preview_frame.grid(row=0, column=1, sticky='nse')
        self.preview = tk.Text(preview_frame, height=20, width=40, state="disabled", wrap=tk.WORD, bg="#f0f0f0")
        self.preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        psb = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview.yview)
        psb.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview.configure(yscrollcommand=psb.set)
        
        # 按钮
        btn_frame = ttk.Frame(content_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="取消", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="确定", command=self.on_confirm).pack(side=tk.LEFT, padx=5)
        
        # 布局
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_cancel)
        
        # 启动预览更新循环（每秒）
        self.update_preview_and_reschedule()
    
    def toggle_side(self):
        """切换先手"""
        # 获取当前值
        current_fen = self.entries['startFen'][0].get()
        
        # 切换先手
        if " w " in current_fen:
            new_fen = current_fen.replace(" w ", " b ")
        elif " b " in current_fen:
            new_fen = current_fen.replace(" b ", " w ")
        else:
            messagebox.showwarning("警告", "FEN串中未找到先手信息(w/b)，无法切换")
            return
        
        # 确保startFen被标记为更改
        if not self.check_vars['startFen'].get():
            self.check_vars['startFen'].set(True)
            self.entries['startFen'][1].config(state="normal")
        
        # 更新值
        self.entries['startFen'][0].set(new_fen)
    
    def reset_to_original(self):
        """恢复到初始状态"""
        for key, (var, entry, default) in self.entries.items():
            if key in self.original_redeclares:
                var.set(self.original_redeclares[key])
                self.check_vars[key].set(True)
                entry.config(state="normal")
            else:
                var.set(default)
                self.check_vars[key].set(False)
                entry.config(state="disabled")
        self.update_preview()
    
    def toggle_entry(self, key):
        """切换输入框状态并处理默认值"""
        var, entry, default = self.entries[key]
        if self.check_vars[key].get():
            entry.config(state="normal")
        else:
            var.set(default)  # 恢复默认值
            entry.config(state="disabled")
        self.update_preview()  # 立即更新预览
    
    def update_preview(self):
        if not self.running:
            return
            
        self.preview.config(state="normal")
        self.preview.delete("1.0", tk.END)
        
        lines = []
        for key, (var, _, _) in self.entries.items():
            if self.check_vars[key].get():
                lines.append(f"{key}={var.get()}")
        
        self.preview.insert("1.0", "\n".join(lines) if lines else "; Nothing changed")
        self.preview.config(state="disabled")

    def update_preview_and_reschedule(self):
        self.update_preview()
        if self.running:
            self.root.after(1000, self.update_preview_and_reschedule)
    
    def on_cancel(self):
        self.confirm = False
        self.running = False
        self.root.quit()
    
    def on_confirm(self):
        result = {k: v.get() for k, (v, _, _) in self.entries.items() if self.check_vars[k].get()}
        if 'startFen' in result and fen_is_invalid(result['startFen']):
            messagebox.showerror("错误", f"FEN串格式错误\n{fen_is_invalid(result['startFen'])}")
            return
        for key, value in result.items():
            if key == 'startFen':
                if fen_is_invalid(result['startFen']):
                    messagebox.showerror("错误", f"FEN串{value}格式错误\n{fen_is_invalid(result['startFen'])}")
                    return
            else:
                if not is_betza(value):
                    messagebox.showerror("错误", f"{key} {value}\n不符合Betza格式")
                    return
        self.confirm = True
        print("棋子配置信息:")
        print(f"更改的数据: {result}")
        self.running = False
        self.root.quit()


if __name__ == "__main__":
    # 示例重声明
    sample_redeclares = {
        'customPiece2': 'x:B5',
        'customPiece10': 'q:WDHFNCAZG'
    }
    
    root = tk.Tk()
    app = ChessPieceSetup(root, sample_redeclares)
    root.mainloop()

    # 集成测试：验证功能完整性
    if app.confirm:
        print("=== 集成测试结果 ===")
        print("用户确认更改")
        result = {k: v.get() for k, (v, _, _) in app.entries.items() if app.check_vars[k].get()}
        print(f"更改的配置: {result}")
        print("格式化预览:")
        print(ChessPieceSetup.format_redeclares(result))
    else:
        print("用户取消操作")
