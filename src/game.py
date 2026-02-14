import logging
import os
import json
import time
import webbrowser  # noinspection
from threading import Thread
from tkinter import filedialog

from src import gists as gts
from src import beach
from src import rate
from src import consts
from src import variable as var
from src.settings import BaseButton, PressBtn, SettingBtn, Menu
from src.settings import EngineStg
from src.LogMsgboxManager import MsgLog

logger = logging.getLogger(__name__)
msglog = MsgLog(logger)


main_menu = Menu([
    PressBtn("返回游戏", "self.state = 'play'", rect=(0.55,0.9,0.2,0.05), shade_time_max=0),
    PressBtn("新局", "self.reset(); self.state = 'play'", rect=(0.25,0.9,0.2,0.05), shade_time_max=0),
    SettingBtn("人机", name_explicit=True, cmds={
        '新手': 'self.ai_think_time = 1',
        '入门': 'self.ai_think_time = 30',
        '高级': 'self.ai_think_time = 500',
        '大师': 'self.ai_think_time = 1000',
        '专家': 'self.ai_think_time = 5000',
    }, n=1),
    SettingBtn("提示", name_explicit=True, cmds={
        '大师': 'self.ai_think_time = 1000',
        '专家': 'self.ai_think_time = 5000',
    }),
    PressBtn("保存", "self.save()", shade_time_max=0),
    PressBtn("载入", "self.load()", shade_time_max=0),
    PressBtn("更改规则", "self.active_menu = engine_setting; self.eng_stg.load_from_default()", shade_time_max=0),
    SettingBtn("评分条", cmds={
        '评分条关闭': 'self.show_ai_bar = False',
        '评分条打开': 'self.show_ai_bar = True'
    }),
    PressBtn("create", "self.create_room(self.eng_stg.export_to_json())"),
    PressBtn("join", "self.join_room()"),
    PressBtn("帮助", "webbrowser.open('https://gitee.com/windbell0711/BingGo2/blob/main/README.md')",
             rect=(0.85,0.8,0.1,0.05), shade_time_max=0),
    PressBtn("赞赏", "webbrowser.open('https://gitee.com/windbell0711/BingGo2/blob/main/readme/support.md')",
             rect=(0.85,0.9,0.1,0.05), shade_time_max=0),
])

engine_setting = Menu([
    PressBtn(name="重新开始", cmd='self.apply_engine_change()', rect=(0.25,0.9,0.2,0.05)),
    PressBtn(name="取消更改", cmd='self.active_menu = main_menu; self.eng_stg.load_from_default(); '
                                 'self.sync_eng_stg_display()', rect=(0.55,0.9,0.2,0.05), shade_time_max=0),
    # 如果bug了可以试一下下面两行替换
    # SettingBtn(name:="重新开始", cmds={name: 'self.apply_engine_change()'}, rect=(0.25,0.9,0.2,0.05)),
    # SettingBtn(name:="取消更改", cmds={name: 'self.active_menu = main_menu;self.load_from_default();self.config_setting_operations()'}, rect=(0.55,0.9,0.2,0.05), shade_time_max=0),
    SettingBtn("white_promo", cmds={
        '不允许中国象棋升变': 'self.set_eng_stg("white_promo", 0)',
        '允许中国象棋升变':   'self.set_eng_stg("white_promo", 1)',
    }),
    SettingBtn("king_enter_palace", cmds={
        '不允许国王进入九宫': 'self.set_eng_stg("king_enter_palace", 0)',
        '允许国王进入九宫':   'self.set_eng_stg("king_enter_palace", 1)',
    }),
    SettingBtn("queen_inf", cmds={
        '皇后移动长度不能大于三':      'self.set_eng_stg("queen_inf", 0)',
        '皇后可沿直线或斜线无限移动':   'self.set_eng_stg("queen_inf", 1)',
        # '自定义皇后走法(实验)':        'self.set_eng_stg("queen_inf", 2)',
    }),
    PressBtn("更多规则设置...(实验)", cmd='self.open_chess_piece_setup()', rect=(0.25,0.8,0.5,0.05)),  # 添加新的按钮
], element_per_line_max=1)


