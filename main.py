import sys
import time

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
    # "engine/binggo.ini",
    # "engine/config.ini",
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
        from src import consts
        consts.DEBUG = True
    except:
        logging.critical("Failed to import constant.")
        sys.exit(1)

# 运行游戏
try:
    from src import display, consts
    logging.info("Game begins: " + consts.VERSION)
    display.play()
except ModuleNotFoundError as e:
    import traceback
    logging.critical(traceback.format_exc())
except (Exception, KeyboardInterrupt) as e:
    import traceback
    logging.critical(traceback.format_exc())
    try:
        logging.info("运行出错，正在尝试保存...")
        import json
        g = display.game
        content = json.dumps({
            'start_fen': g.board.initial_fen,
            'moves': ' '.join(g.moves),
            'switches': g.eng_stg.switches,
        })
        if content:
            with open(f"./saves/error_save_{int(time.time())}.binggo", "a", encoding="ascii") as f:
                f.write(content)
                logging.info("保存成功。")
        else:
            logging.info("没有需要保存的内容。")
    except Exception as ee:
        logging.info("保存失败。")
    display.pygame.quit()
    display.game.quit()
    time.sleep(0.5)
    sys.exit(1)
