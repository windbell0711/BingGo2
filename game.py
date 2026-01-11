import beach
from threading import Thread

ANIM_SPEED = 1

class Game:
    def __init__(self):
        self.board = beach.Beach()
        #显示相关
        self.steady_pieces = set()
        self.highlight_paths = set()
        self.piece_animations = []
        self.last_choice_piece = (-1,-1)
        self.UIs = set()
        self.board_is_flipped = False
        self.pressed_button = [-1,0]
        #走子记录相关
        self.state = 'play'
        self.moves = []
        self.move_step = 0
        self.promotion_move = ''
        # 游戏规则相关
        self.ai_chn = False
        self.ai_int = False
        self.ai_think_time = 500

    def reset_special_pieces_show(self):
        self.highlight_paths = []
        self.last_choice_piece = (-1,-1)

    def handle_input_p(self, display_p):
        # 下棋
        if self.state == 'play':
            if display_p is not None:
                if 0 <= display_p <= 80:
                    self.handle_board_event(display_p if not self.board_is_flipped else 80 - display_p)
                elif 81 <= display_p:
                    self.reset_special_pieces_show()
                    self.handle_game_UIs(display_p)
                    self.adjust_ai(display_p)
            self.process_animation()
            self.process_steady_pieces()
            self.process_UIs()
        elif self.state == 'wait' or self.state == 'waits':
            if display_p is not None:
                self.adjust_ai(display_p)
            self.process_animation()
            self.process_steady_pieces()
            self.process_UIs()
        elif self.state == 'promotion':
            if display_p is not None:
                if self.board_is_flipped:
                    self.handle_promotion_select(80-display_p)
                else:
                    self.handle_promotion_select(display_p)
        # 返回全部显示组件
        return (self.board_is_flipped, self.steady_pieces, self. piece_animations,
                self.last_choice_piece, self.highlight_paths, self.UIs, self.pressed_button)

    def handle_promotion_select(self, p):
        tp = beach.fsf2beach(self.promotion_move[2:4])
        z = None
        if p == tp:
            z = 'q'
        elif p == tp -9:
            z = 'n'
        elif p == tp -18:
            z = 'b'
        elif p == tp - 27:
            z = 'r'
        if z is not None:
            self.apply_move(self.promotion_move+z)

    def adjust_ai(self, p):
        if self.board_is_flipped:
            p = 170 - p
        if p == 81:
            self.ai_int ^= 1
            if self.ai_int and ' b ' in self.board.fen and self.state == 'play':
                self.auto_move()
        elif p == 89:
            self.ai_chn ^= 1
            if self.ai_chn and ' w ' in self.board.fen and self.state == 'play':
                self.auto_move()

    def handle_game_UIs(self, p):
        if p == 98:
            if self.ai_chn ^ self.ai_int:
                self.thread_undo(2)
            else:
                self.thread_undo()
            self.pressed_button = [98, 10]
        elif p == 99:
            self.thread_gret()
            self.pressed_button = [99, 10]
        elif p == 96:
            self.board_is_flipped ^= 1
            self.pressed_button = [96, 10]
        elif p == 91:
            self.auto_move()

    # 删除结束的动画，进度 +1
    def process_animation(self):
        if len(self.piece_animations) > 20:
            self.piece_animations.clear()
            return
        temp = []
        for ani in self.piece_animations:
            if not ani[2] >= ani[3]:
                temp.append((ani[0], ani[1], ani[2]+1, ani[3], ani[4]))
        self.piece_animations = temp

    # 将静态棋子剔除动画结束位与选中位
    def process_steady_pieces(self):
        pieces_to_hide = {self.last_choice_piece[0]}
        for _, end_pos, _, _, _ in self.piece_animations:
            pieces_to_hide.add(int(end_pos+0.5))
        self.steady_pieces.clear()
        p = 0
        for typ in self.board:
            if typ > 0 and p not in pieces_to_hide:
                self.steady_pieces.add((p, typ))
            p += 1

    #这个顺便处理UI按钮点击效果
    def process_UIs(self):
        self.UIs.clear()
        if self.state == 'play' or self.state == 'waits':
            self.UIs.add((91, '!'))
            self.UIs.add((96, '&'))
            self.UIs.add((98, 'undo'))
            self.UIs.add((99, 'gret'))
        if self.state == 'play' or self.state == 'wait' or self.state == 'waits':
            if self.board_is_flipped:
                self.UIs.add((89, 'r' if self.ai_int else 'h'))
                self.UIs.add((81, 'r' if self.ai_chn else 'h'))
            else:
                self.UIs.add((81, 'r' if self.ai_int else 'h'))
                self.UIs.add((89, 'r' if self.ai_chn else 'h'))
        if self.pressed_button[-1] > 0:
            self.pressed_button[-1] -= 1

    def _am(self, d=False):
        if d:
            self.gret()
        if not self.board.get_pms():
            self.state = 'play'
            return
        self.state = 'wait'
        try:
            move = self.board.get_best_move(think_time=self.ai_think_time)
        except RuntimeError:
            return
        self.apply_move(move)

    def auto_move(self, do_gret=False):
        Thread(target=self._am,args=(do_gret,)).start()

    def apply_move(self, move):
        if len(self.moves) != self.move_step:
            self.moves = self.moves[:self.move_step]
        self.moves.append(move)
        if ((self.ai_chn and ' b ' in self.board.fen) or
            (self.ai_int and ' w ' in self.board.fen)):
            self.auto_move(True)
        else:
            self.thread_gret()

    # 走子模式下，棋盘上点击的操作，控制高亮路径和选中的棋子
    def handle_board_event(self,beach_p):
        # 是一步走子
        if beach_p in self.highlight_paths:
            # 添加动画 并且更新 beach 状态
            fp = self.last_choice_piece[0]
            move = beach.beach2fsf(fp) + beach.beach2fsf(beach_p)
            tp = beach_p
            # 如果走子是升变
            if self.board[fp] == 13 and tp//9 == 8:
                self.state = 'promotion'
                self.highlight_paths.clear()
                self.promotion_move = move
                self.piece_animations.append((-1, tp, -1, 1, 14))
                self.piece_animations.append((-1, tp - 9, -1, 1, 14))
                self.piece_animations.append((-1, tp - 18, -1, 1, 14))
                self.piece_animations.append((-1, tp - 27, -1, 1, 14))
                self.piece_animations.append((-1, tp, -1, 1, 11))
                self.piece_animations.append((-1, tp - 9, -1, 1, 10))
                self.piece_animations.append((-1, tp - 18, -1, 1, 9))
                self.piece_animations.append((-1, tp - 27, -1, 1, 8))
                return
            # 中国象棋的升变
            # elif self.board[fp] == 7 and tp//9 == 0:
            #     move += 'j'
            self.reset_special_pieces_show()
            self.apply_move(move)
            return
        # 如果没选子或选了一样的，直接重置
        if beach_p is None or beach_p == self.last_choice_piece[0]:
            self.reset_special_pieces_show()
            return
        self.highlight_paths = self.board.get_pms(beach_p)
        # 如果子走不动路，重置
        if not self.highlight_paths:
            self.reset_special_pieces_show()
            p, typ = beach_p, self.board[beach_p]
            if typ >= 0:
                if self.board_is_flipped:
                    self.piece_animations.append((p - 0.15, p, 0, 3, typ))
                    self.piece_animations.append((p, p - 0.15, -3, 3, typ))
                else:
                    self.piece_animations.append((p + 0.15, p, 0, 3, typ))
                    self.piece_animations.append((p, p + 0.15, -3, 3, typ))
            return
        self.last_choice_piece = (beach_p, self.board[beach_p])

    def undo(self, steps=1):
        if self.move_step >= steps:
            self.reset_special_pieces_show()
            self.move_step -= steps
            self.board.moves_reset(self.moves[:self.move_step])
            move = self.moves[self.move_step]
            fp = beach.fsf2beach(move[:2])
            tp = beach.fsf2beach(move[2:4])
            eat_typ = self.board[tp]
            if eat_typ >= 0:
                self.piece_animations.append((tp, tp, 0, 10//ANIM_SPEED,eat_typ))
            piece_typ = self.board[fp]
            if move == 'd9b9' and piece_typ == 12:
                self.piece_animations.append((2, 2, 0, 10//ANIM_SPEED, 8))
                self.piece_animations.append((2, 0, -10//ANIM_SPEED, 10//ANIM_SPEED, 8))
            if move == 'd9f9' and piece_typ == 12:
                self.piece_animations.append((4, 4, 0, 10//ANIM_SPEED, 8))
                self.piece_animations.append((4, 8, -10//ANIM_SPEED, 10//ANIM_SPEED, 8))
            if piece_typ >= 0:
                self.piece_animations.append((tp, fp, 0, 10//ANIM_SPEED, piece_typ))

    def gret(self):
        if self.move_step < len(self.moves):
            self.reset_special_pieces_show()
            move = self.moves[self.move_step]
            fp = beach.fsf2beach(move[:2])
            tp = beach.fsf2beach(move[2:4])
            eat_typ = self.board[tp]
            if eat_typ >= 0:
                self.piece_animations.append((tp, tp, 0, 10//ANIM_SPEED, eat_typ))
            piece_typ = self.board[fp]
            if move == 'd9b9' and piece_typ == 12:
                self.piece_animations.append((0, 0, 0, 10//ANIM_SPEED, 8))
                self.piece_animations.append((0, 2, -10//ANIM_SPEED, 10//ANIM_SPEED, 8))
            if move == 'd9f9' and piece_typ == 12:
                self.piece_animations.append((8, 8, 0, 10//ANIM_SPEED, 8))
                self.piece_animations.append((8, 4, -10//ANIM_SPEED, 10//ANIM_SPEED, 8))
            if piece_typ >= 0:
                self.piece_animations.append((fp, tp, 0, 10//ANIM_SPEED, piece_typ))
            self.move_step += 1
            self.board.moves_reset(self.moves[:self.move_step])

    def reset(self, fen = None):
        if fen is None:
            self.board.reset()
        else:
            self.board.reset(fen)

        self.steady_pieces.clear()
        self.highlight_paths.clear()
        self.piece_animations.clear()
        self.last_choice_piece = (-1, -1)
        self.UIs.clear()
        self.pressed_button = [-1, 0]

        self.state = 'play'
        self.moves = []
        self.move_step = 0
        self.ai_chn = False
        self.ai_int = False

    def _tu(self,s):
        self.state = 'waits'
        self.undo(s)
        self.state = 'play'

    def thread_undo(self,s=1):
        Thread(target=self._tu,args=(s,)).start()

    def _tg(self):
        self.state = 'waits'
        self.gret()
        self.state = 'play'

    def thread_gret(self):
        Thread(target=self._tg).start()

    def quit(self):
        self.board.suicide()
