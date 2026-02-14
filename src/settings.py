from string import Template
import os
import json
import logging
from typing import Literal, Optional

from src import variable as var
from src import ChessPieceSetup as cps

logger = logging.getLogger(__name__)


class BaseButton:
    def __init__(self, name: str, rect=None, shade_time_max=10):
        if rect is not None:
            if not (len(rect) == 4 and all((0 <= i <= 1) for i in rect)):
                logger.error("rect参数错误")
                raise ValueError("rect参数错误")
        self.name = name
        self.rect = rect
        self.shade_time_max = shade_time_max
        self.shade_time = 0
    
    @property
    def current_text(self):  return self.name

    def __str__(self):  return f"{self.__class__} {self.name} at {self.rect}"

    def is_clicked(self, x, y) -> bool:
        if self.rect is None:
            logger.error("rect未初始化")
            return False
        return self.rect[0]<x<self.rect[0]+self.rect[2] and self.rect[1]<y<self.rect[1]+self.rect[3]

    def press(self) -> Literal[""]:
        # do nothing by default
        self.shade_time = self.shade_time_max
        return ""

    def tick_update(self, *args):
        self.shade_time = max(0, self.shade_time-var.anim_speed)


class PressBtn(BaseButton):
    def __init__(self, name: str, cmd: str, 
                 rect=None, shade_time_max=10):
        super().__init__(name, rect, shade_time_max)
        self.cmd = cmd

    def press(self) -> str:
        """返回需要执行的命令"""
        self.shade_time = self.shade_time_max
        return self.cmd


class SettingBtn(BaseButton):
    def __init__(self, name: str,
                 cmds: dict[str, str], 
                 name_explicit=False,
                 n: int = 0,
                 rect: Optional[tuple[float, float, float, float]] = None,
                 shade_time_max=10):
        super().__init__(name, rect, shade_time_max)
        self.name_explicit = name_explicit; self.cmds = cmds; self.n = n
        self.names:    list[str] = [f'{name}: {s}' for s in cmds.keys()] if name_explicit else list(cmds.keys())
        self.commands: list[str] = list(self.cmds.values())

    def press(self) -> str:
        """返回需要执行的命令"""
        self.n = (self.n + 1) % len(self.cmds)
        self.shade_time = self.shade_time_max
        return self.commands[self.n]

    @property
    def current_text(self) -> str:
        return self.names[self.n]


class Menu:
    def __init__(self, buttons: list[BaseButton], element_per_line_max=2):
        self.buttons = buttons
        assert all(isinstance(elem, BaseButton) for elem in self.buttons)
        if element_per_line_max > 0:
            self.sort_menu_elements_rect(element_per_line_max)
    
    def __getitem__(self, index: int | str) -> BaseButton:
        if isinstance(index, int):
            self.buttons[index]
        elif isinstance(index, str):
            for elem in self.buttons:
                if elem.name == index:
                    return elem
        raise IndexError(f"cannot find btn {index} in menu {self.buttons}")
    
    def __len__(self) -> int:  return len(self.buttons)

    def __str__(self):  return "Menu with btns: " + str(self.buttons)

    def __iter__(self):  return iter(self.buttons)
    
    def sort_menu_elements_rect(self, element_per_line_max=2) -> None:
        line_count = 0
        per_line_count = 0
        line_d = 0.1 #行距
        side_d = 0.2 #边距
        top_d = 0.3 #顶端优势
        elem_d = (1 - 2*side_d)/(element_per_line_max*4-1)*4 #元素间距

        elex = elem_d * (3/4) #元素宽
        eley = line_d / 2

        for elem in self.buttons:
            if elem.rect is not None:
                continue
            _temp_rect = (side_d+per_line_count*elem_d, top_d+line_count*line_d, elex, eley)
            elem.rect = _temp_rect

            per_line_count += 1
            if per_line_count >= element_per_line_max:
                line_count += 1
                per_line_count = 0


