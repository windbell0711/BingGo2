import subprocess
import time
import logging
from typing import Optional, Iterable

# 获取模块专用logger
logger = logging.getLogger(__name__)

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

def betza_is_invalid(betza: str) -> int:
    VALID, INVALID, VERY_INVALID = 0, 1, 2
    if not betza or betza.count(':') > 1:
        return VERY_INVALID
    betza = betza.replace(' ', '')
    if ':' in betza:
        if betza.find(':') != 1 or betza[:1] not in PIECE_TYPS_LOWER:
            return VERY_INVALID
        if len(betza) == 2:
            return VALID  # 如'q:'走不动，但是也允许
        betza = betza[betza.find(':')+1:]
    if betza[0].isdigit():  return VERY_INVALID
    if betza[-1] in 'abcdefghijklmnopqrstuvwxyz': return VERY_INVALID
    for i in range(len(betza)):
        if betza[i] in '012345678':
            if betza[i-1] not in 'WFNRBQ':
                return INVALID
        elif betza[i] not in 'WFNRBQDHAGCZKfblrvscmgpjni':
            return INVALID
    return VALID
    
def fen_is_invalid(fen: str) -> str:
    """检查FEN格式是否合法，返回错误信息（若合法则返回空字符串）"""
    parts = fen.strip().split()
    if len(parts) != 6:
        return "Invalid FEN: Invalid number of parts"

    piece_placement, active_color, castling, en_passant, halfmove, fullmove = parts

    ranks = piece_placement.split('/')
    if len(ranks) != len(BOARD_RANKS):
        return "Invalid FEN: Invalid number of ranks"

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
                    return f"第{len(BOARD_RANKS)-rank_idx}行: 数字{num}超出范围(1-{len(BOARD_FILES)})"
                file_count += num
            elif ch in valid_pieces:  # 棋子
                file_count += 1
            else:  # 非法字符
                return f"第{len(BOARD_RANKS)-rank_idx}行: 非法字符 '{ch}'"
            i += 1

        if file_count != len(BOARD_FILES):
            return f"第{len(BOARD_RANKS)-rank_idx}行: 应有{len(BOARD_FILES)}列，实际有{file_count}列"

    if active_color not in ('w', 'b'):
        return f"活动方应为'w'或'b'，实际是'{active_color}'"

    if castling != '-':
        for ch in castling:
            if ch not in ('K', 'Q', 'k', 'q'):
                return f"王车易位包含非法字符 '{ch}'"

    if en_passant != '-':
        return "暂不支持过路兵"

    if not halfmove.isdigit():
        return f"半回合计数不是有效整数: {halfmove}"
    if not fullmove.isdigit():
        return f"完整回合计数不是有效整数: {fullmove}"

    return ""  # 合法FEN，返回空字符串


