import engine as fsf

c2p = {'J':0,'C':1,'M':2,'X':3,'S':4,'A':5,'W':6,'O':7,'r':8,'b':9,'n':10,'q':11,'k':12,'p':13}
p2c = {0:'J',1:'C',2:'M',3:'X',4:'S',5:'A',6:'W',7:'O',8:'r',9:'b',10:'n',11:'q',12:'k',13:'p',-1:''}

a2n = {'a':0,'b':1,'c':2,'d':3,'e':4,'f':5,'g':6,'h':7,'i':8}
n2a = {0:'a',1:'b',2:'c',3:'d',4:'e',5:'f',6:'g',7:'h',8:'i'}

initial_fen = 'rnbk1qnbr/pppp1pppp/9/9/9/O1O1O1O1O/1A5A1/9/CMXSWSXMC w kq - 0 1'

def fsf2beach(p):
    return a2n[p[0]] + (9 - int(p[1])) * 9

def beach2fsf(p):
    return n2a[p%9] + str(9 - p//9)

class Beach:
    """ 用途：记录当前局面便于显示调用 + 调用引擎。 fen = pieces + extra """
    def __init__(self, fen = initial_fen):
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

    def beach2fen(self):
        pieces = ''; n = 0; lc = 0; cas=''
        if self.beach[3] == 12 and self.beach[8] == 8:
            cas += 'k'
        if self.beach[3] == 12 and self.beach[0] == 8:
            cas += 'q'
        if cas == '':
            cas = '-'
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
        self.fen = pieces[:-1] + f' w {cas} - 0 1'

    def get_best_move(self, think_time = 2000):
        """ 当前局面引擎解法 """
        move = self.eng.best_move(self.fen, think_time=think_time)[0]
        return move

    def apply_move(self, move):
        self.fen = self.eng.perform_move(self.fen, move)
        self.fen2beach(self.fen)

    def get_pms(self, p = None):
        all_pms = self.eng.pms(self.fen)
        if p is None:
            return [fsf2beach(_p[2:4]) for _p in all_pms]
        p = beach2fsf(p)
        res = set()
        for move in all_pms:
            if move[:2] == p:
                res.add(fsf2beach(move[2:4]))
        return res

    def moves_reset(self,moves:list):
        self.fen = self.eng.perform_move(self.initial_fen, moves)
        self.fen2beach(self.fen)
    
    def suicide(self):
        self.eng.close()


if __name__ == '__main__':
    board = Beach()
    print(board.fen)
    board.apply_move('e1e2')
    board.apply_move('a8a6')
    board.apply_move('e2e1')
    board.apply_move('a9a7')
    print(board.fen)
    board.suicide()