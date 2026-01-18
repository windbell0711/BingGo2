import logging
import pygame
import sys, os
from tkinter import messagebox
import game as gm
import constant as cns

game = gm.Game()

logger = logging.getLogger(__name__)

# import ctypes
# if sys.platform == 'win32':
#     ctypes.windll.shcore.SetProcessDpiAwareness(1)

## TEMP!!!
n2c = {0:'将',1:'车',2:'马',3:'相',4:'士',5:'炮',6:'帅',7:'卒',8:'城',9:'教',10:'骑',11:'后',12:'王',13:'兵',14:'升变衬底',15:'将杀'}

FONT = 'fonts\\STLITI.TTF'
IMG_SOURCE = 'imgs'

def get_grid_position(x, y, square_x, square_y, square_size, grid_size=11):
    """计算鼠标点击在网格中的位置"""
    if not (square_x <= x < square_x + square_size and
            square_y <= y < square_y + square_size):
        return None, None
    relative_x = x - square_x
    relative_y = y - square_y
    cell_size = square_size / grid_size
    col = int(relative_x // cell_size)
    row = int(relative_y // cell_size)
    col = min(max(col, 0), grid_size - 1)
    row = min(max(row, 0), grid_size - 1)
    return row,col

def poses2beach_p(mouse_x, mouse_y, square_x, square_y, square_size):
    row, col = get_grid_position(mouse_x, mouse_y, square_x, square_y, square_size)
    if row is None or col is None:
        return None
    elif row not in (0,10) and col not in (0,10):
        return row * 9 + col - 10
    elif col == 0 and 0<row<10:
        return 80 + row
    elif col == 10 and 0<row<10:
        return 90 + row
    else:
        return None

def raise_size_of_rect(rect,side_length):
    return rect[0]*side_length,rect[1]*side_length,rect[2]*side_length,rect[3]*side_length


def play():
    pygame.init()
    try:
        with open('userdata\\display_setting.ini', 'r', encoding='ascii') as f:
            wh = f.read()
            width, height = wh.split('|')
            width = min(int(width), int(pygame.display.Info().current_w*0.8))
            height = min(int(height), int(pygame.display.Info().current_h*0.8))
    except Exception as e:
        logger.warning(f"读取显示设置失败，使用默认值: {e}")
        width, height = 900, 600
    square_size = min(width, height)
    square_x = (width - square_size) // 2
    square_y = (height - square_size) // 2
    cell_size = square_size / 11
    line_w = int(cell_size / 20)
    size_adjust_rate = 1
    MAX_SCREEN_PIXEL = 6000

    shade_count = 20
    bar_count = 0.5

    def adjust_max_pixel():
        nonlocal width, height, square_size, square_x, square_y, cell_size, size_adjust_rate
        if width > MAX_SCREEN_PIXEL or height > MAX_SCREEN_PIXEL:
            size_adjust_rate = min(MAX_SCREEN_PIXEL/width, MAX_SCREEN_PIXEL/height)
            width *= size_adjust_rate
            height *= size_adjust_rate
            square_size *= size_adjust_rate
            square_x *= size_adjust_rate
            square_y *= size_adjust_rate
            cell_size *= size_adjust_rate
        else:
            size_adjust_rate = 1

    adjust_max_pixel()

    flipped = False

    def reset_all_elements():
        nonlocal flipped, steady, animations, last_choice, paths, UIs, pressed
        flipped = False
        steady = set()
        animations = []
        last_choice = (-1,-1)
        paths = set()
        UIs = set()
        pressed = (-1,0)

    pygame.display.set_caption(cns.VERSION)
    clock = pygame.time.Clock()
    running = True

    # 贴图初始化
    img_loss = False
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.HWSURFACE | pygame.DOUBLEBUF)
    try:
        background_image_original = pygame.image.load(f'{IMG_SOURCE}/background.png').convert_alpha()
    except FileNotFoundError:
        background_image_original = pygame.Surface((1,1))
        img_loss = True
    try:
        board_image_original = pygame.image.load(f'{IMG_SOURCE}/board.png').convert_alpha()
    except FileNotFoundError:
        board_image_original = pygame.Surface((1, 1))
        img_loss = True
    try:
        bar_img_original = pygame.image.load(f'{IMG_SOURCE}/rate_bar.png').convert_alpha()
    except FileNotFoundError:
        bar_img_original = pygame.Surface((1, 1))
        img_loss = True

    all_piece_img_names = ['empty_piece','shadow','!','&','undo','gret','h','r',
                           'pressed','dot','empty_button','setting','empty_piece']

    name2piece_original_surface = {}
    name2piece_surface = {}
    for name in all_piece_img_names:
        try:
            name2piece_original_surface[name] = pygame.image.load(f'{IMG_SOURCE}/{name}.png').convert_alpha()
        except FileNotFoundError:
            name2piece_original_surface[name] = pygame.Surface((1, 1))
            img_loss = True
    try:
        font = pygame.font.Font(FONT, 500)
    except FileNotFoundError:
        messagebox.showerror('警告','字体文件缺失。你可以重新下载游戏解决此问题。')
        raise FileNotFoundError
    for typ, name in zip(n2c.keys(),n2c.values()):
        try:
            name2piece_original_surface[name] = pygame.image.load(f'{IMG_SOURCE}/{name}.png').convert_alpha()
        except FileNotFoundError:
            tmps = name2piece_original_surface['empty_piece'].copy()
            text_surface = font.render(n2c[typ], True, (20, 20, 20) if typ > 7 else (137, 57, 37))
            tmps.blit(text_surface,(110,110))
            name2piece_original_surface[name] = tmps
    background_and_board = board_image = background_image = pieces = small_screen = settings = bar_img = pygame.Surface((0,0))

    if img_loss:
        messagebox.showerror('警告', '缺失图片文件，游戏依旧可以运行。你可以重新下载游戏解决此问题。')
    del img_loss

    pygame.display.set_icon(name2piece_original_surface['帅'])

    def reset_all_imgs():
        nonlocal background_and_board, pieces, board_image, font, settings, bar_img,\
            background_and_board, background_image, small_screen, pieces, width, height
        small_screen = pygame.Surface((width, height), pygame.SRCALPHA)
        background_and_board = pygame.Surface((width, height), pygame.SRCALPHA)
        pieces = pygame.Surface((width, height), pygame.SRCALPHA)
        settings = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
        # 此处包含贴图大小调整
        if width > height * 1.5:
            background_image = pygame.transform.scale(background_image_original, (width, width / 1.5))
        else:
            background_image = pygame.transform.scale(background_image_original, (height * 1.5, height))
        board_image = pygame.transform.scale(board_image_original, (square_size, square_size))
        background_and_board.blit(background_image, (min((width - background_image.get_width()) / 2, 0),
                                                     min(height - background_image.get_height(), 0)))
        background_and_board.blit(board_image, (square_x, square_y))
        bar_img = pygame.transform.scale(bar_img_original, (cell_size*0.97, cell_size*7.35))

        for name_ in all_piece_img_names + list(n2c.values()):
            name2piece_surface[name_] = pygame.transform.scale(name2piece_original_surface[name_],
                                                              (cell_size, cell_size))
        font = pygame.font.Font(FONT, int(cell_size))

    reset_all_imgs()
    while running:
        number = None
        mouse_x, mouse_y = None, None
        clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                width, height = event.w, event.h
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE | pygame.HWSURFACE | pygame.DOUBLEBUF)
                square_size = min(width, height)
                square_x = (width - square_size) // 2
                square_y = (height - square_size) // 2
                cell_size = square_size / 11
                line_w = int(cell_size / 20)
                # MAX_SCREEN_PIXEL = screen.get_width() // 2
                adjust_max_pixel()
                reset_all_imgs()
                reset_all_elements()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    number = poses2beach_p(mouse_x*size_adjust_rate, mouse_y*size_adjust_rate, square_x, square_y, square_size)
                    clicked = True

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    number = 98
                elif event.key == pygame.K_DOWN:
                    number = 99
                # Ctrl + Shift + Insert
                elif event.key == pygame.K_INSERT and (pygame.key.get_mods() & pygame.KMOD_SHIFT) and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                    raise KeyboardInterrupt("'Ctrl + Shift + Insert' Pressed")

        pressed = pygame.mouse.get_pressed()[0]
        last_flip = flipped
        flipped, steady, animations, last_choice, paths, UIs, pressed, menu, score = (
            game.handle_input_p(number, width, height, mouse_x, mouse_y, clicked, pressed))

        if menu is not None:
            if shade_count < 10:
                shade_count = min(cns.ANIM_SPEED+shade_count, 10)

            settings.fill((0,0,0,0))
            screen.blit(background_image, (min((width - background_image.get_width()) / 2, 0),
                                           min(height - background_image.get_height(), 0)))
            for elem in menu:
                if type(elem) is gm.Button:
                    normal_size_rect = raise_size_of_rect(elem.rect,square_size)
                    if elem.shade_time_max != 0:
                        rat = elem.shade_time/elem.shade_time_max * 150
                        pygame.draw.rect(settings, (253 - rat, 251 - rat, 184 - rat, 160), normal_size_rect)
                    else:
                        pygame.draw.rect(settings, (253, 251, 184, 160), normal_size_rect)
                    pygame.draw.rect(settings,(30,30,30),normal_size_rect, line_w)
                    text_surface = font.render(elem.return_text(), True, (0,0,0))
                    _t = pygame.transform.scale(text_surface, (normal_size_rect[3]/text_surface.get_height()*text_surface.get_width(),
                                                               normal_size_rect[3]))
                    settings.blit(_t,(normal_size_rect[0]+normal_size_rect[2]/2-_t.get_width()/2,
                                      normal_size_rect[1]))

            bg = pygame.Surface((width, height), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 100 * shade_count/10))
            screen.blit(bg, (0,0))
            screen.blit(settings, (square_x,square_y))

        else:

            if shade_count > 0:
                shade_count = max(shade_count-cns.ANIM_SPEED, 0)

            pieces.fill((0,0,0,0))
            if flipped ^ last_flip:
                board_image = pygame.transform.rotate(board_image, 180)
                background_and_board.fill((0,0,0))
                background_and_board.blit(background_image, (min((width - background_image.get_width()) / 2, 0),
                                                             min(height - background_image.get_height(), 0)))
                background_and_board.blit(board_image, (square_x, square_y))

            #静态棋子
            for p, _ in steady:
                if flipped:
                    p = 80-p
                top_x, top_y = square_x + p % 9 * cell_size + cell_size, square_y + p // 9 * cell_size + cell_size
                pieces.blit(name2piece_surface['shadow'],(top_x,top_y + cell_size*0.2))

            #静态的动画棋子阴影
            for fp, tp, jd, du, typ in animations:
                if flipped:
                    fp = 80-fp; tp = 80-tp
                if fp == tp:
                    pieces.blit(name2piece_surface['shadow'],
                                (square_x + fp % 9 * cell_size + cell_size, square_y + fp // 9 * cell_size + cell_size * 1.2))

            for p, typ in steady:
                if flipped:
                    p = 80 - p
                pieces.blit(name2piece_surface[n2c[typ]],
                            (square_x + p%9 * cell_size + cell_size,square_y + p//9 * cell_size+ cell_size))

            #高亮棋子
            if last_choice[0] >= 0:
                p, typ = last_choice
                if flipped:
                    p = 80-p
                pieces.blit(name2piece_surface['shadow'],
                            (square_x + p % 9 * cell_size + cell_size, square_y + p // 9 * cell_size + cell_size * 1.25))
                text_surface = name2piece_surface[n2c[typ]]
                pieces.blit(text_surface,(square_x + p % 9 * cell_size + cell_size, square_y + p // 9 * cell_size + int(cell_size*0.9)))

            #棋子动画
            for fp, tp, jd, du, typ in animations:
                if jd < 0:
                    continue
                if fp == -1:
                    if flipped:
                        tp = 80 - tp
                    pieces.blit(name2piece_surface[n2c[typ]],
                                (square_x + tp % 9 * cell_size + cell_size, square_y + tp // 9 * cell_size + cell_size))
                    continue
                elif fp == -2:
                    if flipped:
                        tp = 80 - tp
                    rat = jd / du
                    _i = name2piece_surface[n2c[typ]]
                    _i.set_alpha((1-rat)*255)
                    pieces.blit(_i, (square_x + tp % 9 * cell_size + cell_size, square_y + tp // 9 * cell_size + cell_size))
                    _i.set_alpha(255)
                    continue
                if flipped:
                    fp = 80-fp; tp = 80-tp
                text_surface = name2piece_surface[n2c[typ]]
                if fp == tp:
                    pieces.blit(name2piece_surface[n2c[typ]],
                                (square_x + fp % 9 * cell_size + cell_size, square_y + fp // 9 * cell_size + cell_size))
                else:
                    rat = jd/du
                    tx = (rat * (tp%9-fp%9)+fp%9) * cell_size
                    ty = (rat * (tp // 9 - fp // 9) + fp // 9) * cell_size
                    pieces.blit(name2piece_surface['shadow'],
                                (square_x + tx + cell_size, square_y + ty + cell_size*1.2))
                    pieces.blit(text_surface,(square_x + tx + cell_size,square_y + ty + cell_size * (0.8+abs(rat-0.5)*0.4)))
            #路径
            for p in paths:
                if flipped:
                    p = 80-p
                #!
                text_surface = name2piece_surface['dot']
                pieces.blit(text_surface,(square_x + p % 9 * cell_size + cell_size, square_y + p // 9 * cell_size + cell_size))
            #UI
            for p, rule in UIs:
                #!
                # text_surface = font.render(rule, True, (200, 200, 200))
                try:
                    text_surface = name2piece_surface[rule]
                except KeyError:
                    text_surface = name2piece_surface['empty_button']
                if p//10 == 8:
                    pieces.blit(text_surface,(square_x - cell_size*0.2, square_y + p%10 * cell_size))
                elif p//10 == 9:
                    pieces.blit(text_surface,(square_x + cell_size*10.2,square_y + p%10 * cell_size))
            #UI按下的效果
            if pressed[-1] > 0:
                p = pressed[0]
                #!
                text_surface = name2piece_surface['pressed']
                rat = pressed[-1]/10
                text_surface.set_alpha(255 * rat)
                if p // 10 == 8:
                    pieces.blit(text_surface, (square_x - cell_size*0.2, square_y + p % 10 * cell_size))
                elif p // 10 == 9:
                    pieces.blit(text_surface, (square_x + cell_size * 10.2, square_y + p % 10 * cell_size))

            # 评分条
            if score != -1:
                bar_count = (bar_count+score)/2
                if flipped:
                    pygame.draw.rect(pieces, (0, 0, 0),
                                     (square_x + cell_size * 0.09, square_y + cell_size * 2,
                                      cell_size * 0.5, cell_size * 7))
                    pygame.draw.rect(pieces, (255, 0, 0),
                                     (square_x + cell_size * 0.09, square_y + cell_size * 2,
                                      cell_size * 0.5, bar_count*7*cell_size))
                else:
                    pygame.draw.rect(pieces, (255, 0, 0),
                                     (square_x + cell_size * 0.09, square_y + cell_size * 2,
                                      cell_size * 0.5, cell_size * 7))
                    pygame.draw.rect(pieces, (30, 30, 30),
                                     (square_x + cell_size * 0.09, square_y + cell_size * 2,
                                      cell_size * 0.5, (1-bar_count)*7*cell_size))
                pieces.blit(bar_img, (square_x - cell_size*0.2, square_y + cell_size * 1.8))

            screen.fill((0,0,0))
            if size_adjust_rate != 1:
                small_screen.fill((0, 0, 0))
                small_screen.blit(background_and_board, (0, 0))
                small_screen.blit(pieces, (0, 0))
                screen.blit(pygame.transform.scale(small_screen,screen.get_size()),(0,0))
            else:
                screen.blit(background_and_board, (0, 0))

                screen.blit(pieces,(0,0))
                if shade_count > 0:
                    bg = pygame.Surface((width, height), pygame.SRCALPHA)
                    bg.fill((0, 0, 0, 100 * shade_count / 10))
                    screen.blit(bg, (0, 0))

        pygame.display.flip()

        clock.tick(cns.FLIP_TICKS)

    if not os.path.exists('userdata'):
        os.mkdir('userdata')
    with open('userdata\\display_setting.ini', 'w', encoding='ascii') as f:
        f.write(str(int(width))+'|'+str(int(height)))

    pygame.quit()
    game.quit()
    sys.exit()


if __name__ == "__main__":
    play()