class EngineStg:
    repl_dict: dict[str, dict[int, str]] = {
        "queen_inf": {
            0: "q:B3R3",
            1: "q:BR",
            # 2: "q:WDHFNCAZG",
        },
        "white_promo": {
            0: "pawnTypes = p",
            1: "pawnTypes = po\npromotionPawnTypesWhite = o\n"
               "promotionPieceTypesWhite = jcaxsm\npromotionRegionWhite = *9",
        },
        "king_enter_palace": {
            0: "mobilityRegionBlackCustomPiece9  = a1 a2 a3 b1 b2 b3 c1 c2 c3 g1 g2 g3 h1 h2 h3 i1 i2 i3 *4 *5 *6 *7 *8 *9",
            1: "",
        },
    }
    text_dict: dict[str, dict[int, str]] = {
        "皇后最远移动距离": {
            0: "不超过三",
            1: "无限",
            # 2: "WDHFNCAZG",
        },
        "中国象棋中卒的升变": {
            0: "禁止",
            1: "底线升变",
        },
        "国象中王进入九宫": {
            0: "不允许",
            1: "允许",
        },
    }
    swit_default = {
        "queen_inf": 0, "white_promo": 1, "king_enter_palace": 0
    }
    assert len(repl_dict) == len(text_dict) == len(swit_default)

    ini_template = """
[binggo]
maxRank = 9
maxFile = 9

; Note that fen and some pieces might be declared twice
startFen = rnbk1qnbr/pppp1pppp/9/9/9/O1O1O1O1O/1A5A1/9/CMXSWSXMC w kq - 0 1

customPiece1 = j:NB2RmpRcpR
customPiece2 = x:B2
customPiece3 = o:fsW
customPiece4 = s:K
customPiece5 = a:mRpR
customPiece6 = c:R
customPiece7 = w:W
customPiece8 = m:nN

customPiece9 = k:K
customPiece10 = $queen_inf
customPiece11 = r:R
customPiece12 = b:B
customPiece13 = n:N
customPiece14 = p:mfWcfFimfR2

; Redeclare
$BLANK

$white_promo
promotionPawnTypesBlack = p
promotionPieceTypesBlack = rqnb
promotionRegionBlack = *1
enPassantRegion = -

castling = true
castlingKingPiece = k
castlingRookPiece = r
castlingKingFile = d
castlingKingsideFile = f
castlingRookKingsideFile = i
castlingQueensideFile = b
castlingRookQueensideFile = a

checking = true
doubleStep = true
doubleStepRegionBlack = *8
; doubleStepRegionWhite = *4

extinctionPieceTypes = Wk
extinctionValue = loss
extinctionPseudoRoyal = true
perpetualCheckIllegal = true
moveRepetitionIllegal = true

nFoldRule = 4
nFoldValue = loss
nFoldValueAbsolute = true
stalemateValue = loss

mobilityRegionWhiteCustomPiece7 = d1 e1 f1 d2 e2 f2 d3 e3 f3
$king_enter_palace

; pieceToCharTable https://www.gnu.org/software/xboard/whats_new/4.9.0/index.html#tag-B1
"""

    def __init__(self) -> None:
        # yo absolutely cool!! TEMPLATE!! hiahiahia~
        self.template = Template(EngineStg.ini_template)
        self.switches: dict[str, int] = EngineStg.swit_default
        self.redeclares: dict[str, str] = {}
        self.load_from_default()
    
    # def __getitem__(self, key: str) -> int:
    #     return self.switches[key]
    
    # def __setitem__(self, key: str, value: int) -> None:
    #     self.switches[key] = value
    
    # def __len__(self) -> int:
    #     return len(self.switches)
    
    def __iter__(self):  raise NotImplementedError
    
    def load_from_default(self) -> None:
        try:
            with open('userdata\\engine_setting.json', 'r', encoding='ascii') as f:
                self.load_from_json(f.read())
        except FileNotFoundError as e:
            logger.warning("读取引擎设置失败，使用默认值 " + str(e))
    
    def load_from_json(self, f: str) -> None:
        _ = json.loads(f)
        self.switches   = _.get('switches')   or EngineStg.swit_default
        self.redeclares = _.get('redeclares') or {}

    def export_to_json(self) -> str:
        return json.dumps({
            'switches': self.switches,
            'redeclares': self.redeclares,
        })
    
    def save_to_json(self) -> None:
        if not os.path.exists('userdata'):  os.mkdir('userdata')
        with open('userdata\\engine_setting.json', 'w', encoding='ascii') as f:
            json.dump({
                'switches': self.switches,
                'redeclares': self.redeclares,
            }, f)
    
    def export_to_ini(self) -> str:
        sub_dict: dict[str, str] = {}
        for key, value in self.switches.items():
            sub_dict[key] = EngineStg.repl_dict[key][value]
        return self.template.substitute(**sub_dict, BLANK=cps.format_redeclares(self.redeclares))
    
    def write_to_ini(self) -> None:
        with open('engine\\binggo.ini', 'w', encoding='UTF-8') as f:
            f.write(self.export_to_ini())
    
    def export_to_text(self) -> str:
        return "基本规则:\n" + ",\n".join([
            f"  {k}: {d[opt]}" for (_, opt), (k, d) in 
                zip(self.switches.items(), EngineStg.text_dict.items())
        ]) + "." + "\n\n实验修改: " + json.dumps(self.redeclares, indent=2)


if __name__ == '__main__':
    e = EngineStg()
    print(e.export_to_ini())
