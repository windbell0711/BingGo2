import pygame
import sys
import game as gm

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

def grid_number(row, col):
    """将网格位置转换为对应的数字"""
    return row * 9 + col - 10

def poses2beach_p(mouse_x, mouse_y, square_x, square_y, square_size):
    row, col = get_grid_position(mouse_x, mouse_y, square_x, square_y, square_size)
    if row is None or col is None:
        print("Invalid position")
        return None
    if row not in (0,10) and col not in (0,10):
        number = grid_number(row, col)
        return number
    elif col == 0 and 0<row<10:
        return 80 + row
    elif col == 10 and 0<row<10:
        return 90 + row
    else:
        return None

def main():
    pygame.init()
    game = gm.Game()
    width, height = 800, 600
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    pygame.display.set_caption("")
    clock = pygame.time.Clock()
    running = True

    font = pygame.font.Font(None, 48)

    while running:
        number = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                width, height = event.w, event.h
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
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
        square_size = min(width, height)
        square_x = (width - square_size) // 2
        square_y = (height - square_size) // 2

        red_square = pygame.Surface((square_size, square_size))
        red_square.fill((100, 100, 100))

        cell_size = square_size / 11
        for i in range(12):
            pygame.draw.line(red_square, (150, 150, 150),
                             (i * cell_size, 0),
                             (i * cell_size, square_size), 1)
            pygame.draw.line(red_square, (150, 150, 150),
                             (0, i * cell_size),
                             (square_size, i * cell_size), 1)
        screen.blit(red_square, (square_x, square_y))

        for p, typ in steady:
            text_surface = font.render(str(typ), True, (200, 200, 200))
            screen.blit(text_surface,(square_x + p%9 * cell_size + cell_size,square_y + p//9 * cell_size+ cell_size))
        if last_choice[0] >= 0:
            p, typ = last_choice
            text_surface = font.render(str(typ), True, (255, 255, 255))
            screen.blit(text_surface,(square_x + p % 9 * cell_size + cell_size, square_y + p // 9 * cell_size + int(cell_size*0.9)))
        for fp, tp, jd, du, typ in animations:
            text_surface = font.render(str(typ), True, (200, 200, 200))
            rat = max(0,jd/du)
            tx = int((rat * (tp%9-fp%9)+fp%9) * cell_size)
            ty = int((rat * (tp // 9 - fp // 9) + fp // 9) * cell_size)
            screen.blit(text_surface,(square_x + tx + cell_size,square_y + ty+ cell_size))
        for p in paths:
            text_surface = font.render('·', True, (200, 200, 200))
            screen.blit(text_surface,(square_x + p % 9 * cell_size + cell_size, square_y + p // 9 * cell_size + cell_size))




        ##+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    game.quit()
    sys.exit()


if __name__ == "__main__":
    main()
