import time
import logging
from threading import Thread

from src import engine
from src import constant as consts

logger = logging.getLogger(__name__)


class RatingSystem:
    def __init__(self):
        if consts.DEBUG:
            self.eng = engine.BinggoEngine(debug_file="eng_rate.log")
        else:
            self.eng = engine.BinggoEngine()
        self.score = (None, None, None, None)
        self.rating_thread = None
        self.fen = None
        self.rating_depth = 5
        self.do_rate = True

    def _tr(self):
        while self.do_rate:
            if self.rating_depth < 16:
                try:
                    assert self.fen
                    self.score = self.eng.analyze(self.fen, depth=self.rating_depth)
                except RuntimeError as e:
                    logger.warning(f"Runtime error during analysis: {e}")
                except Exception as e:
                    self.quit()
                self.rating_depth += 2
            else:
                time.sleep(0.2)

    def stop_current_rate(self):
        self.eng.stop()

    def thread_rate_begin(self):
        self.rating_thread = Thread(target=self._tr)
        self.rating_thread.start()

    def refresh_fen(self, fen: str):
        self.fen = fen
        self.rating_time = 100
        self.stop_current_rate()

    def reboot(self):
        self.do_rate = False
        self.stop_current_rate()
        self.rating_thread.join()  # type: ignore
        self.eng.close()
        if consts.DEBUG:
            self.eng = engine.BinggoEngine(debug_file="eng_rate.log")
        else:
            self.eng = engine.BinggoEngine()
        self.do_rate = True
        self.thread_rate_begin()

    def quit(self):
        self.do_rate = False
        self.stop_current_rate()
        self.eng.close()
