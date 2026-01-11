import pygame
import sys
from typing import Literal, Tuple, List, Dict, Any, Optional, Callable
import ctypes

if sys.platform == 'win32':
    ctypes.windll.shcore.SetProcessDpiAwareness(1)


class SettingOption:
    """设置选项"""

    def __init__(self, name: str, typ: Callable[[int], Any], text: str, options: list[str], default_index: int = 0):
        assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in name)
        self.name = name
        self.typ = typ  # 添加typ实例属性
        self.text = text  # 选项名称
        self.options = options  # 可选值列表
        self.selected_index = default_index  # 当前选中索引

    def get_current(self) -> str:
        """获取当前选中的值"""
        return self.options[self.selected_index]

    def get_display_text(self) -> str:
        """获取显示文本"""
        return f"{self.text}: {self.get_current()}"

    def next_option(self):
        """切换到下一个选项"""
        self.selected_index = (self.selected_index + 1) % len(self.options)


class SettingCategory:
    """设置类别"""

    def __init__(self, name: str, options: list[SettingOption]):
        self.name = name
        self.options = options


SETTING_WIDTH_MIN = 250
SETTING_HEIGHT_MIN = 300

SETTING_MARGIN_N = 20
SETTING_MARGIN_S = 60
SETTING_MARGIN_W = 30
SETTING_MARGIN_E = 30

BUTTON_WIDTH = 200
BUTTON_HEIGHT = 25
BUTTON_SPACING_Y = 10
BUTTON_SPACING_X = 15


class Color:
    BG = (240, 240, 240)
    BUTTON = (200, 200, 200)
    BUTTON_HOVER = (180, 180, 220)
    TEXT = (50, 50, 50)
    BORDER = (100, 100, 100)
    PAGE_BTN = (150, 150, 150)
    PAGE_BTN_HOVER = (130, 130, 180)
    PAGE_TEXT = (70, 70, 70)
    BACK_BTN = (200, 150, 150)
    BACK_BTN_HOVER = (180, 130, 130)


