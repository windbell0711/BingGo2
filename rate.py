import time
from threading import Thread
import engine


class RatingSystem:
    def __init__(self):
        self.eng = engine.BinggoEngine(debug_file="rate.log")
        self.score = 0
        self.rating_thread = None
        self.fen = None
        self.rating_time = 100
        self.do_rate = True

    def _tr(self):
        while self.do_rate:
            try:
                self.score = self.eng.analyze(self.fen,movetime=self.rating_time)
            except RuntimeError:
                pass
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
        self.eng = engine.BinggoEngine(debug_file="rate.log")
        self.do_rate = True
        self.thread_rate_begin()

    def quit(self):
        self.do_rate = False
        self.stop_current_rate()
        self.eng.close()
