import time
import logging
import json

from src import variable as var
from src import consts
from src import engine as fsf

logger = logging.getLogger(__name__)

c2p = {'J':0,'C':1,'M':2,'X':3,'S':4,'A':5,'W':6,'O':7,'r':8,'b':9,'n':10,'q':11,'k':12,'p':13}
p2c = {0:'J',1:'C',2:'M',3:'X',4:'S',5:'A',6:'W',7:'O',8:'r',9:'b',10:'n',11:'q',12:'k',13:'p',-1:''}

a2n = {'a':0,'b':1,'c':2,'d':3,'e':4,'f':5,'g':6,'h':7,'i':8}
n2a = {0:'a',1:'b',2:'c',3:'d',4:'e',5:'f',6:'g',7:'h',8:'i'}

try:
    with open('userdata\\engine_setting.json', 'r', encoding='ascii') as f:
        var.init_fen = json.load(f)['redeclares']['startFen']
except:
    logger.debug('no engine setting file found')

def fsf2beach(p):
    return a2n[p[0]] + (9 - int(p[1])) * 9

def beach2fsf(p):
    return n2a[p%9] + str(9 - p//9)

class Beach:
    """ 用途：记录当前局面便于显示调用 + 调用引擎。 fen = pieces + extra """
    def __init__(self, fen=var.init_fen):
        self.beach = []
        for char in fen.replace('/',''):
            if char == ' ':
                break
            if char.isnumeric():
                self.beach += [-1]*int(char)
            else:
                self.beach.append(c2p[char])
        self.fen = fen
        self.initial_fen = fen
        if consts.DEBUG:
            self.eng = fsf.BinggoEngine(debug_file="eng_beach.log")
        else:
            self.eng = fsf.BinggoEngine()

    def __getitem__(self, item):
        return self.beach[item]

    def __setitem__(self, key, value):
        self.beach[key] = value
        self.beach2fen()

    def fen2beach(self, fen):
        self.beach = []
        self.fen = fen
        for char in fen.replace('/', ''):
            if char == ' ':
                break
            if char.isnumeric():
                self.beach += [-1] * int(char)
            else:
                self.beach.append(c2p[char])
        if len(self.beach) != 81:
            error_msg = 'beach must contain 81 elements'
            logger.error(error_msg)
            raise IndexError(error_msg)

    def beach2fen(self):
        pieces = ''; n = 0; lc = 0
        for num in self.beach:
            lc += 1
            if num < 0:
                n += 1
            if lc == 9:
                pieces += (str(n) + p2c[num] if n > 0 else p2c[num]) + '/'
                n = 0; lc = 0
            elif num >= 0:
                pieces += str(n) + p2c[num] if n > 0 else p2c[num]
                n = 0
        self.fen = pieces[:-1] + f' w kq - 0 1'

    def reset(self, fen = None, force = False):
        if force:
            self.fen = self.initial_fen = var.init_fen
            self.fen2beach(self.fen)
            return
        if fen is None:
            self.fen = self.initial_fen
        else:
            self.fen = self.initial_fen = fen
        self.fen2beach(self.fen)


    def get_best_move(self, think_time = 2000):
        """ 当前局面引擎解法 """
        st = time.time()
        move = self.eng.best_move(self.fen, movetime=think_time)[0]
        _t = time.time() - st
        if _t < 200:
            time.sleep(0.2)
        return move

    def get_pms(self, p = None):
        all_pms = self.eng.pms(self.fen)
        if p is None:
            return [fsf2beach(_p[2:4]) for _p in all_pms], all_pms == []
        p = beach2fsf(p)
        res = set()
        for move in all_pms:
            if move[:2] == p:
                res.add(fsf2beach(move[2:4]))
        return res, all_pms == []

    def moves_reset(self,moves:list):
        self.fen = self.eng.perform_move(self.initial_fen, moves)
        self.fen2beach(self.fen)
    
    def suicide(self):
        self.eng.close()

    def reboot_engine(self):
        self.suicide()
        if consts.DEBUG:
            self.eng = fsf.BinggoEngine(debug_file="eng_beach.log")
        else:
            self.eng = fsf.BinggoEngine()