class Game:
    def __init__(self):
        # 引擎ini相关
        self.eng_stg = EngineStg()
        self.eng_stg.write_to_ini()
        self.sync_eng_stg_display()
        #棋盘和评分相关
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
        # Gist相关
        self.gist = gts.Messager(gts.ACCESS_TOKEN, str(time.time()))
        self.on_get = False

    @property
    def w_promotion_allowed(self):
        return self.eng_stg.switches['white_promo']

    def reset_special_pieces_show(self):
        self.highlight_paths = []
        self.last_choice_piece = (-1,-1)

    def handle_input_p(self, display_p , w, h, mx, my, c, p):
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
        elif self.state == 'setting_wait':
            for elem in self.active_menu:
                elem.tick_update(c, p)
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
        elif self.state == 'multiplayer':
            if display_p is not None:
                if 0 <= display_p <= 80:
                    move = self.ana_mov(display_p if not self.board_is_flipped else 80 - display_p)
                    if move is not None:
                        self.apply_mlt_move(move)
                elif 81 <= display_p:
                    pass
            self.process_animation()
            self.process_steady_pieces()
        elif self.state == 'promotions':
            if display_p is not None:
                if self.board_is_flipped:
                    self.handle_mlt_promotion(80-display_p)
                else:
                    self.handle_mlt_promotion(display_p)
            self.process_steady_pieces()
        elif self.state == 'mltwait':
            self.process_animation()
            if int(time.time())%2 == 0 and not self.on_get:
                Thread(target=self._gm).start()
            self.process_animation()
            self.process_steady_pieces()
        if self.state in ('multiplayer', 'promotions', 'mltwait'):
            if display_p == 96:
                self.board_is_flipped ^= 1
                self.pressed_button = [96, 10]
            elif display_p == 95:
                if msglog.askyesno("确认退出", "真的要退出联机模式吗？对方可能正在期待你的下一步棋 qwq"):
                    logger.info("用户退出联机模式")
                    self.exit_mlt()
            self.process_UIs(p)

        # 返回全部显示组件
        return (self.board_is_flipped, self.steady_pieces, self. piece_animations,
                self.last_choice_piece, self.highlight_paths, self.UIs, self.pressed_button,
                self.active_menu if self.state == 'setting' or self.state == 'setting_wait' else None,
                self.red_rate if self.show_ai_bar else -1)

    def _gm(self):
        self.on_get = True
        _move = self.gist.get()
        if _move:
            print(_move)
            self.moves.append(_move)
            self.gret()
            self.state = 'multiplayer'
            _, game_end = self.board.get_pms()
            if game_end:
                self.state = 'play'
        self.on_get = False

    def _sm(self, _message):
        if self.gist.send(_message):
            if self.state == 'multiplayer':
                self.state = 'mltwait'
            return
        if msglog.askyesno("发送意外失败\n点击是：尝试重新发送\n点击否：结束对局"):
            if self.gist.send(_message):
                if self.state == 'multiplayer':
                    self.state = 'mltwait'
                return
        self.exit_mlt()
        msglog.error(f"消息{_message}发送失败，已退出联机模式")


    def join_room(self, *args, **kwargs):
        try:
            ret = self.gist.进去了哦(*args, **kwargs)
            assert ret
            self.eng_stg.load_from_json(ret)
        except AssertionError: return
        except Exception:
            msglog.error("加入房间失败")
            return
        self.eng_stg.write_to_ini()
        msglog.info(self.eng_stg.export_to_text() + "\n您是先手，游戏即将开始...", title='当前游戏规则')
        self.reset()
        fen = self.eng_stg.redeclares.get('startFen') or var.INIT_FEN_DEFAULT
        self.board.reset(fen=fen)
        self.board.reboot_engine()
        self.state = 'multiplayer'

    def create_room(self, *args, **kwargs):
        match self.gist.开大床房(*args, **kwargs):
            case None:
                msglog.info('房间名未输入，无法启动联机。')
            case False:
                msglog.error("创建房间失败")
            case True:
                msglog.info(self.eng_stg.export_to_text(), title='当前游戏规则')
                self.reset()
                fen = self.eng_stg.redeclares.get('startFen') or var.INIT_FEN_DEFAULT
                self.board.reset(fen=fen)
                self.board.reboot_engine()
                self.state = 'mltwait'

    def exit_mlt(self):
        self.state = 'play'

    def handle_mlt_promotion(self, p):
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
            self.apply_mlt_move(self.promotion_move+z)

    def apply_mlt_move(self, move):
        if len(self.moves) != self.move_step:
            self.moves = self.moves[:self.move_step]
        self.moves.append(move)
        self.gret()
        _, game_end = self.board.get_pms()
        if game_end:
            self.state = 'play'
        Thread(target=self._sm, args=(move,)).start()

    def ana_mov(self, beach_p):
        # 是一步走子
        if beach_p in self.highlight_paths:
            # 添加动画 并且更新 beach 状态
            fp = self.last_choice_piece[0]
            move = beach.beach2fsf(fp) + beach.beach2fsf(beach_p)
            tp = beach_p
            # 如果走子是升变
            if self.board[fp] == 13 and tp // 9 == 8:
                self.state = 'promotions'
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
                return None
            # 中国象棋的升变
            elif self.w_promotion_allowed == True and self.board[fp] == 7 and tp // 9 == 0:
                self.state = 'promotions'
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
                return None
            self.reset_special_pieces_show()
            return move
        # 如果没选子或选了一样的，重置
        if beach_p is None or beach_p == self.last_choice_piece[0]:
            self.reset_special_pieces_show()
            return None
        self.highlight_paths, game_end = self.board.get_pms(beach_p)
        # 将杀了
        if game_end:
            self.reset_special_pieces_show()
            self.do_checkmate_animation(delay=0)
            return None
        # 如果子走不动路，重置
        if not self.highlight_paths:
            self.reset_special_pieces_show()
            p, typ = beach_p, self.board[beach_p]
            if typ >= 0:
                if self.board_is_flipped:
                    self.piece_animations.append((p - 0.15, p, 0, 3 // var.anim_speed, typ))
                    self.piece_animations.append((p, p - 0.15, -3, 3 // var.anim_speed, typ))
                else:
                    self.piece_animations.append((p + 0.15, p, 0, 3 // var.anim_speed, typ))
                    self.piece_animations.append((p, p + 0.15, -3, 3 // var.anim_speed, typ))
            return None
        self.last_choice_piece = (beach_p, self.board[beach_p])

    def renew_score(self):
        new_score = self.rater.score
        if new_score[1] is None:
            logger.warning('无评分数据')
            return
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
                command = elem.press()
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
        delay //= var.anim_speed
        if ' w ' in self.board.fen:
            p = self.board.beach.index(6, 56)
            self.piece_animations.append((p, p, 0, 20//var.anim_speed+delay, 6))
        else:
            p = self.board.beach.index(12)
            self.piece_animations.append((p, p, 0, 20//var.anim_speed+delay, 12))
        self.piece_animations.append((-2, p, -delay, 20//var.anim_speed, 15))

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
        if self.state in ('play', 'waits'):
            self.UIs.add((91, '!'))
            self.UIs.add((96, '&'))
            self.UIs.add((98, 'undo'))
            self.UIs.add((99, 'gret'))
            self.UIs.add((92, 'setting'))
        if self.state in ('multiplayer', 'mltwait'):
            self.UIs.add((96, '&'))
            self.UIs.add((95, 'x'))
        if self.state in ('play', 'waits', 'wait'):
            if self.board_is_flipped:
                self.UIs.add((89, 'r' if self.ai_int else 'h'))
                self.UIs.add((81, 'r' if self.ai_chn else 'h'))
            else:
                self.UIs.add((81, 'r' if self.ai_int else 'h'))
                self.UIs.add((89, 'r' if self.ai_chn else 'h'))
        if self.pressed_button[-1] > 0 and not pressed:
            self.pressed_button[-1] = max(0, self.pressed_button[-1] - var.anim_speed)

    def _am(self, d=False, tt = 1000):
        if d:
            self.gret()
        if self.board.get_pms()[1]:
            self.state = 'play'
            return
        self.state = 'wait'
        try:
            move = self.board.get_best_move(think_time=tt)
        except RuntimeError as e:
            logger.error("Runtime error during AI move calculation: " + str(e))
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
    def handle_board_event(self, beach_p):
        # 是一步走子
        if beach_p in self.highlight_paths:
            # 添加动画 并且更新 beach 状态
            fp = self.last_choice_piece[0]
            move = beach.beach2fsf(fp) + beach.beach2fsf(beach_p)
            tp = beach_p
            # 如果走子是升变
            if self.board[fp] == 13 and tp // 9 == 8:
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
            elif self.w_promotion_allowed == True and self.board[fp] == 7 and tp // 9 == 0:
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
                    self.piece_animations.append((p - 0.15, p, 0, 3 // var.anim_speed, typ))
                    self.piece_animations.append((p, p - 0.15, -3, 3 // var.anim_speed, typ))
                else:
                    self.piece_animations.append((p + 0.15, p, 0, 3 // var.anim_speed, typ))
                    self.piece_animations.append((p, p + 0.15, -3, 3 // var.anim_speed, typ))
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
                self.piece_animations.append((tp, tp, 0, 10//var.anim_speed,eat_typ))
            piece_typ = self.board[fp]
            if move == 'd9b9' and piece_typ == 12:
                self.piece_animations.append((2, 2, 0, 10//var.anim_speed, 8))
                self.piece_animations.append((2, 0, -10//var.anim_speed, 10//var.anim_speed, 8))
            if move == 'd9f9' and piece_typ == 12:
                self.piece_animations.append((4, 4, 0, 10//var.anim_speed, 8))
                self.piece_animations.append((4, 8, -10//var.anim_speed, 10//var.anim_speed, 8))
            if piece_typ >= 0:
                self.piece_animations.append((tp, fp, 0, 10//var.anim_speed, piece_typ))
            self.rater.refresh_fen(self.board.fen)

    def gret(self):
        if self.move_step < len(self.moves):
            self.reset_special_pieces_show()
            move = self.moves[self.move_step]
            fp = beach.fsf2beach(move[:2])
            tp = beach.fsf2beach(move[2:4])
            eat_typ = self.board[tp]
            if eat_typ >= 0:
                self.piece_animations.append((tp, tp, 0, 10//var.anim_speed, eat_typ))
            piece_typ = self.board[fp]
            if move == 'd9b9' and piece_typ == 12:
                self.piece_animations.append((0, 0, 0, 10//var.anim_speed, 8))
                self.piece_animations.append((0, 2, -10//var.anim_speed, 10//var.anim_speed, 8))
            if move == 'd9f9' and piece_typ == 12:
                self.piece_animations.append((8, 8, 0, 10//var.anim_speed, 8))
                self.piece_animations.append((8, 4, -10//var.anim_speed, 10//var.anim_speed, 8))
            if piece_typ >= 0:
                self.piece_animations.append((fp, tp, 0, 10//var.anim_speed, piece_typ))
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
        self.eng_stg.save_to_json()
        self.board.suicide()
        self.rater.quit()

    def load(self):
        file_path = filedialog.askopenfilename(
            defaultextension=".binggo",
            initialdir='saves\\',
            filetypes=[("BingGo存档", "*.binggo")]
        )
        if file_path:
            with open(file_path, 'r', encoding='ascii') as f:
                content: str = f.read()
            self.state = 'setting_wait'
            try:
                self.eng_stg.load_from_json(content)
                self.eng_stg.write_to_ini()
                self.sync_eng_stg_display()
                dumped: dict = json.loads(content)
                self.board.reset(dumped["start_fen"])
                self.moves = dumped["moves"].split(' ')
                if self.moves == [""]:  self.moves = []
                self.board.reboot_engine()
                self.rater.reboot()
                self.board.moves_reset(self.moves)
                self.board.moves_reset([])
            except Exception as e:
                msglog.error(f'存档文件损坏，请检查存档文件。\n{e}')
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
        content = json.dumps({
            'version': consts.VERSION,
            'start_fen': self.board.initial_fen,
            'moves': ' '.join(self.moves),
            'switches': self.eng_stg.switches,
        })
        if not os.path.exists('saves'):
            os.mkdir('saves')
        file_path = filedialog.asksaveasfilename(
            defaultextension=".binggo",
            initialdir='saves\\',
            filetypes=[("BingGo存档", "*.binggo")]
        )
        if file_path:
            with open(file_path, 'w', encoding='ascii') as file:
                file.write(content)
        else:
            logger.warning("保存失败：" + ' '.join(self.moves))

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

    def open_chess_piece_setup(self):
        """打开棋子走法设置器"""
        import tkinter as tk
        from src import ChessPieceSetup as cps

        root = tk.Tk()
        app = cps.ChessPieceSetup(root, self.eng_stg.redeclares)
        root.mainloop()

        # 处理结果
        match app.confirm:
            case True:
                # 用户确认更改，获取结果数据
                result_data = {k: v.get() for k, (v, _, _) in app.entries.items() if app.check_vars[k].get()}
                self.eng_stg.redeclares = result_data
                # 保存设置并应用
                self.eng_stg.save_to_json()

                # 应用引擎更改
                var.init_fen = result_data.get('startFen') or var.INIT_FEN_DEFAULT
                self.apply_engine_change()

                msglog.info("棋子走法设置已保存并应用！", title="成功")
            case False:
                # 用户取消
                msglog.info("设置未保存", title="取消")
            case _:
                msglog.error(f"{app.confirm =}")

        # 清理
        root.destroy()

    def _apply_engine_change(self):
        self.state = 'setting_wait'
        self.eng_stg.write_to_ini()
        self.board.reboot_engine()
        self.rater.reboot()

        # 检查是否有新的起始FEN需要应用
        new_start_fen = self.eng_stg.redeclares.get('startFen') if self.eng_stg.redeclares else None
        if new_start_fen:
            # 先重置棋盘到新FEN
            self.board.reset(fen=new_start_fen)
            self.rater.refresh_fen(new_start_fen)
            logger.info(f"棋盘FEN已更新为: {new_start_fen}")

        # 然后执行正常的reset逻辑
        self.reset()
        self.active_menu = main_menu

    def apply_engine_change(self):
        Thread(target=self._apply_engine_change).start()

    def set_eng_stg(self, target: str, option: int):  # pyright: ignore[reportUnusedFunction]
        self.eng_stg.switches[target] = option

    def sync_eng_stg_display(self):
        for k, v in self.eng_stg.switches.items():
            engine_setting[k].n = v # pyright: ignore[reportAttributeAccessIssue]

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

        ai_tt_d = {
            '1': 0,
            '30': 1,
            '500': 2,
            '1000': 3,
            '5000': 4,
        }
        if ai_tt in ai_tt_d:
            main_menu['人机'].n = ai_tt_d[ai_tt] # type: ignore
            self.ai_think_time = int(ai_tt)
        else:
            main_menu['人机'].n = 0 # type: ignore
            self.ai_think_time = 1

        ht_tt_d = {
            '1000': 0,
            '5000': 1,
        }
        if ht_tt in ht_tt_d:
            main_menu['提示'].n = ht_tt_d[ht_tt] # type: ignore
            self.hint_think_time = int(ht_tt)
        else:
            main_menu['提示'].n = 0 # type: ignore
            self.hint_think_time = 1000

        if show_bar == '1':
            main_menu['评分条'].n = 1 # type: ignore
            self.show_ai_bar = True
        else:
            main_menu['评分条'].n = 0 # type: ignore
            self.show_ai_bar = False

        if flip == '1':
            self.board_is_flipped = True
