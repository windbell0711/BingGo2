import sys

# 配置全局日志
import logging
import logging.handlers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler('binggo.log', encoding='utf-8')  # 文件输出
    ]
)

# 保证必要文件就位
import os
FILES = (
    "engine/binggo.ini",
    "engine/config.ini",
    "engine/fairy-stockfish-largeboards_x86-64-bmi2-latest.exe",
)
for file in FILES:
    if not os.path.exists(file):
        logging.critical(f"缺少必要文件：{file}")
        from tkinter import messagebox
        messagebox.showerror("错误", f"缺少必要文件：{file}")
        sys.exit(1)

# 确定debug模式是否开启
if os.path.exists("debug_admin.txt"):
    logging.getLogger().setLevel(logging.DEBUG)
    logging.info("Debug mode enabled.")
    try:
        import constant
        constant.DEBUG = True
    except:
        logging.critical("Failed to import constant.")
        sys.exit(1)

# 运行游戏
try:
    import display
    display.play()
except Exception as e:
    import traceback
    logging.critical(traceback.format_exc())
    display.pygame.quit()
    display.game.quit()
    sys.exit(1)
