import subprocess
import time

BOARD_FILES = 'abcdefghi'
BOARD_RANKS = '123456789'
PIECE_TYPS_LOWER = 'rnbkqpoacmxswj'
PIECE_TYPS_LOWER_PROMOTED_ONLY = 'j'

def is_pgn(move: str) -> bool:
    """检查走法格式是否符合pgn格式"""
    if len(move) == 5:
        if move[4] not in PIECE_TYPS_LOWER_PROMOTED_ONLY:
            return False
    elif len(move) != 4:
        return False
    return (move[0] in BOARD_FILES and move[2] in BOARD_FILES and
            move[1] in BOARD_RANKS and move[3] in BOARD_RANKS)


class BinggoEngine:
    def __init__(self, engine_path="fairy-stockfish-largeboard_x86-64-bmi2.exe"):
        """
        初始化引擎
        engine_path: 引擎可执行文件路径
        """
        print("=== BINGGO VARIANT ENGINE ===")
        print(f"Starting engine: {engine_path}")
        
        self.engine = subprocess.Popen(
            [engine_path],
            universal_newlines=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            bufsize=1  # 行缓冲
        )
        
        # 初始化引擎
        INI_FILE_NAME = "binggo.ini"
        self._send_command("uci")
        self._send_command(f"setoption name VariantPath value {INI_FILE_NAME}")
        self._send_command("setoption name UCI_Variant value binggo")
        self._send_command("ucinewgame")
        self._send_command("startpos")  # 必须给我加上！！
        
        # 等待引擎初始化完成
        self._wait_for_ready()
        print("Engine initialized and ready!")

    def _readline(self) -> str:
        """
        安全读取引擎输出的一行
        """
        if self.engine.stdout:
            return self.engine.stdout.readline()
        else:
            raise AttributeError("Engine stdin is not available")

    def _send_command(self, cmd: str) -> None:
        """发送命令到引擎"""
        if not self.engine.stdin:
            print("Warning: Engine stdin not available")
            return
        self.engine.stdin.write(cmd + "\n")
        self.engine.stdin.flush()
        time.sleep(0.01)
    
    def _wait_for_ready(self):
        """等待引擎准备就绪"""
        self._send_command("isready")
        while True:
            line = self._readline()
            if "readyok" in line:
                break
    
    @staticmethod
    def _extract_fen_from_board(board_output):
        """从棋盘显示中提取FEN字符串"""
        # 查找包含"Fen:"的行
        for line in board_output.split('\n'):
            if line.startswith("Fen:"):
                return line[4:].strip()
        return None
    
    def _display_board(self) -> None:
        """输出并显示当前棋盘状态"""
        self._send_command("d")
        
        # 读取棋盘显示
        board_output = ""
        collecting = True
        while collecting:
            line = self._readline()
            if "Key" in line or "Fen:" in line or "Checkers:" in line:
                collecting = False
            else:
                board_output += line
        
        # 打印棋盘（只保留棋盘部分）
        lines = board_output.strip().split('\n')
        for line in lines:
            if line.strip():  # 跳过空行
                print(line.strip())
    
    def _d(self) -> None:
        """调试用，显示当前棋盘状态"""
        self._display_board()
    
    def perform_move(self, fen: str, move: str | list[str]) -> str:
        """
        根据给定的FEN和走法，返回新的FEN
        :param fen:  起始局面的FEN字符串
        :param move: 要执行的走法（如"e2e4"）
        :return:     执行走法后的新FEN
        """
        # 处理输入
        if isinstance(move, list):
            moves = ""
            for m in move:
                if is_pgn(m):
                    moves += m + " "
                else: raise ValueError(f"Warning: Invalid PGN move: {m}")
            moves = moves.strip()
        elif isinstance(move, str):
            if not is_pgn(move):
                raise ValueError(f"Warning: Invalid PGN move: {move}")
            moves = move
        else:
            raise TypeError("move must be str or list[str]")
        
        # 设置局面并执行走法
        self._send_command(f"position fen {fen} moves {moves}")
        self._send_command("d")
        
        # 读取棋盘显示
        board_output = ""
        start_collecting = False
        for _ in range(30):  # 读取足够的行数
            line = self._readline()
            if "Fen:" in line:
                start_collecting = True
            if start_collecting:
                board_output += line
                if "Checkers:" in line:  # 棋盘显示结束的标志
                    break
        
        # 从棋盘显示中提取新FEN
        new_fen = self._extract_fen_from_board(board_output)
        
        if new_fen:
            # 打印走法信息
            print(f"Move: {moves}")
            return new_fen
        else:
            print(f"Warning: Could not extract FEN after move {moves}")
            return fen
    
    def pms(self, fen: str) -> list[str]:
        """
        获取给定FEN下的所有合法走法列表
        
        参数:
        fen: 起始局面的FEN字符串
        
        返回:
        moves: 所有合法走法的字符串列表
        """
        self._send_command(f"position fen {fen}")
        self._send_command("go perft 1")
        
        moves = []
        while True:
            line = self._readline()
            if not line:
                continue
            # 跳过空行
            line = line.strip()
            if not line:  continue
            # 解析走法行（格式如："e2e4: 1"）
            if ":" in line and "Nodes searched:" not in line:
                move = line[:line.find(":")].strip()
                if move:  moves.append(move)
            # 结束条件
            if "Nodes searched:" in line:
                break
        
        return moves
    
    def best_move(self, fen: str, think_time=2000) -> tuple[str | None, str | None]:
        """
        从给定的FEN位置获取最佳走法
        
        参数:
        fen: 起始局面的FEN字符串
        think_time: 思考时间(毫秒)
        
        返回:
        (best_move, new_fen): 最佳走法和执行走法后的新FEN

        出错则为None，请及时校验。
        """
        self._send_command(f"position fen {fen}")
        self._send_command(f"go movetime {think_time}")
        
        best_move = None
        while True:
            line = self._readline()
            if not line:
                continue
            if "bestmove" in line:
                parts = line.strip().split()
                if len(parts) > 1 and parts[1] != "(none)":
                    best_move = parts[1]
                break
        
        if not best_move:
            print(f"Warning: No best move found for FEN {fen}")
            return None, None
        
        # 应用走法并获取新FEN
        self._send_command(f"position fen {fen} moves {best_move}")
        self._send_command("d")
        
        # 读取棋盘显示
        board_output = ""
        start_collecting = False
        for _ in range(30):  # 读取足够的行数
            line = self._readline()
            if "Fen:" in line:
                start_collecting = True
            if start_collecting:
                board_output += line
                if "Checkers:" in line:  # 棋盘显示结束的标志
                    break
        new_fen = self._extract_fen_from_board(board_output)
        
        return best_move, new_fen
    
    def analyze(self, fen: str, think_time=2000) -> dict:
        raise NotImplementedError("The analyze method is currently disabled.")
        # self._send_command(f"position fen {fen}")
        # self._send_command(f"go movetime {think_time}")
        
        # analysis = {
        #     "fen": fen,
        #     "best_move": None,
        #     "evaluation": None,
        #     "depth": None,
        #     "nodes": None,
        #     "pv": []  # 主要变例
        # }
        
        # while True:
        #     line = self._readline()
        #     if not line:
        #         continue
            
        #     # 解析思考信息
        #     if "info" in line and "depth" in line:
        #         parts = line.split()
        #         for i, part in enumerate(parts):
        #             if part == "depth" and i + 1 < len(parts):
        #                 analysis["depth"] = parts[i + 1]
        #             elif part == "nodes" and i + 1 < len(parts):
        #                 analysis["nodes"] = parts[i + 1]
        #             elif part == "score" and i + 1 < len(parts):
        #                 analysis["evaluation"] = parts[i + 2] if i + 2 < len(parts) else parts[i + 1]
        #             elif part == "pv" and i + 1 < len(parts):
        #                 analysis["pv"] = parts[i + 1:]
            
        #     # 解析最佳走法
        #     if "bestmove" in line:
        #         parts = line.strip().split()
        #         if len(parts) > 1 and parts[1] != "(none)":
        #             analysis["best_move"] = parts[1]
        #         break
        
        # # 获取执行走法后的新FEN
        # if analysis["best_move"]:
        #     best_move, new_fen = self.best_move(fen, think_time)
        #     analysis["new_fen"] = new_fen
        
        # return analysis
    
    def close(self) -> None:
        """关闭引擎"""
        self._send_command("quit")
        self.engine.terminate()
        self.engine.wait()
        print("Engine closed.")


if __name__ == "__main__":
    # 初始化引擎
    eng = BinggoEngine()
    
    ori_fen = "rnbk1qnbr/pppp1pppp/9/9/9/OOO1O1OOO/1A5A1/9/CMXSWSXMC w kq - 0 1"
    # my_fen = "r2k4r/pppp1pppp/9/9/9/OOO1O1OOO/1A5A1/9/CMXSWSXMC b kq - 0 1"
    
    # best_move, new_fen = eng.best_move(my_fen, think_time=2000)
    # print(f"{best_move=}")
    # print(f"{new_fen=}")

    # for i in eng.pms(my_fen):
    #     if "d9" in i:
    #         print(i)

    # # Perform Move a1a2
    # print(eng.perform_move(my_fen, "d9b9"))
    # print(eng._display_board())

    print(eng.perform_move(ori_fen, "e4e5"))
    print(eng._d())
    print(eng.perform_move(ori_fen, ["e4e5", "d9e9", "a1a2"]))
    print(eng._d())

    eng.close()
