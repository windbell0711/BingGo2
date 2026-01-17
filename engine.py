import subprocess
import time
import logging
from typing import Optional, Iterable

# 配置基本的日志记录器
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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

def is_fen(fen: str) -> bool:
    """检查是否符合FEN格式"""
    parts = fen.strip().split()
    if len(parts) != 6:
        logging.warning("Invalid FEN: Invalid number of parts")
        return False
    piece_placement, active_color, castling, en_passant, halfmove, fullmove = parts
    
    ranks = piece_placement.split('/')
    if len(ranks) != len(BOARD_RANKS):
        logging.warning("Invalid FEN: Invalid number of ranks")
        return False
    valid_pieces = PIECE_TYPS_LOWER + PIECE_TYPS_LOWER.upper()
    
    for rank_idx, rank in enumerate(ranks):
        file_count = 0
        i = 0
        while i < len(rank):
            ch = rank[i]
            if ch.isdigit():  # 数字表示空格
                if i + 1 < len(rank) and rank[i+1].isdigit():  # 处理两位数
                    num = int(ch + rank[i+1])
                    i += 1
                else:
                    num = int(ch)
                if num < 1 or num > len(BOARD_FILES):
                    logging.warning(f"第{len(BOARD_RANKS)-rank_idx}行: 数字{num}超出范围(1-{len(BOARD_FILES)})")
                    return False
                file_count += num
            elif ch in valid_pieces:  # 棋子
                file_count += 1
            else:  # 非法字符
                logging.warning(f"第{len(BOARD_RANKS)-rank_idx}行: 非法字符 '{ch}'")
                return False
            i += 1
        
        if file_count != len(BOARD_FILES):
            logging.warning(f"第{len(BOARD_RANKS)-rank_idx}行: 应有{len(BOARD_FILES)}列，实际有{file_count}列")
            return False
    
    if active_color not in ('w', 'b'):
        logging.warning(f"活动方应为'w'或'b'，实际是'{active_color}'")
        return False
    
    if castling != '-':
        for ch in castling:
            if ch not in ('K', 'Q', 'k', 'q'):
                logging.warning(f"王车易位包含非法字符 '{ch}'")
                return False
    
    if en_passant != '-':
        logging.warning("暂不支持过路兵")
        return False
    
    if not halfmove.isdigit():
        logging.warning(f"半回合计数不是有效整数: {halfmove}")
        return False
    if not fullmove.isdigit():
        logging.warning(f"完整回合计数不是有效整数: {fullmove}")
        return False
    
    return True


