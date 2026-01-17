import time
import logging
from threading import Thread
import engine
import constant as consts


logger = logging.getLogger(__name__)

class RatingSystem:
    def __init__(self):
        if consts.DEBUG:
            self.eng = engine.BinggoEngine(debug_file="eng_rate.log")
        else:
            self.eng = engine.BinggoEngine()
        self.score = 0
        self.rating_thread = None
        self.fen = None
        self.rating_time = 100
        self.do_rate = True

    def _tr(self):
        while self.do_rate:
            try:
                self.score = self.eng.analyze(self.fen,movetime=self.rating_time)
            except RuntimeError as e:
                logger.warning(f"Runtime error during analysis: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during analysis: {e}")
            if self.rating_time < 10000:
                self.rating_time *= 2
            else:
                time.sleep(0.2)

    def stop_current_rate(self):
        self.eng.stop()

    def thread_rate_begin(self):
        self.rating_thread = Thread(target=self._tr)
        self.rating_thread.start()

    def refresh_fen(self, fen):
        self.fen = fen
        self.rating_time = 100
        self.stop_current_rate()

    def reboot(self):
        self.do_rate = False
        self.stop_current_rate()
        self.rating_thread.join()
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
