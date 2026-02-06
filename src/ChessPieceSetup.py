"""
棋子走法设置器 - 简化版本
https://www.qianwen.com/chat/f2da8f4fe71048aa87cdf72b57f7c254
"""
import tkinter as tk
from tkinter import ttk
import webbrowser

class ChessPieceSetup:
    def __init__(self, root):
        self.root = root
        self.root.title("棋子走法设置器")
        self.root.geometry("900x650")
        
        # 创建滚动框架
        self.setup_ui()
        self.load_default_config()
        
    def setup_ui(self):
        """设置用户界面"""
        # 主滚动框架
        canvas = tk.Canvas(self.root, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind("<Configure>", 
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # 默认配置
        self.default_pieces = [
            ["棋子1", "A", "fmWfceF"], ["棋子2", "B", "mQcQ"], ["棋子3", "C", "mRcR"],
            ["棋子4", "D", "mBcB"], ["棋子5", "E", "nightrider"], ["棋子6", "F", "ferz"],
            ["棋子7", "G", "wazir"], ["棋子8", "K", "king"], ["棋子9", "Q", "queen"],
            ["棋子10", "R", "rook"], ["棋子11", "B", "bishop"], ["棋子12", "N", "knight"],
            ["棋子13", "P", "pawn"], ["棋子14", "S", "silver"]
        ]
        self.initial_fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        
        # 创建内容框架
        content_frame = ttk.Frame(self.scrollable_frame, padding=10)
        content_frame.grid(row=0, column=0, sticky="nsew")
        self.scrollable_frame.columnconfigure(0, weight=1)
        
        # 说明文本
        ttk.Label(content_frame, text="说明：设置棋子字符和Betza走法，点击按钮插入到FEN中", 
                 wraplength=800).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))
        
        # Betza链接
        link_frame = ttk.Frame(content_frame)
        link_frame.grid(row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))
        ttk.Label(link_frame, text="Betza记号法参考：").pack(side="left")
        link = ttk.Label(link_frame, text="https://www.gnu.org/software/xboard/Betza.html", 
                        foreground="blue", cursor="hand2")
        link.pack(side="left")
        link.bind("<Button-1>", lambda e: webbrowser.open("https://www.gnu.org/software/xboard/Betza.html"))
        
        # 表格
        self.create_table(content_frame)
        
        # FEN设置
        ttk.Label(content_frame, text="初始FEN设置:", font=("TkDefaultFont", 9, "bold")).grid(
            row=3, column=0, columnspan=3, sticky="w", pady=(20, 0))
        
        self.fen_text = tk.Text(content_frame, height=9, width=70)
        self.fen_text.grid(row=4, column=0, columnspan=3, pady=(0, 10), sticky="we")
        
        scrollbar_fen = ttk.Scrollbar(content_frame, orient="vertical", command=self.fen_text.yview)
        scrollbar_fen.grid(row=4, column=3, sticky="ns")
        self.fen_text.configure(yscrollcommand=scrollbar_fen.set)
        
        # 按钮
        btn_frame = ttk.Frame(content_frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=10)
        ttk.Button(btn_frame, text="取消", command=self.root.quit).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="确定", command=self.output_data).pack(side="left", padx=5)
        
        # 布局
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
    def create_table(self, parent):
        """创建棋子设置表格"""
        table_frame = ttk.Frame(parent)
        table_frame.grid(row=2, column=0, columnspan=4, sticky="we", pady=(0, 10))
        
        # 表头
        headers = ["棋子名称", "字符表示", "Betza走法", "操作"]
        for i, header in enumerate(headers):
            ttk.Label(table_frame, text=header, font=("TkDefaultFont", 9, "bold")).grid(
                row=0, column=i, sticky="w", padx=(0, 10), pady=(0, 5))
        
        # 表格行
        self.entries = {}  # 存储所有输入框
        for i, (name, char, betza) in enumerate(self.default_pieces):
            # 名称标签
            ttk.Label(table_frame, text=name).grid(row=i+1, column=0, sticky="w", padx=(0, 10), pady=2)
            
            # 字符输入框
            char_entry = ttk.Entry(table_frame, width=5)
            char_entry.grid(row=i+1, column=1, sticky="w", padx=(0, 10), pady=2)
            char_entry.insert(0, char)
            
            # Betza输入框
            betza_entry = ttk.Entry(table_frame, width=20)
            betza_entry.grid(row=i+1, column=2, sticky="w", padx=(0, 10), pady=2)
            betza_entry.insert(0, betza)
            
            # 插入按钮
            ttk.Button(table_frame, text="插入FEN", width=10,
                      command=lambda n=name, c=char_entry: self.fen_text.insert("insert", (c.get() or n[0]))).grid(row=i+1, column=3, sticky="w", pady=2)
            
            self.entries[name] = (char_entry, betza_entry)
        
    def load_default_config(self):
        """加载默认配置"""
        self.fen_text.delete("1.0", "end")
        self.fen_text.insert("1.0", self.initial_fen)
                
    def output_data(self):
        """输出配置数据"""
        # 收集数据
        pieces_data = []
        for name, (char_entry, betza_entry) in self.entries.items():
            pieces_data.append([
                name, 
                char_entry.get().strip(), 
                betza_entry.get().strip()
            ])
        
        fen_data = self.fen_text.get("1.0", "end").strip()
        
        # 输出结果
        print("棋子配置信息:")
        print(f"棋子详细信息: {pieces_data}")
        print(f"初始FEN: {repr(fen_data)}")
        print("-" * 50)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessPieceSetup(root)
    root.mainloop()
