import logging
import os
from threading import Thread
from tkinter import filedialog

import beach
import rate
import constant as cns


logger = logging.getLogger(__name__)

class SettingElement:
    def __init__(self, rect):
        if rect is not None:
            for i in rect:
                if not 0<=i<=1:
                    error_msg = "rect参数错误"
                    logger.error(error_msg)
                    raise ValueError(error_msg)
        self.rect = rect

    def is_clicked(self, x, y):
        return self.rect[0]<x<self.rect[0]+self.rect[2] and self.rect[1]<y<self.rect[1]+self.rect[3]

    def active(self):
        pass

    def tick_update(self,c,p):
        pass

class Button(SettingElement):
    def __init__(self,commands,texts,n=0,rect = None,shade_time_max=10):
        super().__init__(rect)
        self.n = n; self.commands = commands; self.texts = texts
        if len(commands) != len(texts):
            error_msg = "commands和texts长度不一致"
            logger.error(error_msg)
            raise ValueError(error_msg)
        self.length = len(commands)
        self.shade_time_max = shade_time_max
        self.shade_time = 0

    def active(self):
        self.n+=1
        self.n%=self.length
        self.shade_time = self.shade_time_max
        return self.commands[self.n]

    def return_text(self):
        return self.texts[self.n]

    def tick_update(self,c,p):
        if not p:
            self.shade_time = max(0, self.shade_time-cns.ANIM_SPEED)

def sort_menu_elements_rect(menu, element_per_line_max = 2):
    line_count = 0
    per_line_count = 0
    line_d = 0.1 #行距
    side_d = 0.2 #边距
    top_d = 0.3 #顶端优势
    elem_d = (1 - 2*side_d)/(element_per_line_max*4-1)*4 #元素间距

    elex = elem_d * (3/4) #元素宽
    eley = line_d / 2

    for elem in menu:
        if elem.rect is not None:
            continue
        if type(elem) == Button:
            _temp_rect = (side_d+per_line_count*elem_d, top_d+line_count*line_d, elex, eley)
            elem.rect = _temp_rect

        per_line_count += 1
        if per_line_count >= element_per_line_max:
            line_count += 1
            per_line_count = 0

main_menu =  [
             Button(['self.state = \'play\''],['返回游戏'], rect=(0.55,0.9,0.2,0.05), shade_time_max=0),
             Button(['self.reset();self.state = \'play\''],['新局'], rect=(0.25,0.9,0.2,0.05), shade_time_max=0),
             Button(['self.ai_think_time = 1', 'self.ai_think_time = 40', 'self.ai_think_time = 500', 'self.ai_think_time = 1000'],
                    ['人机:新手', '人机:入门', '人机:高级', '人机:大师']),#!
             Button(['self.hint_think_time = 500', 'self.hint_think_time = 1000'],
                    ['提示:高级', '提示:大师'],n=1),
             Button(['self.save()'],['保存'], shade_time_max=0),
             Button(['self.load()'],['载入'], shade_time_max=0),
             Button(['self.active_menu = engine_setting; self.read_ini()'],['更改规则'], shade_time_max=0),
             Button(['self.show_ai_bar=False', 'self.show_ai_bar=True'],
                    ['评分条关闭', '评分条打开'])
             ]
sort_menu_elements_rect(main_menu)

engine_setting = [
             Button(['self.apply_engine_change()'],['重新开始'], rect=(0.25,0.9,0.2,0.05)),
             Button(['self.active_menu = main_menu;self.read_ini();self.config_setting_operations()'],['取消更改'], rect=(0.55,0.9,0.2,0.05), shade_time_max=0),
             Button(['self.set_chn_promotion(False);self.promotion_allowed = False',
                     'self.set_chn_promotion(True);self.promotion_allowed = True'],
                    ['不允许中国象棋升变', '允许中国象棋升变']),
             Button(['self.set_king_mobility(False)','self.set_king_mobility(True)'],
                    ['不允许国王进入九宫', '允许国王进入九宫']),
             Button(['self.set_queen_can_move_infinite(False)','self.set_queen_can_move_infinite(True)'],
                    ['皇后移动长度不能大于三', '允许皇后长距离移动'])
                ]
sort_menu_elements_rect(engine_setting,1)

# noinspection SpellCheckingInspection
allowed_pro ='''; promo
pawnTypes = po
promotionPawnTypesWhite = o
promotionPieceTypesWhite = jcaxsm
promotionRegionWhite = *9
; promo'''
not_allowed_pro='; promo\npawnTypes = p\n; promo'''