class BinggoEngine:
    def __init__(self, 
                 engine_path: str = "engine\\fairy-stockfish-largeboards_x86-64-bmi2-latest.exe",  # 沿用BingGo beta 1.2使用的引擎，否则Pawn出现意外错误
                 ini_file:    str = "engine\\binggo.ini",
                 debug_file:  Optional[str] = None):
        """
        初始化引擎
        engine_path: 引擎可执行文件路径
        """
        logging.info(f"Starting engine: {engine_path}")

        try:
            self.proc = subprocess.Popen(
                [engine_path],
                universal_newlines=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1  # 行缓冲
            )
        except FileNotFoundError:
            logging.error(f"Error: Engine file '{engine_path}' not found")
            raise FileNotFoundError(f"Error: Engine file '{engine_path}' not found")
        
        self.wait_time = 0.001

        # 初始化引擎
        self._send_command("uci")
        if debug_file:
            self._send_command(f"setoption name Debug Log File value {debug_file}")
        self._send_command(f"setoption name VariantPath value {ini_file}")
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
        logging.info("Engine initialized and ready!")

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
            logging.error("Engine stdin is not available")
            return ""

    def _read_until(self, until: str, ignore: Optional[Iterable[str]] = None, 
                    del_blank_lines=True) -> str:
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
        for _ in range(2070):
            line = self._readline()
            if del_blank_lines and line.strip() == "":
                continue
            if not any((word in line) for word in ignore):
                output += line
            if until in line:
                return output
        logging.error(f"Too many lines to read without finding '{until}'")
        return ""
    
    def _send_command(self, cmd: str) -> None:
        """发送命令到引擎"""
        if not self.proc.stdin:
            logging.warning("Warning: Engine stdin not available")
            return
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()
        time.sleep(self.wait_time)
    
    def stop(self) -> None:
        """终止思考"""
        self._send_command("stop")

    @staticmethod
    def _extract_fen_from_board(board_output):
        """从棋盘显示中提取FEN字符串"""
        for line in board_output.split('\n'):
            if line.startswith("Fen:"):  # 查找包含"Fen:"的行
                return line[4:].strip()
        return None
    
    @staticmethod
    def _process_input_think_time(movetime, depth) -> str:
        """
        解析输入
        @param movetime: 思考时间（毫秒）
        @param depth: 搜索深度
        @return: cmd
        """
        if not (depth > 0) ^ (movetime > 0):
            logging.error("Error: Please specify either movetime or depth")
            return ""
        if movetime == 207016001046:
            return "go infinity"
        else:
            return f"go movetime {movetime}" if movetime > 0 else f"go depth {depth}"

    def _d(self) -> None:
        """输出并显示当前棋盘状态"""
        self._send_command("d")
        board_output = self._read_until("Chased", ignore=("Sfen", "Checkers", "Key", "Chased"))
        logging.info(board_output)

    def perform_move(self, fen: str, move: str | Iterable[str]) -> str:
        """
        根据给定的FEN和走法，返回新的FEN
        :param fen:  起始局面的FEN字符串
        :param move: 要执行的走法（如"e2e4"）
        :return:     执行走法后的新FEN
        """
        # 处理输入
        if not is_fen(fen):
            logging.error(f"Invalid FEN: {fen}")
            return ""
        if isinstance(move, list):
            moves = ""
            for m in move:
                if is_pgn(m):
                    moves += m + " "
                else:
                    logging.error(f"Warning: Invalid PGN move: {m}")
                    return ""
            moves = moves.strip()
        elif isinstance(move, str):
            if not is_pgn(move):
                logging.error(f"Warning: Invalid PGN move: {move}")
                return ""
            moves = move
        else:
            raise TypeError("move must be str or Iterable[str]")

        # 设置局面并执行走法
        self._send_command(f"position fen {fen} moves {moves}")
        self._send_command("d")

        # 读取棋盘显示
        output = self._read_until("Chased")
        new_fen = self._extract_fen_from_board(output)
        if new_fen == fen:
            logging.warning(f"Warning: No change ({fen}) after move {moves}")

        if new_fen:
            return new_fen
        else:
            logging.error(f"Error: Could not extract FEN after move {moves}")
            return fen

    def pms(self, fen: str) -> list[str]:
        """
        获取给定FEN下的所有合法走法列表
        @param fen: 起始局面的FEN字符串
        @return: 所有合法走法的字符串列表
        """
        if not is_fen(fen):
            logging.warning(f"Warning: Invalid FEN: {fen}")
            return []
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
                    logging.warning(f"Warning: Invalid PGN move: {move}")
        return moves

    def best_move(self, fen: str, movetime=0, depth=0) -> tuple[str, str] | tuple[None, None]:
        """
        从给定的FEN位置获取最佳走法
        @param fen: 起始局面的FEN字符串
        @param movetime: 思考时间(毫秒)
        @param depth: 搜索深度
        @return: (best_move, new_fen): 最佳走法和执行走法后的新FEN

        出错则为None，请及时校验。
        """
        if not is_fen(fen):
            logging.error(f"Warning: Invalid FEN: {fen}")
            return None, None
        # 获取最佳走法
        self._send_command(f"position fen {fen}")
        self._send_command(self._process_input_think_time(movetime, depth))
        output = self._read_until("bestmove").strip()
        parts = output.split('\n')[-1].strip().split()
        if len(parts) > 1 and is_pgn(parts[1]):
            best_move = parts[1]
        else:
            logging.error(f"Warning: No best move found for FEN {fen}")
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

    def analyze(self, fen: str, movetime=0, depth=0) -> tuple[str, int, str, int] | tuple[None, None, None, None]:  # TODO
        if not is_fen(fen):
            logging.error(f"Warning: Invalid FEN: {fen}")
            return None, None, None, None
        # 解析mycamp
        try: mycamp = {'w': 1, 'b': -1}[fen.strip().split()[1]]
        except LookupError:
            logging.error(f"Warning: Invalid FEN string: {fen}")
            return None, None, None, None
        # 获取输出
        self._send_command(f"position fen {fen}")
        self._send_command(self._process_input_think_time(movetime, depth))
        output = self._read_until("bestmove").strip()
        lines = output.split('\n')
        # 解析数据
        try:
            assert lines[-1].startswith("bestmove")
            best_move = lines[-1].split()[1]
            assert lines[-2].startswith("info")
            _ = lines[-2].split()
            ana_depth = int(_[_.index("depth") + 1])
            if "mate" in _:
                return "mate",  int(_[_.index("mate") + 1]) * mycamp, best_move, ana_depth
            else:
                return "score", int(_[_.index("cp") + 1]) * mycamp,   best_move, ana_depth
        except (AssertionError, IndexError, ValueError) as e:
            logging.error(f"Warning: Invalid output from engine. {e}")
            return None, None, None, None
    
    def close(self) -> None:
        """关闭引擎"""
        self._send_command("quit")
        time.sleep(0.2)
        self.proc.terminate()
        self.proc.wait()
        logging.info("Engine closed.")


if __name__ == "__main__":
    eng = BinggoEngine(debug_file="debug.log")
    root_fen = "rnbk1qnbr/pppp1pppp/9/9/9/OOO1O1OOO/1A5A1/9/CMXSWSXMC w kq - 0 1"
    # fen = eng.perform_move(root_fen, "a4b4 f9c6 h3a3 c9b7 g1e3 d9c9 b3c3 c6e4 h1f2 e4d5 c4c5 d5d2 c1d2 b7d6 a3a9".split())
    # print(fen)
    logging.info(eng.analyze(root_fen, depth=8))
    # eng._d()