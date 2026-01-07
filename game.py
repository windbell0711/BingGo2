import beach

class Game:
    def __init__(self):
        self.board = beach.Beach()
        self.steady_pieces = set()
        self.highlight_paths = set()
        self.piece_animations = []
        self.last_choice_piece = (-1,-1)
        self.UIs = []
        self.board_is_flipped = False
        self.state = 'play'
        self.moves = []
        self.move_step = 0
    
    def reset_special_pieces_show(self):
        self.highlight_paths = []
        self.last_choice_piece = (-1,-1)

    def handle_input_p(self, display_p):
        # 下棋
        if display_p is not None:
            if self.state == 'play':
                if 0 <= display_p <= 80:
                    ## 待办：这里要适配翻转棋盘 ##
                    self.handle_board_event(display_p)
                elif 81 <= display_p:
                    self.reset_special_pieces_show()
                    self.handle_game_UIs(display_p)
        if self.state == 'play':
            self.process_animation()
            self.process_steady_pieces()
        # 返回全部显示组件
        return (self.board_is_flipped, self.steady_pieces, self. piece_animations,
                self.last_choice_piece, self.highlight_paths, self.UIs)

    def handle_game_UIs(self, p):
        if p == 98:
            self.undo()
        elif p == 99:
            self.gret()

    # 删除结束的动画，进度 +1
    def process_animation(self):
        temp = []
        for ani in self.piece_animations:
            if not ani[2] >= ani[3]:
                temp.append((ani[0], ani[1], ani[2]+1, ani[3], ani[4]))
        self.piece_animations = temp

    def apply_animation(self, move):
        fp = beach.fsf2beach(move[:2])
        tp = beach.fsf2beach(move[2:4])
        eat_typ = self.board[tp]
        if eat_typ >= 0:
            self.piece_animations.append((tp, tp, 0, 10, eat_typ))
        piece_typ = self.board[fp]
        if move == 'd9b9' and piece_typ == 12:
            self.piece_animations.append((0, 2, -10, 10, 8))
        if move == 'd9f9' and piece_typ == 12:
            self.piece_animations.append((8, 4, -10, 10, 8))
        if piece_typ >= 0:
            self.piece_animations.append((fp, tp, 0, 10, piece_typ))


    # 将静态棋子剔除动画结束位与选中位
    def process_steady_pieces(self):
        pieces_to_hide = {self.last_choice_piece[0]}
        for _, end_pos, _, _, _ in self.piece_animations:
            pieces_to_hide.add(end_pos)
        self.steady_pieces.clear()
        p = 0
        for typ in self.board:
            if typ > 0 and p not in pieces_to_hide:
                ## 待办：这里要适配翻转棋盘 ##
                self.steady_pieces.add((p, typ))
            p += 1

    # 走子模式下，棋盘上点击的操作，控制高亮路径和选中的棋子
    def handle_board_event(self,beach_p):
        # 是一步走子
        if beach_p in self.highlight_paths:
            # 添加动画 并且更新 beach 状态
            move = beach.beach2fsf(self.last_choice_piece[0]) + beach.beach2fsf(beach_p)

            self.apply_animation(move)

            self.reset_special_pieces_show()
            self.board.apply_move(move)

            self.moves = self.moves[:self.move_step]
            self.move_step += 1
            self.moves.append(move)
            return
        # 如果没选子，直接重置
        if beach_p is None:
            self.reset_special_pieces_show()
            return
        self.highlight_paths = self.board.get_pms(beach_p)
        # 如果子走不动路，重置
        if not self.highlight_paths:
            self.reset_special_pieces_show()
            return
        self.last_choice_piece = (beach_p, self.board[beach_p])
        # 是一步选子
        print(self.last_choice_piece,self.highlight_paths)

    def undo(self):
        if self.move_step > 0:
            self.move_step -= 1
            self.board.moves_reset(self.moves[:self.move_step])
            move = self.moves[self.move_step]
            fp = beach.fsf2beach(move[:2])
            tp = beach.fsf2beach(move[2:4])
            eat_typ = self.board[tp]
            if eat_typ >= 0:
                self.piece_animations.append((tp, tp, 0, 10, eat_typ))
            piece_typ = self.board[fp]
            if move == 'd9b9' and piece_typ == 12:
                self.piece_animations.append((2, 0, -10, 10, 8))
            if move == 'd9f9' and piece_typ == 12:
                self.piece_animations.append((4, 8, -10, 10, 8))
            if piece_typ >= 0:
                self.piece_animations.append((tp, fp, 0, 10, piece_typ))

    def gret(self):
        if self.move_step < len(self.moves):
            self.apply_animation(self.moves[self.move_step])
            self.move_step += 1
            self.board.moves_reset(self.moves[:self.move_step])

    def quit(self):
        self.board.suicide()


# from typing import Generator
# from dataclasses import dataclass

# @dataclass
# class Screen:
#     empty:   bool = False
#     flipped: bool = False
#     normal_pieces:    list[tuple[int, int]] = []
#     highlight_pieces: list[tuple[int, int]] = []

# def game() -> Generator[Screen, int, None]:
#     ...
#     yld = Screen(empty=True)
#     while True:
#         # do not modify yld before this line
#         event: int = yield yld
#         ...
#         yld = Screen(
#             flipped=False,
#             normal_pieces=[(1, 2), (3, 4)],
#             highlight_pieces=[(5, 6)]
#         )  # do not modify yld after this line