class SettingsUI:
    """设置界面管理类（请不要从外部调用SettingsUI）"""

    def __init__(self):
        # 界面状态
        self.current_state: Literal['main'] | Literal['submenu'] = 'main'
        self.current_category: Optional[SettingCategory] = None
        self.current_category_index = -1

        # 分页相关
        self.current_page = 0
        self.total_pages = 1
        self.buttons_per_page = 0

        # 子菜单分页
        self.submenu_current_page = 0
        self.submenu_total_pages = 1
        self.submenu_buttons_per_page = 0

        # 按钮状态
        self.category_buttons: List[Dict[str, Any]] = []  # 存储category按钮的矩形和索引
        self.option_buttons: List[Dict[str, Any]] = []  # 存储选项按钮的矩形和选项信息
        self.page_buttons: Dict[str, pygame.Rect] = {}  # 存储翻页按钮的矩形
        self.back_button: Optional[pygame.Rect] = None  # 返回按钮

        # 错误信息
        self.error_message: Optional[str] = None

        # 绘制列表
        self.draw_list: List[Dict[str, Any]] = []

    def _validate_screen_size(self, screen_width: int, screen_height: int) -> None:
        """验证屏幕尺寸是否满足最小要求"""
        if screen_width < SETTING_WIDTH_MIN:
            raise ValueError(f"屏幕宽度必须至少为{SETTING_WIDTH_MIN}像素")

        if screen_height < SETTING_HEIGHT_MIN:
            raise ValueError(f"屏幕高度必须至少为{SETTING_HEIGHT_MIN}像素")

    def _calculate_layout_params(self, available_width: int, available_height: int) -> Tuple[int, int]:
        """计算布局参数"""
        # 检查最小按钮显示区域
        min_button_height = 2 * BUTTON_HEIGHT + BUTTON_SPACING_Y
        if available_height < min_button_height:
            raise ValueError("屏幕高度不足以显示按钮")

        # 计算每行按钮数量
        min_row_width = 2 * BUTTON_WIDTH + BUTTON_SPACING_X
        if available_width < min_row_width:
            buttons_per_row = 1
        else:
            buttons_per_row = 2

        # 计算每列按钮数量
        buttons_per_col = available_height // (BUTTON_HEIGHT + BUTTON_SPACING_Y)

        return buttons_per_row, buttons_per_col

    def calculate_main_layout(self, screen_width: int, screen_height: int) -> Tuple[int, int, int, int]:
        """计算主菜单布局"""
        # 验证屏幕尺寸
        self._validate_screen_size(screen_width, screen_height)

        # 计算可用区域
        available_width = screen_width - SETTING_MARGIN_W - SETTING_MARGIN_E
        available_height = screen_height - SETTING_MARGIN_N - SETTING_MARGIN_S

        # 计算按钮布局参数
        buttons_per_row, buttons_per_col = self._calculate_layout_params(available_width, available_height)

        # 计算总页数
        self.buttons_per_page = buttons_per_row * buttons_per_col
        self.total_pages = (len(Settings.SETTINGS) + self.buttons_per_page - 1) // self.buttons_per_page

        # 确保当前页在有效范围内
        if self.current_page >= self.total_pages:
            self.current_page = max(0, self.total_pages - 1)

        return available_width, available_height, buttons_per_row, buttons_per_col

    def calculate_submenu_layout(self, screen_width: int, screen_height: int) -> Optional[Tuple[int, int, int, int]]:
        """计算子菜单布局"""
        if not self.current_category:
            return None

        # 验证屏幕尺寸
        self._validate_screen_size(screen_width, screen_height)

        # 计算可用区域（留出底部完成按钮的位置）
        available_width = screen_width - SETTING_MARGIN_W - SETTING_MARGIN_E
        available_height = screen_height - SETTING_MARGIN_N - SETTING_MARGIN_S - BUTTON_HEIGHT - BUTTON_SPACING_Y

        # 计算按钮布局参数
        buttons_per_row, buttons_per_col = self._calculate_layout_params(available_width, available_height)

        # 获取当前category的选项列表
        option_names = [o.text for o in self.current_category.options]

        # 计算总页数
        self.submenu_buttons_per_page = buttons_per_row * buttons_per_col
        self.submenu_total_pages = (
                                               len(option_names) + self.submenu_buttons_per_page - 1) // self.submenu_buttons_per_page

        # 确保当前页在有效范围内
        if self.submenu_current_page >= self.submenu_total_pages:
            self.submenu_current_page = max(0, self.submenu_total_pages - 1)

        return available_width, available_height, buttons_per_row, buttons_per_col

    def update(self, screen_size: Tuple[int, int], mouse_pos: Optional[Tuple[int, int]] = None,
               mouse_clicked: bool = False) -> list[Dict[str, Any]]:
        """更新UI状态并生成绘制列表"""
        screen_width, screen_height = screen_size

        # 清空绘制列表
        self.draw_list.clear()

        # 添加背景
        self.draw_list.append({
            'type': 'rect',
            'rect': pygame.Rect(0, 0, screen_width, screen_height),
            'color': Color.BG,
            'border_radius': 0,
            'border_width': 0
        })

        try:
            if self.current_state == 'main':
                self._update_main_menu(screen_width, screen_height, mouse_pos, mouse_clicked)
            elif self.current_state == 'submenu':
                self._update_submenu(screen_width, screen_height, mouse_pos, mouse_clicked)
        except ValueError as e:
            self.error_message = str(e)
            self._draw_error_message(screen_width, screen_height)
        return self.draw_list

    def _update_main_menu(self, screen_width: int, screen_height: int,
                          mouse_pos: Optional[Tuple[int, int]], mouse_clicked: bool) -> None:
        """更新主菜单状态"""
        self.error_message = None

        # 计算布局
        available_width, available_height, buttons_per_row, buttons_per_col = self.calculate_main_layout(screen_width,
                                                                                                         screen_height)

        # 绘制标题
        self.draw_list.append({
            'type': 'text',
            'text': '设置',
            'font_size': 28,
            'color': Color.TEXT,
            'center': (screen_width // 2, 10),
            'font_name': 'SimHei'
        })

        # 计算按钮起始位置
        start_x = SETTING_MARGIN_W
        start_y = SETTING_MARGIN_N

        # 计算按钮居中偏移量
        if buttons_per_row == 1:
            # 单列时居中
            offset_x = (available_width - BUTTON_WIDTH) // 2
            button_x = start_x + offset_x
        else:
            # 多列时居中
            total_buttons_width = 2 * BUTTON_WIDTH + BUTTON_SPACING_X
            offset_x = (available_width - total_buttons_width) // 2
            button_x = start_x + offset_x

        # 绘制当前页的按钮
        self.category_buttons.clear()
        start_index = self.current_page * self.buttons_per_page
        end_index = min(start_index + self.buttons_per_page, len(Settings.SETTINGS))

        row, col = 0, 0
        for i in range(start_index, end_index):
            category = Settings.SETTINGS[i]

            # 计算按钮位置
            if buttons_per_row == 1:
                x = button_x
            else:
                x = button_x + col * (BUTTON_WIDTH + BUTTON_SPACING_X)
            y = start_y + row * (BUTTON_HEIGHT + BUTTON_SPACING_Y)

            # 创建按钮矩形
            button_rect = pygame.Rect(x, y, BUTTON_WIDTH, BUTTON_HEIGHT)

            # 检查鼠标是否悬停
            is_hover = False
            if mouse_pos and button_rect.collidepoint(mouse_pos):
                is_hover = True
                if mouse_clicked:
                    # 进入子菜单
                    self.current_state = 'submenu'
                    self.current_category = category
                    self.current_category_index = i
                    self.submenu_current_page = 0  # 重置子菜单页码
                    return

            # 添加按钮到绘制列表
            color = Color.BUTTON_HOVER if is_hover else Color.BUTTON
            self.draw_list.append({
                'type': 'rect',
                'rect': button_rect,
                'color': color,
                'border_radius': 5,
                'border_width': 2,
                'border_color': Color.BORDER
            })

            # 添加按钮文字
            self.draw_list.append({
                'type': 'text',
                'text': category.name,
                'font_size': 20,
                'color': Color.TEXT,
                'center': button_rect.center,
                'font_name': 'SimHei'
            })

            # 保存按钮信息
            self.category_buttons.append({
                'rect': button_rect,
                'index': i,
                'category': category
            })

            # 更新行列计数
            col += 1
            if col >= buttons_per_row:
                col = 0
                row += 1

        # 绘制页码控件
        self._draw_page_controls(screen_width, screen_height, mouse_pos, mouse_clicked, is_main_menu=True)

    def _update_submenu(self, screen_width: int, screen_height: int,
                        mouse_pos: Optional[Tuple[int, int]], mouse_clicked: bool) -> None:
        """更新子菜单状态"""
        self.error_message = None

        # 计算布局
        layout_result = self.calculate_submenu_layout(screen_width, screen_height)
        if not layout_result:
            return

        available_width, available_height, buttons_per_row, buttons_per_col = layout_result

        # 绘制标题（显示当前category名称）
        if self.current_category:
            self.draw_list.append({
                'type': 'text',
                'text': self.current_category.name,
                'font_size': 28,
                'color': Color.TEXT,
                'center': (screen_width // 2, 10),
                'font_name': 'SimHei'
            })

        # 绘制选项按钮
        self.option_buttons.clear()

        # 计算按钮起始位置
        start_x = SETTING_MARGIN_W
        start_y = SETTING_MARGIN_N

        # 计算按钮居中偏移量
        if buttons_per_row == 1:
            # 单列时居中
            offset_x = (available_width - BUTTON_WIDTH) // 2
            button_x = start_x + offset_x
        else:
            # 多列时居中
            total_buttons_width = 2 * BUTTON_WIDTH + BUTTON_SPACING_X
            offset_x = (available_width - total_buttons_width) // 2
            button_x = start_x + offset_x

        # 绘制当前页的按钮
        if self.current_category:
            option_items = self.current_category.options
            start_index = self.submenu_current_page * self.submenu_buttons_per_page
            end_index = min(start_index + self.submenu_buttons_per_page, len(option_items))

            row, col = 0, 0
            MAX_DISPLAY_LENGTH = 15  # 最大显示长度常量
            for i in range(start_index, end_index):
                option = option_items[i]

                # 计算按钮位置
                if buttons_per_row == 1:
                    x = button_x
                else:
                    x = button_x + col * (BUTTON_WIDTH + BUTTON_SPACING_X)
                y = start_y + row * (BUTTON_HEIGHT + BUTTON_SPACING_Y)

                # 创建按钮矩形
                button_rect = pygame.Rect(x, y, BUTTON_WIDTH, BUTTON_HEIGHT)

                # 检查鼠标是否悬停
                is_hover = False
                if mouse_pos and button_rect.collidepoint(mouse_pos):
                    is_hover = True
                    if mouse_clicked:
                        # 切换选项
                        option.next_option()
                        print(f"切换选项: {option.get_display_text()}")

                # 添加按钮到绘制列表
                color = Color.BUTTON_HOVER if is_hover else Color.BUTTON
                self.draw_list.append({
                    'type': 'rect',
                    'rect': button_rect,
                    'color': color,
                    'border_radius': 5,
                    'border_width': 2,
                    'border_color': Color.BORDER
                })

                # 添加按钮文字
                display_text = option.get_display_text()
                # 如果文字太长，截断
                # if len(display_text) > MAX_DISPLAY_LENGTH:
                #     display_text = display_text[:MAX_DISPLAY_LENGTH] + "..."

                self.draw_list.append({
                    'type': 'text',
                    'text': display_text,
                    'font_size': 20,
                    'color': Color.TEXT,
                    'center': button_rect.center,
                    'font_name': 'SimHei'
                })

                # 保存按钮信息
                self.option_buttons.append({
                    'rect': button_rect,
                    'option': option
                })

                # 更新行列计数
                col += 1
                if col >= buttons_per_row:
                    col = 0
                    row += 1

        # 绘制完成按钮（右下角）
        back_button_width = 80
        back_button_x = screen_width - SETTING_MARGIN_E - back_button_width
        back_button_y = screen_height - SETTING_MARGIN_S + 10

        back_button_rect = pygame.Rect(back_button_x, back_button_y, back_button_width, BUTTON_HEIGHT)

        # 检查鼠标是否悬停
        is_hover_back = False
        if mouse_pos and back_button_rect.collidepoint(mouse_pos):
            is_hover_back = True
            if mouse_clicked:
                # 返回主菜单
                self.current_state = 'main'
                self.current_category = None
                self.current_category_index = -1
                self.page_buttons.clear()  # 清空翻页按钮
                return

        # 绘制返回按钮
        back_color = Color.BACK_BTN_HOVER if is_hover_back else Color.BACK_BTN
        self.draw_list.append({
            'type': 'rect',
            'rect': back_button_rect,
            'color': back_color,
            'border_radius': 5,
            'border_width': 2,
            'border_color': Color.BORDER
        })

        self.draw_list.append({
            'type': 'text',
            'text': "完成",
            'font_size': 20,
            'color': Color.TEXT,
            'center': back_button_rect.center,
            'font_name': 'SimHei'
        })

        self.back_button = back_button_rect

        # 如果选项多于一页，绘制子菜单的翻页控件
        if self.submenu_total_pages > 1:
            self._draw_page_controls(screen_width, screen_height, mouse_pos, mouse_clicked, is_main_menu=False)

    def _draw_page_controls(self, screen_width: int, screen_height: int,
                            mouse_pos: Optional[Tuple[int, int]], mouse_clicked: bool,
                            is_main_menu: bool = True) -> None:
        """绘制页码控件"""
        if is_main_menu:
            total_pages = self.total_pages
            current_page = self.current_page
            if total_pages <= 1:
                return
        else:
            total_pages = self.submenu_total_pages
            current_page = self.submenu_current_page
            if total_pages <= 1:
                return

        # 页码显示区域
        if is_main_menu:
            page_area_y = screen_height - SETTING_MARGIN_S
            page_area_height = SETTING_MARGIN_S
        else:
            # 子菜单中，页码显示在返回按钮上方
            page_area_y = screen_height - SETTING_MARGIN_S
            page_area_height = SETTING_MARGIN_S - BUTTON_HEIGHT - BUTTON_SPACING_Y

        # 页码文字
        page_text = f"第 {current_page + 1} / {total_pages} 页"
        self.draw_list.append({
            'type': 'text',
            'text': page_text,
            'font_size': 16,
            'color': Color.PAGE_TEXT,
            'center': (screen_width // 2, page_area_y + page_area_height // 2),
            'font_name': 'SimHei'
        })

        # 翻页按钮
        btn_width, btn_height = 80, 30
        btn_y = page_area_y + (page_area_height - btn_height) // 2

        # 上一页按钮
        prev_btn_x = screen_width // 2 - btn_width - 20
        prev_btn_rect = pygame.Rect(prev_btn_x, btn_y, btn_width, btn_height)

        prev_hover = False
        if mouse_pos and prev_btn_rect.collidepoint(mouse_pos):
            prev_hover = True
            if mouse_clicked:
                if is_main_menu and self.current_page > 0:
                    self.current_page -= 1
                elif not is_main_menu and self.submenu_current_page > 0:
                    self.submenu_current_page -= 1

        prev_color = Color.PAGE_BTN_HOVER if prev_hover else Color.PAGE_BTN
        self.draw_list.append({
            'type': 'rect',
            'rect': prev_btn_rect,
            'color': prev_color,
            'border_radius': 3,
            'border_width': 1,
            'border_color': Color.BORDER
        })

        self.draw_list.append({
            'type': 'text',
            'text': "上一页",
            'font_size': 16,
            'color': Color.PAGE_TEXT,
            'center': prev_btn_rect.center,
            'font_name': 'SimHei'
        })

        self.page_buttons['prev'] = prev_btn_rect

        # 下一页按钮
        next_btn_x = screen_width // 2 + 20
        next_btn_rect = pygame.Rect(next_btn_x, btn_y, btn_width, btn_height)

        next_hover = False
        if mouse_pos and next_btn_rect.collidepoint(mouse_pos):
            next_hover = True
            if mouse_clicked:
                if is_main_menu and self.current_page < total_pages - 1:
                    self.current_page += 1
                elif not is_main_menu and self.submenu_current_page < total_pages - 1:
                    self.submenu_current_page += 1

        next_color = Color.PAGE_BTN_HOVER if next_hover else Color.PAGE_BTN
        self.draw_list.append({
            'type': 'rect',
            'rect': next_btn_rect,
            'color': next_color,
            'border_radius': 3,
            'border_width': 1,
            'border_color': Color.BORDER
        })

        self.draw_list.append({
            'type': 'text',
            'text': "下一页",
            'font_size': 16,
            'color': Color.PAGE_TEXT,
            'center': next_btn_rect.center,
            'font_name': 'SimHei'
        })

        self.page_buttons['next'] = next_btn_rect

    def _draw_error_message(self, screen_width: int, screen_height: int) -> None:
        """绘制错误信息"""
        if self.error_message:
            self.draw_list.append({
                'type': 'text',
                'text': f"错误: {self.error_message}",
                'font_size': 20,
                'color': (255, 0, 0),
                'center': (screen_width // 2, screen_height // 2),
                'font_name': 'SimHei'
            })


class Settings:
    SETTINGS = [
        SettingCategory("规则设置", [
            SettingOption("castle_black", bool, "王车易位", ["关闭", "黑方开启"], 0),
            SettingOption("mobility_king_in_palace", bool, "黑王走子范围", ["不可进入九宫", "全局"], 0),
        ]),
        SettingCategory("显示设置", [
            SettingOption("hint_no_avai_move", int, "棋子无可走区域提示", ["仅高亮", "抖动", "弹窗"], 1),
        ]),
    ]

    def __init__(self):
        self.ui = SettingsUI()
        self.switches: Dict[str, Any] = {}

    def sync(self, screen_size: Tuple[int, int], mouse_pos: Optional[Tuple[int, int]] = None,
             mouse_clicked: bool = False) -> List[Dict[str, Any]]:
        # 更新ui和设置项
        temp = self.ui.update(screen_size, mouse_pos, mouse_clicked)

        # 同步所有设置选项到self.switches字典
        for category in self.SETTINGS:
            for option in category.options:
                if option.typ is str:
                    self.switches[option.name] = option.get_current()
                else:
                    self.switches[option.name] = option.typ(option.selected_index)

        return temp

    def __getitem__(self, item_name: str):
        return self.switches[item_name]


def draw_from_list(screen: pygame.Surface, draw_list: List[Dict[str, Any]],
                   fonts_cache: Dict[Tuple[str, int], pygame.font.Font]) -> None:
    """根据绘制列表在屏幕上绘制"""
    for draw_item in draw_list:
        item_type = draw_item['type']

        if item_type == 'rect':
            # 绘制矩形
            rect = draw_item['rect']
            color = draw_item['color']
            border_radius = draw_item.get('border_radius', 0)
            border_width = draw_item.get('border_width', 0)
            border_color = draw_item.get('border_color', None)

            # 绘制填充矩形
            pygame.draw.rect(screen, color, rect, border_radius=border_radius)

            # 绘制边框
            if border_width > 0 and border_color:
                pygame.draw.rect(screen, border_color, rect, border_width, border_radius=border_radius)

        elif item_type == 'text':
            # 绘制文本
            text = draw_item['text']
            font_size = draw_item['font_size']
            color = draw_item['color']
            center = draw_item['center']
            font_name = draw_item.get('font_name', 'SimHei')

            # 从缓存获取字体或创建新字体
            font_key = (font_name, font_size)
            if font_key not in fonts_cache:
                fonts_cache[font_key] = pygame.font.SysFont(font_name, font_size)

            font = fonts_cache[font_key]
            text_surface = font.render(text, True, color)
            text_rect = text_surface.get_rect(center=center)
            screen.blit(text_surface, text_rect)


def test():
    # 初始化pygame
    pygame.init()
    screen = pygame.display.set_mode((SETTING_WIDTH_MIN, SETTING_HEIGHT_MIN), pygame.RESIZABLE)
    pygame.display.set_caption("设置")

    # 创建UI实例
    set = Settings()

    # 字体缓存
    fonts_cache = {}

    # 鼠标点击状态
    mouse_clicked = False
    mouse_pos = None

    # 主循环
    clock = pygame.time.Clock()
    running = True

    try:
        while running:
            # 重置鼠标点击状态
            mouse_clicked = False

            # 处理事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_clicked = True
                elif event.type == pygame.VIDEORESIZE:
                    # 窗口大小改变时，更新屏幕
                    screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            # 获取鼠标位置
            mouse_pos = pygame.mouse.get_pos()

            # 获取屏幕大小
            screen_size = screen.get_size()

            # 更新UI状态并生成绘制列表
            set.sync(screen_size, mouse_pos, mouse_clicked)

            # 清屏
            screen.fill(Color.BG)

            # 根据绘制列表绘制
            draw_from_list(screen, set.ui.draw_list, fonts_cache)

            # 更新显示
            pygame.display.flip()

            # 控制帧率
            clock.tick(60)

    except KeyboardInterrupt:
        print(set.switches)
        pass
    finally:
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    test()