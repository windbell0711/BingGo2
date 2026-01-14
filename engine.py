import subprocess
import time

BOARD_FILES = 'abcdefghi'
BOARD_RANKS = '123456789'
PIECE_TYPS_LOWER = 'rnbkqpoacmxswj'
PIECE_TYPS_LOWER_PROMOTED_ONLY = 'jqnbrcaxsm'

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
                 engine_path="engine\\fairy-stockfish-largeboards_x86-64-bmi2-latest.exe",  # 沿用BingGo beta 1.2使用的引擎，否则Pawn出现意外错误
                 ini_file="engine\\binggo.ini"):
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
        self.wait_time = 0.001

        # 初始化引擎
        self.ini_file_name = ini_file

        self._send_command("uci")
        self._send_command(f"setoption name VariantPath value {self.ini_file_name}")
        self._send_command("setoption name UCI_Variant value binggo")
        self._send_command("ucinewgame")
        self._send_command("startpos")  # 必须给我加上！！

        """
        引擎调试咒语
        uci
        setoption name Debug Log File value debug.log
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
        time.sleep(self.wait_time)

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

    def best_move(self, fen: str, movetime=2000) -> tuple[str, str] | tuple[None, None]:
        """
        从给定的FEN位置获取最佳走法
        @param fen: 起始局面的FEN字符串
        @param movetime: 思考时间(毫秒)
        @return: (best_move, new_fen): 最佳走法和执行走法后的新FEN

        出错则为None，请及时校验。
        """
        # 获取最佳走法
        self._send_command(f"position fen {fen}")
        self._send_command(f"go movetime {movetime}")
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
        if new_fen:
            return best_move, new_fen
        else:
            return None, None

    def analyze(self, fen: str, movetime=2000) -> tuple[str, float, int] | tuple[None, None, None]:  # TODO
        # 获取输出
        self._send_command(f"position fen {fen}")
        self._send_command(f"go movetime {movetime}")
        output = self._read_until("bestmove").strip()
        lines = output.split('\n')
        # 解析数据
        try:
            assert lines[-1].startswith("bestmove")
            best_move = lines[-1].split()[1]
            assert lines[-2].startswith("info")
            _ = lines[-2].split()
            score_cp =  int(_[_.index("cp") + 1]) / 100
            ana_depth = int(_[_.index("depth") + 1])
            return best_move, score_cp, ana_depth
        except (AssertionError, IndexError, ValueError) as e:
            print(f"Warning: Invalid output from engine.\t{e.with_traceback}")
            return None, None, None
    
    def 这种评分评价他会把人的付出给异化掉的懂吗(self, fen: str, user_move: str, one_movetime=2000) -> float | None:
        # try: mycamp = {'w': 1, 'b': -1}[fen.strip().split()[1]]
        # except LookupError:
        #     raise ValueError(f"Warning: Invalid FEN string: {fen}")
        if not is_pgn(user_move):
            raise ValueError(f"Warning: Invalid PGN move: {user_move}")
        best_move, before_score_cp, _ = self.analyze(fen, one_movetime)
        if best_move == user_move:
            return float("inf")
        _, after_score_cp, _ = self.analyze(self.perform_move(fen, user_move))
        if before_score_cp is None or after_score_cp is None:
            print("Warning: Invalid score from engine.")
            return None
        print(f"{user_move}前评分: {before_score_cp}，后评分: {after_score_cp}")
        print(f"{user_move=}, {best_move=}")
        # return (after_score_cp + before_score_cp) * mycamp
        return -(after_score_cp + before_score_cp)

    def close(self) -> None:
        """关闭引擎"""
        self._send_command("quit")
        time.sleep(0.2)
        self.proc.terminate()
        self.proc.wait()
        print("Engine closed.")


def test():
    # 初始化引擎
    print("=== 测试 BinggoEngine 功能 ===")
    eng = BinggoEngine()

    # 初始FEN位置
    ori_fen = "rnbk1qnbr/pppp1pppp/9/9/9/OOO1O1OOO/1A5A1/9/CMXSWSXMC w kq - 0 1"
    test_fen = 'rnbk1qnbr/pppp1pppp/9/9/4O4/O1O3O1O/1A5A1/9/CMXSWSXMC b kq - 0 1'

    print("\n1. 测试走法生成功能:")
    moves = eng.pms(test_fen)
    print(f"在给定位置找到 {len(moves)} 个合法走法")
    print(f"前10个走法: {moves[:10]}")

    print("\n2. 测试执行走法功能:")
    if moves:
        first_move = moves[0]
        print(f"执行走法: {first_move}")
        new_fen = eng.perform_move(test_fen, first_move)
        print(f"执行后的FEN: {new_fen}")

    print("\n3. 测试最佳走法功能:")
    best_move, best_new_fen = eng.best_move(ori_fen, movetime=1000)  # 1秒思考时间
    if best_move:
        print(f"最佳走法: {best_move}")
        print(f"走法后的新FEN: {best_new_fen}")
    else:
        print("未能找到最佳走法")

    print("\n4. 测试多个连续走法:")
    if moves and len(moves) >= 2:
        move1 = moves[0]
        move2 = moves[1]
        print(f"执行走法序列: [{move1}, {move2}]")
        new_fen_seq = eng.perform_move(test_fen, [move1, move2])
        print(f"执行序列后的新FEN: {new_fen_seq}")

    print("\n5. 显示当前棋盘状态:")
    eng._d()

    eng.close()
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    # test()
    eng = BinggoEngine()
    fen = "rnbk1qnbr/ppppOpppp/9/9/9/OOO1O1OOO/1A5A1/9/CMXSWSXMC w kq - 0 1"
    print("e8e9j" in eng.pms(fen))
