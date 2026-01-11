import subprocess
import time

BOARD_FILES = 'abcdefghi'
BOARD_RANKS = '123456789'
PIECE_TYPS_LOWER = 'rnbkqpoacmxswj'
PIECE_TYPS_LOWER_PROMOTED_ONLY = 'jqnbr'

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
    def __init__(self,
                 engine_path="fairy-stockfish-largeboards_x86-64-bmi2-latest.exe"):  # 沿用BingGo beta 1.2使用的引擎，否则Pawn出现意外错误
        """
        初始化引擎
        engine_path: 引擎可执行文件路径
        """
        print("=== BINGGO VARIANT ENGINE ===")
        print(f"Starting engine: {engine_path}")

        self.proc = subprocess.Popen(
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

        """
        uci
        setoption name VariantPath value binggo.ini
        setoption name UCI_Variant value binggo
        ucinewgame
        startpos
        """

        # 等待引擎初始化完成
        self._wait_for_ready()
        print("Engine initialized and ready!")

    def _wait_for_ready(self):
        """等待引擎准备就绪"""
        self._send_command("isready")
        while True:
            line = self._readline()
            if "readyok" in line:
                break

    def _readline(self) -> str:
        """
        读取引擎输出的一行
        """
        if self.proc.stdout:
            return self.proc.stdout.readline()
        else:
            raise AttributeError("Engine stdin is not available")

    def _read_until(self, until: str, ignore=None, del_blank_lines=True) -> str:
        """
        读取引擎输出直到遇到目标字符串
        :param until: 目标字符串
        :param ignore_lines: 忽略的行
        """
        if ignore is None:
            ignore = []
        for s in ignore:
            assert isinstance(s, str), "ignore_lines must be a list of strings"

        output = ""
        for _ in range(800):
            line = self._readline()
            if del_blank_lines and line.strip() == "":
                continue
            if not any((word in line) for word in ignore):
                output += line
            if until in line:
                return output
        raise RuntimeError(f"Too many lines to read without finding '{until}'")

    def _send_command(self, cmd: str) -> None:
        """发送命令到引擎"""
        if not self.proc.stdin:
            print("Warning: Engine stdin not available")
            return
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()
        time.sleep(0.002)

    @staticmethod
    def _extract_fen_from_board(board_output):
        """从棋盘显示中提取FEN字符串"""
        for line in board_output.split('\n'):
            if line.startswith("Fen:"):  # 查找包含"Fen:"的行
                return line[4:].strip()
        return None

    def _d(self) -> None:
        """输出并显示当前棋盘状态"""
        self._send_command("d")
        board_output = self._read_until("Chased", ignore=("Sfen", "Checkers", "Key", "Chased"))
        print(board_output)

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
                else:
                    raise ValueError(f"Warning: Invalid PGN move: {m}")
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
        output = self._read_until("Chased")
        new_fen = self._extract_fen_from_board(output)

        if new_fen:
            return new_fen
        else:
            print(f"Error: Could not extract FEN after move {moves}")
            return fen

    def pms(self, fen: str) -> list[str]:
        """
        获取给定FEN下的所有合法走法列表
        @param fen: 起始局面的FEN字符串
        @return: 所有合法走法的字符串列表
        """
        self._send_command(f"position fen {fen}")
        self._send_command("go perft 1")
        output = self._read_until("Nodes searched")

        moves = []
        for line in output.split('\n'):
            # 解析走法行（格式如："e2e4: 1"）
            if ":" in line and "Nodes searched" not in line:
                move = line[:line.find(":")].strip()
                if is_pgn(move):
                    moves.append(move)
                else:
                    print(f"Warning: Invalid PGN move: {move}")
        return moves

    def best_move(self, fen: str, think_time=2000) -> tuple[str | None, str | None]:
        """
        从给定的FEN位置获取最佳走法
        @param fen: 起始局面的FEN字符串
        @param think_time: 思考时间(毫秒)
        @return: (best_move, new_fen): 最佳走法和执行走法后的新FEN

        出错则为None，请及时校验。
        """
        # 获取最佳走法
        self._send_command(f"position fen {fen}")
        self._send_command(f"go movetime {think_time}")
        output = self._read_until("bestmove").strip()
        parts = output.split('\n')[-1].strip().split()
        if len(parts) > 1 and is_pgn(parts[1]):
            best_move = parts[1]
        else:
            print(f"Warning: No best move found for FEN {fen}")
            return None, None

        # 应用走法并获取新FEN
        self._send_command(f"position fen {fen} moves {best_move}")
        self._send_command("d")
        output = self._read_until("Chased")
        new_fen = self._extract_fen_from_board(output)

        return best_move, new_fen

    def analyze(self):
        raise NotImplementedError("The analyze method is currently disabled.")

    def close(self) -> None:
        """关闭引擎"""
        self._send_command("quit")
        time.sleep(0.2)
        self.proc.terminate()
        self.proc.wait()
        print("Engine closed.")


if __name__ == "__main__":
    eng = BinggoEngine()
    ...
