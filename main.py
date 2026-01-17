import logging
import logging.handlers

# 配置全局日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler('binggo.log', encoding='utf-8')  # 文件输出
    ]
)

try:
    from display import play
    play()
except Exception as e:
    import traceback
    logging.critical(traceback.format_exc())
    raise e