class BinggoEngine:
    def __init__(self, 
                 engine_path: str = "engine\\fairy-stockfish-largeboards_x86-64-bmi2-latest.exe",  # 沿用BingGo beta 1.2使用的引擎，否则Pawn出现意外错误
                 ini_file:    str = "engine\\binggo.ini",
                 debug_file:  Optional[str] = None):
        """
        初始化引擎
        engine_path: 引擎可执行文件路径
        """
        logger.debug(f"Starting engine: {engine_path}")

        try:
            self.proc = subprocess.Popen(
                [engine_path],
                creationflags=subprocess.CREATE_NO_WINDOW,  # https://blog.51cto.com/u_16175464/12403697
                universal_newlines=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1  # 行缓冲
            )
        except FileNotFoundError:
            error_msg = f"Error: Engine file '{engine_path}' not found"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
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
        logger.debug("Engine initialized and ready!")

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
            error_msg = "Engine stdout is not available"
            logger.error(error_msg)
            raise AttributeError(error_msg)

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
        logger.warning(f"Too many lines to read without finding '{until}', trying to stop...")
        self.stop()
        time.sleep(0.500)
        for _ in range(220):
            line = self._readline()
            if del_blank_lines and line.strip() == "":
                continue
            if not any((word in line) for word in ignore):
                output += line
            if until in line:
                return output
        logging.warning("Still fail to find")
        raise RuntimeError("Too many lines to read without finding '{until}'")

    def _send_command(self, cmd: str) -> None:
        """发送命令到引擎"""
        if not self.proc.stdin:
            logger.warning("Warning: Engine stdin not available")
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
            error_msg = "Error: Please specify either movetime or depth"
            logger.error(error_msg)
            raise ValueError(error_msg)
        if movetime == 207016001046:
            return "go infinity"
        else:
            return f"go movetime {movetime}" if movetime > 0 else f"go depth {depth}"

    def _d(self) -> None:
        """输出并显示当前棋盘状态"""
        self._send_command("d")
        board_output = self._read_until("Chased", ignore=("Sfen", "Checkers", "Key", "Chased"))
        logger.info(board_output)

    def perform_move(self, fen: str, move: str | Iterable[str]) -> str:
        """
        根据给定的FEN和走法，返回新的FEN
        :param fen:  起始局面的FEN字符串
        :param move: 要执行的走法（如"e2e4"）
        :return:     执行走法后的新FEN
        """
        # 处理输入
        if not move:
            return fen
        if fen_is_invalid(fen):
            warning_msg = f"Warning: Invalid FEN: {fen} {fen_is_invalid(fen)}"
            logger.warning(warning_msg)
            raise ValueError(warning_msg)
        if isinstance(move, list):
            moves = ""
            for m in move:
                if is_pgn(m):
                    moves += m + " "
                else:
                    warning_msg = f"Warning: Invalid PGN move: {m}"
                    logger.warning(warning_msg)
                    raise ValueError(warning_msg)
            moves = moves.strip()
        elif isinstance(move, str):
            if not is_pgn(move):
                warning_msg = f"Warning: Invalid PGN move: {move}"
                logger.warning(warning_msg)
                raise ValueError(warning_msg)
            moves = move
        else:
            error_msg = "move must be str or Iterable[str]"
            logger.error(error_msg)
            raise TypeError(error_msg)

        # 设置局面并执行走法
        self._send_command(f"position fen {fen} moves {moves}")
        self._send_command("d")

        # 读取棋盘显示
        output = self._read_until("Chased")
        new_fen = self._extract_fen_from_board(output)
        if new_fen == fen:
            logger.warning(f"Warning: No change ({fen}) after move {moves}")

        if new_fen:
            return new_fen
        else:
            error_msg = f"Error: Could not extract FEN after move {moves}"
            logger.error(error_msg)
            return fen

    def pms(self, fen: str) -> list[str]:
        """
        获取给定FEN下的所有合法走法列表
        @param fen: 起始局面的FEN字符串
        @return: 所有合法走法的字符串列表
        """
        if fen_is_invalid(fen):
            warning_msg = f"Warning: Invalid FEN: {fen} {fen_is_invalid(fen)}"
            logger.warning(warning_msg)
            raise ValueError(warning_msg)
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
                    logger.warning(f"Warning: Invalid PGN move: {move}")
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
        if fen_is_invalid(fen):
            warning_msg = f"Warning: Invalid FEN: {fen} {fen_is_invalid(fen)}"
            logger.warning(warning_msg)
            raise ValueError(warning_msg)
        # 获取最佳走法
        self._send_command(f"position fen {fen}")
        self._send_command(self._process_input_think_time(movetime, depth))
        output = self._read_until("bestmove").strip()
        parts = output.split('\n')[-1].strip().split()
        if len(parts) > 1 and is_pgn(parts[1]):
            best_move = parts[1]
        else:
            logger.warning(f"Warning: No best move found for FEN {fen}")
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
        if fen_is_invalid(fen):
            warning_msg = f"Warning: Invalid FEN: {fen} {fen_is_invalid(fen)}"
            logger.warning(warning_msg)
            raise ValueError(warning_msg)
        # 解析mycamp
        try: mycamp = {'w': 1, 'b': -1}[fen.strip().split()[1]]
        except LookupError:
            warning_msg = f"Warning: Invalid FEN string: {fen}"
            logger.warning(warning_msg)
            raise ValueError(warning_msg)
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
            logger.warning(f"Warning: Invalid output from engine. {e}")
            return None, None, None, None
    
    def close(self) -> None:
        """关闭引擎"""
        self._send_command("quit")
        time.sleep(0.2)
        self.proc.terminate()
        self.proc.wait()
        logger.debug("Engine closed.")


if __name__ == "__main__":
    eng = BinggoEngine(debug_file="engine\\debug.log")
    root_fen = "rbnk1qbnr/pppp1pppp/9/9/9/OOO1O1OO1/1A5A1/9/CMXSWSXMC w kq - 0 1"
    fen = eng.perform_move(root_fen, "a1a2 f9a4 a2a1".split())
    print(fen)
    eng._d()
