import pygame
import sys
import game as gm

## TODO: TEMP!!!
n2c = {1:'车',2:'马',3:'相',4:'士',5:'炮',6:'帅',7:'卒',8:'城',9:'教',10:'骑',11:'后',12:'王',13:'兵'}

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
    return row, col

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

def play():
    pygame.init()
    game = gm.Game()
    width, height = 800, 600
    square_size = min(width, height)
    square_x = (width - square_size) // 2
    square_y = (height - square_size) // 2
    cell_size = square_size / 11
    font = pygame.font.SysFont('STLiti', int(cell_size))
    #此处应包含贴图初始化

    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    pygame.display.set_caption("Chess vs XiangQi")
    clock = pygame.time.Clock()
    running = True


    while running:
        number = None
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
                font = pygame.font.SysFont('STLiti', int(cell_size))
                # 此处应包含贴图大小调整

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    square_size = min(width, height)
                    square_x = (width - square_size) // 2
                    square_y = (height - square_size) // 2
                    number = poses2beach_p(mouse_x, mouse_y, square_x, square_y, square_size)
        flipped, steady, animations, last_choice, paths, UIs = game.handle_input_p(number)

        #####以下可以删++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        screen.fill((80,80,80))

        red_square = pygame.Surface((square_size, square_size))
        red_square.fill((100, 100, 100))
        for i in range(12):
            pygame.draw.line(red_square, (150, 150, 150),
                             (i * cell_size, 0),
                             (i * cell_size, square_size), 1)
            pygame.draw.line(red_square, (150, 150, 150),
                             (0, i * cell_size),
                             (square_size, i * cell_size), 1)
        screen.blit(red_square, (square_x, square_y))

        for p, typ in steady:
            #!
            if flipped:
                p = 80-p
            text_surface = font.render(n2c[typ], True, (200, 200, 200) if typ > 7 else (220, 100, 100))
            screen.blit(text_surface,(square_x + p%9 * cell_size + cell_size,square_y + p//9 * cell_size+ cell_size))

        if last_choice[0] >= 0:
            p, typ = last_choice
            if flipped:
                p = 80-p
            #!
            text_surface = font.render(n2c[typ], True, (255, 255, 255) if typ > 7 else (250, 100, 100))
            screen.blit(text_surface,(square_x + p % 9 * cell_size + cell_size, square_y + p // 9 * cell_size + int(cell_size*0.9)))

        for fp, tp, jd, du, typ in animations:
            if jd < 0:
                continue
            if flipped:
                fp = 80-fp; tp = 80-tp
            #!
            text_surface = font.render(n2c[typ], True, (200, 200, 200) if typ > 7 else (220, 100, 100))
            rat = jd/du
            tx = int((rat * (tp%9-fp%9)+fp%9) * cell_size)
            ty = int((rat * (tp // 9 - fp // 9) + fp // 9) * cell_size)
            screen.blit(text_surface,(square_x + tx + cell_size,square_y + ty+ cell_size))

        for p in paths:
            if flipped:
                p = 80-p
            #!
            text_surface = font.render('·', True, (200, 200, 200))
            screen.blit(text_surface,(square_x + p % 9 * cell_size + cell_size, square_y + p // 9 * cell_size + cell_size))

        for p, rule in UIs:
            #!
            text_surface = font.render(rule, True, (200, 200, 200))
            if p//10 == 8:
                screen.blit(text_surface,(square_x,square_y + p%10 * cell_size))
            elif p//10 == 9:
                screen.blit(text_surface,(square_x + cell_size*10,square_y + p%10 * cell_size))

        ##+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    game.quit()
    sys.exit()


if __name__ == "__main__":
    play()
