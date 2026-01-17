import time
print("------From main_debug.py------")

print("Entering DEBUG mode...")
time.sleep(1)

with open("main_debug_report.txt", "a") as f:
    f.write(f"------From main_debug.py------\n{time.time() = }\n")
    f.write(f"Entering DEBUG mode...\n")

    import constant
    constant.DEBUG = True

    f.write(f"{constant.DEBUG = }\n")

    print("Setting up binggo_debug.log...")
    f.write("Setting up binggo_debug.log...\n")
    time.sleep(1)

    import logging
    import logging.handlers

    # 配置全局日志
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # 控制台输出
            logging.FileHandler('binggo_debug.log', encoding='utf-8')  # 文件输出
        ]
    )

    print("Opening game...")
    f.write("Opening game...\n")
    time.sleep(1)

    from display import play

    play()