not_allow_king_in_palace = '''; king_mov
mobilityRegionBlackKing  = a1 a2 a3 b1 b2 b3 c1 c2 c3 g1 g2 g3 h1 h2 h3 i1 i2 i3 *4 *5 *6 *7 *8 *9
; king_mov'''
allow_king_in_palace = '; king_mov\n; king_mov'

not_allow_queen_infinite = '; queen_mov\ncustomPiece7 = q:R3B3\n; queen_mov'
allow_queen_infinite = '; queen_mov\nqueen = q\n; queen_mov'

class Game:
    def __init__(self):
        self.board = beach.Beach()
        self.rater = rate.RatingSystem()
        self.rater.refresh_fen(self.board.fen)
        self.rater.thread_rate_begin()
        self.last_score = 0
        self.red_rate = 0.5
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
        self.active_menu = main_menu
        self.ai_think_time = 1
        self.hint_think_time = 1000
        self.show_ai_bar = False
        try:
            self.load_user_setting()
        except Exception as e:
            logger.warning(f"加载用户设置失败: {e}")
        # 引擎ini相关
        self.ini_content = None
        self.promotion_allowed = None
        self.read_ini()
        self.config_setting_operations()
        with open('engine\\config.ini', 'r', encoding='UTF-8') as f:
            self.config_ini_content = f.read()

    def reset_special_pieces_show(self):
        self.highlight_paths = []
        self.last_choice_piece = (-1,-1)

    def handle_input_p(self, display_p ,w, h, mx, my, c, p):
        if self.state == 'play':
            if display_p is not None:
                if 0 <= display_p <= 80:
                    self.handle_board_event(display_p if not self.board_is_flipped else 80 - display_p)
                elif 81 <= display_p:
                    self.reset_special_pieces_show()
                    self.handle_game_UIs(display_p)
                    self.adjust_ai(display_p)
            self.renew_score()
            self.process_animation()
            self.process_steady_pieces()
            self.process_UIs(p)
        elif self.state == 'wait' or self.state == 'waits':
            if display_p is not None:
                self.adjust_ai(display_p)
            self.renew_score()
            self.process_animation()
            self.process_steady_pieces()
            self.process_UIs(p)
        elif self.state == 'promotion':
            if display_p is not None:
                if self.board_is_flipped:
                    self.handle_promotion_select(80-display_p)
                else:
                    self.handle_promotion_select(display_p)
        elif self.state == 'setting':
            for elem in self.active_menu:
                elem.tick_update(c,p)
            if c:
                if w > h:
                    ry = my / h
                    rx = (mx - (w - h) / 2) / h
                else:
                    rx = mx / w
                    ry = (my - (h - w) / 2) / w
                self.handle_menu_click(rx, ry)
        elif self.state == 'setting_wait':
            for elem in self.active_menu:
                elem.tick_update(c, p)

        # 返回全部显示组件
        return (self.board_is_flipped, self.steady_pieces, self. piece_animations,
                self.last_choice_piece, self.highlight_paths, self.UIs, self.pressed_button,
                self.active_menu if self.state == 'setting' or self.state == 'setting_wait' else None,
                self.red_rate if self.show_ai_bar else -1)

    def renew_score(self):
        new_score = self.rater.score
        if self.last_score != new_score:
            self.last_score = new_score
            if new_score[0] == 'score':
                rat = max(0.05,min(0.95,0.5+new_score[1]/7000))
            elif new_score[0] == 'mate':
                if new_score[1] < 0:
                    rat = 0
                elif new_score[1] > 0:
                    rat = 1
                else:
                    if ' w ' in self.board.fen:
                        rat = 0
                    else:
                        rat = 1
            else:
                rat = self.red_rate
            self.red_rate = rat


    def handle_menu_click(self, rx, ry):
        # element_button[type,rect,img_source,end_command,n,commands]
        for elem in self.active_menu:
            if elem.is_clicked(rx, ry):
                command = elem.active()
                break
        else:
            command = None
        if command is not None:
            exec(command)

    def handle_promotion_select(self, p):
        tp = beach.fsf2beach(self.promotion_move[2:4])
        z = None
        if tp // 9 == 8:
            if p == tp:
                z = 'q'
            elif p == tp -9:
                z = 'n'
            elif p == tp -18:
                z = 'b'
            elif p == tp - 27:
                z = 'r'
        else:
            if p == tp:
                z = 'j'
            elif p == tp +9:
                z = 'c'
            elif p == tp +18:
                z = 'm'
            elif p == tp +27:
                z = 'x'
            elif p == tp +36:
                z = 's'
            elif p == tp +45:
                z = 'a'
        if z is not None:
            self.apply_move(self.promotion_move+z)

    def adjust_ai(self, p):
        if self.board_is_flipped:
            p = 170 - p
        if p == 81:
            self.ai_int ^= 1
            if self.ai_int and ' b ' in self.board.fen and self.state == 'play':
                self.auto_move(tt = self.ai_think_time)
        elif p == 89:
            self.ai_chn ^= 1
            if self.ai_chn and ' w ' in self.board.fen and self.state == 'play':
                self.auto_move(tt = self.ai_think_time)

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
            self.auto_move(tt = self.hint_think_time)
        elif p == 92:
            self.state = 'setting'

    def do_checkmate_animation(self, delay = 10):
        delay //= cns.ANIM_SPEED
        if ' w ' in self.board.fen:
            p = self.board.beach.index(6, 56)
            self.piece_animations.append((p, p, 0, 20//cns.ANIM_SPEED+delay, 6))
        else:
            p = self.board.beach.index(12)
            self.piece_animations.append((p, p, 0, 20//cns.ANIM_SPEED+delay, 12))
        self.piece_animations.append((-2, p, -delay, 20//cns.ANIM_SPEED, 15))

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
        for st, end_pos, _, _, _ in self.piece_animations:
            pieces_to_hide.add(int(end_pos+0.5))
            pieces_to_hide.add(int(st + 0.5))
        self.steady_pieces.clear()
        p = 0
        for typ in self.board:
            if typ >= 0 and p not in pieces_to_hide:
                self.steady_pieces.add((p, typ))
            p += 1

    #这个顺便处理UI按钮点击效果
    def process_UIs(self, pressed):
        self.UIs.clear()
        if self.state == 'play' or self.state == 'waits':
            self.UIs.add((91, '!'))
            self.UIs.add((96, '&'))
            self.UIs.add((98, 'undo'))
            self.UIs.add((99, 'gret'))
            self.UIs.add((92, 'setting'))
        if self.state == 'play' or self.state == 'wait' or self.state == 'waits':
            if self.board_is_flipped:
                self.UIs.add((89, 'r' if self.ai_int else 'h'))
                self.UIs.add((81, 'r' if self.ai_chn else 'h'))
            else:
                self.UIs.add((81, 'r' if self.ai_int else 'h'))
                self.UIs.add((89, 'r' if self.ai_chn else 'h'))
        if self.pressed_button[-1] > 0 and not pressed:
            self.pressed_button[-1] = max(0, self.pressed_button[-1] - cns.ANIM_SPEED)

    def _am(self, d=False, tt = 1000):
        if d:
            self.gret()
        if self.board.get_pms()[1]:
            self.state = 'play'
            return
        self.state = 'wait'
        try:
            move = self.board.get_best_move(think_time=tt)
        except RuntimeError:
            logger.warning("Runtime error during AI move calculation")
            return
        self.apply_move(move)

    def auto_move(self, do_gret=False, tt = 1000):
        Thread(target=self._am,args=(do_gret, tt,)).start()

    def apply_move(self, move):
        if len(self.moves) != self.move_step:
            self.moves = self.moves[:self.move_step]
        self.moves.append(move)
        if ((self.ai_chn and ' b ' in self.board.fen) or
            (self.ai_int and ' w ' in self.board.fen)):
            self.auto_move(True, tt = self.ai_think_time)
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
            #中国象棋的升变
            elif self.promotion_allowed == True and self.board[fp] == 7 and tp//9 == 0:
                self.state = 'promotion'
                self.highlight_paths.clear()
                self.promotion_move = move
                self.piece_animations.append((-1, tp, -1, 1, 14))
                self.piece_animations.append((-1, tp + 9, -1, 1, 14))
                self.piece_animations.append((-1, tp + 18, -1, 1, 14))
                self.piece_animations.append((-1, tp + 27, -1, 1, 14))
                self.piece_animations.append((-1, tp + 36, -1, 1, 14))
                self.piece_animations.append((-1, tp + 45, -1, 1, 14))
                self.piece_animations.append((-1, tp, -1, 1, 0))
                self.piece_animations.append((-1, tp + 9, -1, 1, 1))
                self.piece_animations.append((-1, tp + 18, -1, 1, 2))
                self.piece_animations.append((-1, tp + 27, -1, 1, 3))
                self.piece_animations.append((-1, tp + 36, -1, 1, 4))
                self.piece_animations.append((-1, tp + 45, -1, 1, 5))
                return
            self.reset_special_pieces_show()
            self.apply_move(move)
            return
        # 如果没选子或选了一样的，重置
        if beach_p is None or beach_p == self.last_choice_piece[0]:
            self.reset_special_pieces_show()
            return
        self.highlight_paths, game_end = self.board.get_pms(beach_p)
        # 将杀了
        if game_end:
            self.reset_special_pieces_show()
            self.do_checkmate_animation(delay=0)
            return
        # 如果子走不动路，重置
        if not self.highlight_paths:
            self.reset_special_pieces_show()
            p, typ = beach_p, self.board[beach_p]
            if typ >= 0:
                if self.board_is_flipped:
                    self.piece_animations.append((p - 0.15, p, 0, 3//cns.ANIM_SPEED, typ))
                    self.piece_animations.append((p, p - 0.15, -3, 3//cns.ANIM_SPEED, typ))
                else:
                    self.piece_animations.append((p + 0.15, p, 0, 3//cns.ANIM_SPEED, typ))
                    self.piece_animations.append((p, p + 0.15, -3, 3//cns.ANIM_SPEED, typ))
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
                self.piece_animations.append((tp, tp, 0, 10//cns.ANIM_SPEED,eat_typ))
            piece_typ = self.board[fp]
            if move == 'd9b9' and piece_typ == 12:
                self.piece_animations.append((2, 2, 0, 10//cns.ANIM_SPEED, 8))
                self.piece_animations.append((2, 0, -10//cns.ANIM_SPEED, 10//cns.ANIM_SPEED, 8))
            if move == 'd9f9' and piece_typ == 12:
                self.piece_animations.append((4, 4, 0, 10//cns.ANIM_SPEED, 8))
                self.piece_animations.append((4, 8, -10//cns.ANIM_SPEED, 10//cns.ANIM_SPEED, 8))
            if piece_typ >= 0:
                self.piece_animations.append((tp, fp, 0, 10//cns.ANIM_SPEED, piece_typ))
            self.rater.refresh_fen(self.board.fen)

    def gret(self):
        if self.move_step < len(self.moves):
            self.reset_special_pieces_show()
            move = self.moves[self.move_step]
            fp = beach.fsf2beach(move[:2])
            tp = beach.fsf2beach(move[2:4])
            eat_typ = self.board[tp]
            if eat_typ >= 0:
                self.piece_animations.append((tp, tp, 0, 10//cns.ANIM_SPEED, eat_typ))
            piece_typ = self.board[fp]
            if move == 'd9b9' and piece_typ == 12:
                self.piece_animations.append((0, 0, 0, 10//cns.ANIM_SPEED, 8))
                self.piece_animations.append((0, 2, -10//cns.ANIM_SPEED, 10//cns.ANIM_SPEED, 8))
            if move == 'd9f9' and piece_typ == 12:
                self.piece_animations.append((8, 8, 0, 10//cns.ANIM_SPEED, 8))
                self.piece_animations.append((8, 4, -10//cns.ANIM_SPEED, 10//cns.ANIM_SPEED, 8))
            if piece_typ >= 0:
                self.piece_animations.append((fp, tp, 0, 10//cns.ANIM_SPEED, piece_typ))
            self.move_step += 1
            self.board.moves_reset(self.moves[:self.move_step])
            if self.board.get_pms()[1]:
                self.do_checkmate_animation()
            self.rater.refresh_fen(self.board.fen)

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
        self.save_all_user_setting()
        self.board.suicide()
        self.rater.quit()

    def load(self):
        file_path = filedialog.askopenfilename(
            defaultextension=".binggo",
            initialdir='saves\\',
            filetypes=[("BingGo存档", "*.binggo")]
        )
        if file_path:
            with open(file_path, 'r', encoding='ascii') as file:
                content = file.read()
            self.state = 'setting_wait'
            try:
                rule_str, fen, moves = content.strip().split('|')
                new_ini = self.get_ini_by_rule_str(rule_str)
                with open('engine\\binggo.ini', 'w', encoding='UTF-8') as f:
                    f.write(new_ini)
                self.config_setting_operations()
                self.board.reset(fen)
                _m = moves.split(' ')
                self.moves = _m if _m != [''] else []
                self.board.reboot_engine()
                self.rater.reboot()
                self.board.moves_reset(self.moves)
                self.board.moves_reset([])
            except Exception as e:
                logger.error(f'存档文件损坏: {e}')
                self.board.reset(force=True)
                self.moves = []
                self.state = 'setting'
                return
            self.state = 'play'
            self.rater.refresh_fen(self.board.fen)
            self.move_step = 0
            self.ai_chn = False
            self.ai_int = False
            return

    def save(self):
        content = self.load_rule_str_from_ini() + '|' + self.board.initial_fen + '|' + ' '.join(self.moves)
        file_path = filedialog.asksaveasfilename(
            defaultextension=".binggo",
            initialdir='saves\\',
            filetypes=[("BingGo存档", "*.binggo")]
        )
        if file_path:
            with open(file_path, 'w', encoding='ascii') as file:
                file.write(content)

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

        self.moves = []
        self.rater.refresh_fen(self.board.fen)
        self.move_step = 0
        self.ai_chn = False
        self.ai_int = False
        self.state = 'play'

    def _aec(self):
        self.state = 'setting_wait'
        with open('engine\\binggo.ini', 'w', encoding='UTF-8') as f:
            f.write(self.ini_content)
        self.board.reboot_engine()
        self.rater.reboot()
        self.reset()
        self.active_menu = main_menu

    def apply_engine_change(self):
        Thread(target=self._aec).start()

    def read_ini(self):
        with open('engine\\binggo.ini', 'r', encoding='UTF-8') as f:
            self.ini_content = f.read()

    def config_setting_operations(self):
        with open('engine\\binggo.ini', 'r', encoding='UTF-8') as f:
            content = f.read()
            if not_allowed_pro in content:
                self.promotion_allowed = False
                engine_setting[2].n = 0
            else:
                self.promotion_allowed = True
                engine_setting[2].n = 1
            if not_allow_king_in_palace in content:
                engine_setting[3].n = 0
            else:
                engine_setting[3].n = 1
            if not_allow_queen_infinite in content:
                engine_setting[4].n = 0
            else:
                engine_setting[4].n = 1

    def set_chn_promotion(self, is_allowed):
        if is_allowed:
            old_str = not_allowed_pro
            new_str = allowed_pro
        else:
            old_str = allowed_pro
            new_str = not_allowed_pro
        self.ini_content = self.ini_content.replace(old_str, new_str)

    def set_king_mobility(self, is_allowed):
        if is_allowed:
            old_str = not_allow_king_in_palace
            new_str = allow_king_in_palace
        else:
            old_str = allow_king_in_palace
            new_str = not_allow_king_in_palace
        self.ini_content = self.ini_content.replace(old_str, new_str)

    def set_queen_can_move_infinite(self, is_allowed):
        if is_allowed:
            old_str = not_allow_queen_infinite
            new_str = allow_queen_infinite
        else:
            old_str = allow_queen_infinite
            new_str = not_allow_queen_infinite
        self.ini_content = self.ini_content.replace(old_str, new_str)

    def load_rule_str_from_ini(self):
        rule = ''
        self.read_ini()
        rule += '1' if allowed_pro in self.ini_content else '0'
        rule += '1' if allow_king_in_palace in self.ini_content else '0'
        rule += '1' if allow_queen_infinite in self.ini_content else '0'
        return rule

    def get_ini_by_rule_str(self, rule_str):
        _i = self.config_ini_content
        logger.info(rule_str)
        if rule_str[0] == '1':
            _i = _i.replace(not_allowed_pro, allowed_pro)
        if rule_str[1] == '1':
            _i = _i.replace(not_allow_king_in_palace, allow_king_in_palace)
        if rule_str[2] == '1':
            _i = _i.replace(not_allow_queen_infinite, allow_queen_infinite)
        return _i

    def save_all_user_setting(self):
        content = ''
        content += str(self.ai_think_time)+'|'
        content += str(self.hint_think_time)+'|'
        content += ('1' if self.show_ai_bar else '0')+'|'
        content += ('1' if self.board_is_flipped else '0')
        if not os.path.exists('userdata'):
            os.mkdir('userdata')
        with open('userdata\\rule_setting.ini','w',encoding='ascii') as f:
            f.write(content)

    def load_user_setting(self):
        with open('userdata\\rule_setting.ini','r',encoding='ascii') as f:
            content = f.read()
        ai_tt, ht_tt, show_bar, flip = content.split('|')
        if ai_tt == '40':
            main_menu[2].n = 1
            self.ai_think_time = 40
        elif ai_tt == '500':
            main_menu[2].n = 2
            self.ai_think_time = 500
        elif ai_tt == '1000':
            main_menu[2].n = 3
            self.ai_think_time = 1000
        else:
            main_menu[2].n = 0
            self.ai_think_time = 1
        if ht_tt == '500':
            main_menu[3].n = 0
            self.hint_think_time = 500
        else:
            main_menu[3].n = 1
            self.hint_think_time = 1000
        if show_bar == '1':
            main_menu[7].n = 1
            self.show_ai_bar = True
        if flip == '1':
            self.board_is_flipped = True