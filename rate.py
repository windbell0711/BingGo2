import engine
from threading import Thread

class RatingSystem:
    def __init__(self):
        self.eng = engine.BinggoEngine()
        self.score = 0
        self.rating_thread = None
        self.fen = None
        self.rating_depth = 8
        self.do_rate = True

    def _tr(self):
        while self.do_rate:
            self.score = self.eng.analyze(self.fen, depth=self.rating_depth)
            if self.rating_depth < 40:
                self.rating_depth += 1

    def stop_current_rate(self):
        self.eng.stop()

    def thread_rate_begin(self):
        self.rating_thread = Thread(target=self._tr)
        self.rating_thread.start()

    def refresh_fen(self, fen):
        self.fen = fen
        self.rating_depth = 8
        self.stop_current_rate()

    def reboot(self):
        self.do_rate = False
        self.stop_current_rate()
        self.rating_thread.join()
        self.eng.close()
        self.eng = engine.BinggoEngine()
        self.do_rate = True
        self.thread_rate_begin()

    def quit(self):
        self.do_rate = False
        self.stop_current_rate()
        self.eng.close()
