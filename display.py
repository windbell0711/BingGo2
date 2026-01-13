import time
import pygame
import sys
import game as gm

# import ctypes
# if sys.platform == 'win32':
#     ctypes.windll.shcore.SetProcessDpiAwareness(1)

## TEMP!!!
n2c = {1:'车',2:'马',3:'相',4:'士',5:'炮',6:'帅',7:'卒',8:'城',9:'教',10:'骑',11:'后',12:'王',13:'兵',14:'#'}

FONT = 'STLiTi'

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
    return int(row), int(col)

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
    game = gm.Game()
    width, height = 900, 600
    square_size = min(width, height)
    square_x = (width - square_size) // 2
    square_y = (height - square_size) // 2
    cell_size = square_size / 11
    line_w = int(cell_size / 20)
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    size_adjust_rate = 1
    MAX_SCREEN_PIXEL = 3000

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
    # steady = set()
    # animations = []
    # last_choice = (-1, -1)
    # paths = set()
    # UIs = set()
    # pressed = (-1, 0)

    def reset_all_elements():
        nonlocal flipped, steady, animations, last_choice, paths, UIs, pressed
        flipped = False
        steady = set()
        animations = []
        last_choice = (-1,-1)
        paths = set()
        UIs = set()
        pressed = (-1,0)

    pygame.display.set_caption("Chess vs XiangQi")
    clock = pygame.time.Clock()
    running = True

    # 贴图初始化
    background_image_original = pygame.image.load('imgs/background.png').convert_alpha()

    board_image_original = pygame.image.load('imgs/board.png').convert_alpha()

    all_piece_img_names = ['empty_piece','shadow','!','&','undo','gret','h','r','pressed','dot','empty_button']

    name2piece_original_surface = {}
    name2piece_surface = {}
    for name in all_piece_img_names:
        name2piece_original_surface[name] = pygame.image.load(f'imgs/{name}.png').convert_alpha()
    font = pygame.font.SysFont(FONT, 500)
    for typ, name in zip(n2c.keys(),n2c.values()):
        try:
            name2piece_original_surface[name] = pygame.image.load(f'imgs/{name}.png').convert_alpha()
        except FileNotFoundError:
            tmps = pygame.image.load('imgs/empty_piece.png').convert_alpha()
            text_surface = font.render(n2c[typ], True, (20, 20, 20) if typ > 7 else (137, 57, 37))
            tmps.blit(text_surface,(110,110))
            name2piece_original_surface[name] = tmps
    background_and_board = board_image = background_image = pieces = small_screen = settings = pygame.Surface((0,0))

    def reset_all_imgs():
        nonlocal background_and_board, pieces, board_image, font, settings, \
            background_and_board, background_image, small_screen, pieces, width, height
        small_screen = pygame.Surface((width, height), pygame.SRCALPHA)
        background_and_board = pygame.Surface((width, height), pygame.SRCALPHA)
        pieces = pygame.Surface((width, height), pygame.SRCALPHA)
        settings = pygame.Surface((square_size, square_size), pygame.SRCALPHA)
        print(width,height)
        # 此处包含贴图大小调整
        if width > height * 1.5:
            background_image = pygame.transform.scale(background_image_original, (width, width / 1.5))
        else:
            background_image = pygame.transform.scale(background_image_original, (height * 1.5, height))
        board_image = pygame.transform.scale(board_image_original, (square_size, square_size))
        background_and_board.blit(background_image, (min((width - background_image.get_width()) / 2, 0),
                                                     min(height - background_image.get_height(), 0)))
        background_and_board.blit(board_image, (square_x, square_y))

        for name_ in all_piece_img_names + list(n2c.values()):
            name2piece_surface[name_] = pygame.transform.scale(name2piece_original_surface[name_],
                                                              (cell_size, cell_size))
        font = pygame.font.SysFont(FONT, int(cell_size))

    reset_all_imgs()
    while running:
        number = None
        mouse_x, mouse_y = None, None
        clicked = False
        size_changed = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                width, height = event.w, event.h
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                square_size = min(width, height)
                square_x = (width - square_size) // 2
                square_y = (height - square_size) // 2
                cell_size = square_size / 11
                line_w = int(cell_size / 20)
                # MAX_SCREEN_PIXEL = screen.get_width() // 2
                adjust_max_pixel()
                reset_all_imgs()
                reset_all_elements()
                size_changed = True

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    number = poses2beach_p(mouse_x*size_adjust_rate, mouse_y*size_adjust_rate, square_x, square_y, square_size)
                    clicked = True

        st = time.time()
        last_flip = flipped
        flipped, steady, animations, last_choice, paths, UIs, pressed, menu = (
            game.handle_input_p(number, width, height, mouse_x, mouse_y, clicked))

        if menu is not None:
            settings.fill((0,0,0,0))
            screen.blit(background_image, (min((width - background_image.get_width()) / 2, 0),
                                           min(height - background_image.get_height(), 0)))
            for elem in menu:
                if type(elem) is gm.Button:
                    normal_size_rect = raise_size_of_rect(elem.rect,square_size)
                    rat = elem.shade_time/elem.shade_time_max * 150
                    pygame.draw.rect(settings, (253 - rat, 251 - rat, 184 - rat, 160), normal_size_rect)
                    pygame.draw.rect(settings,(30,30,30),normal_size_rect, line_w)
                    text_surface = font.render(elem.return_text(), True, (0,0,0))
                    _t = pygame.transform.scale(text_surface, (normal_size_rect[3]/text_surface.get_height()*text_surface.get_width(),
                                                               normal_size_rect[3]))
                    settings.blit(_t,(normal_size_rect[0]+normal_size_rect[2]/2-_t.get_width()/2,
                                      normal_size_rect[1]))

            bg = pygame.Surface((width, height), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 100))
            screen.blit(bg, (0,0))
            screen.blit(settings, (square_x,square_y))

        else:

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

            #静态动画棋子阴影
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
                            (square_x + p % 9 * cell_size + cell_size, square_y + p // 9 * cell_size + cell_size * 1.2))
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
                if p // 10 == 8:
                    pieces.blit(text_surface, (square_x - cell_size*0.2, square_y + p % 10 * cell_size))
                elif p // 10 == 9:
                    pieces.blit(text_surface, (square_x + cell_size * 10.2, square_y + p % 10 * cell_size))


            screen.fill((0,0,0))
            if size_adjust_rate != 1:
                small_screen.fill((0, 0, 0))
                small_screen.blit(background_and_board, (0, 0))
                small_screen.blit(pieces, (0, 0))
                screen.blit(pygame.transform.scale(small_screen,screen.get_size()),(0,0))
            else:
                screen.blit(background_and_board, (0, 0))
                screen.blit(pieces,(0,0))

        if time.time()-st>0.01:
            print(time.time()-st)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    game.quit()
    sys.exit()


if __name__ == "__main__":
    play()