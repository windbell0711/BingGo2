"""
-*- coding: utf-8 -*-
由BingGo v1.2中gists.py改写
https://gitee.com/api/v5/swagger#/getV5Gists
"""
import requests
import json
import time
import logging
from typing import Dict, Optional, Any, Literal

from src import variable as var
from src.consts import ACCESS_TOKEN
from src.LogMsgboxManager import MsgLog

logger = logging.getLogger(__name__)
msglog = MsgLog(logger, var.root)


class Gist:
    def __init__(self, access_token: str):
        """
        初始化Gist客户端
        :param access_token: Gitee访问令牌
        """
        self.access_token = access_token
        self.api_url = "https://gitee.com/api/v5/gists/"
        self.gist_id = None
        self.last_read_content = {}  # 存储每个文件上次读取的内容
        
    def create_session(self, room_name: str, 
                       files: Dict[str, str]) -> Optional[str]:
        """
        创建Gist会话

        :param room_name: 房间名称
        :param files: 字典，键为文件名，值为文件内容
        :return gist_id: 成功返回gist_id，失败返回None
        """
        payload = {
            "access_token": self.access_token,
            "files": {file_name: {"content": content} for file_name, content in files.items()},
            "description": room_name,
            "public": "false"
        }
        
        try:
            response = requests.post(self.api_url, json=payload)
            if response.status_code == 201:
                self.gist_id = response.json()["id"]
                # 初始化上次读取内容
                for file_name in files.keys():
                    self.last_read_content[file_name] = files[file_name]
                return self.gist_id
            else:
                logger.error(f"创建会话失败，状态码：{response.status_code}")
                logger.error(response.text)
        except Exception as e:
            logger.error(f"网络错误：{str(e)}")
        
        return None
    
    def _get_gist_data(self) -> Optional[Dict[str, Any]]:
        """
        获取Gist数据

        :return data: 获取的Gist数据字典，成功返回字典，失败返回None
        """
        if not self.gist_id:
            logger.error("错误：未设置gist_id")
            return None
            
        try:
            response = requests.get(f"{self.api_url}{self.gist_id}", 
                                   params={"access_token": self.access_token})
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"获取Gist数据失败，状态码：{response.status_code}")
        except Exception as e:
            logger.error(f"网络错误：{str(e)}")
        
        return None
    
    def read_file(self, file_name: str) -> str:
        """
        读取指定文件的内容

        :param file_name: 文件名
        :return file_content: 文件内容
        :raises: FileNotFoundError: 文件不存在时抛出
        """
        gist_data = self._get_gist_data()
        if not gist_data:
            raise FileNotFoundError("无法获取Gist数据")
        
        files = gist_data.get("files", {})
        if file_name not in files:
            raise FileNotFoundError(f"文件 '{file_name}' 不存在")
        
        content = files[file_name].get("content", "")
        # 更新上次读取内容
        self.last_read_content[file_name] = content
        return content
    
    def wait_for_update(self, file_name: str, 
                        check_interval: float = 3.0) -> str:
        """
        阻塞直到指定文件的内容更新

        :param file_name: 文件名
        :param check_interval: 检查间隔（秒）
        :return file_content: 更新后的文件内容
        :raises FileNotFoundError: 文件不存在时抛出
        """
        # 初始化上次读取内容（如果未记录）
        if file_name not in self.last_read_content:
            try:
                self.last_read_content[file_name] = self.read_file(file_name)
            except FileNotFoundError:
                raise FileNotFoundError(f"文件 '{file_name}' 不存在")
        
        last_content = self.last_read_content[file_name]
        
        while True:
            try:
                current_content = self.read_file(file_name)
                if current_content != last_content:
                    logger.info(f"文件 '{file_name}' 已更新")
                    self.last_read_content[file_name] = current_content
                    return current_content
            except FileNotFoundError:
                # 文件可能被删除，但之前存在过，所以等待它重新出现
                pass
            except Exception as e:
                logger.error(f"读取文件时出错：{str(e)}")
            
            time.sleep(check_interval)
    
    def write_file(self, file_name: str, content: str) -> bool:
        """
        向指定文件写入内容

        :param file_name: 文件名
        :param content: 要写入的内容
        :return success: 成功返回True，失败返回False
        :raises FileNotFoundError: 文件不存在时抛出
        """
        if not self.gist_id:
            logger.error("错误：未设置gist_id")
            return False
        
        # 首先检查文件是否存在
        gist_data = self._get_gist_data()
        if not gist_data:
            raise FileNotFoundError("无法获取Gist数据")
        
        files = gist_data.get("files", {})
        if file_name not in files:
            raise FileNotFoundError(f"文件 '{file_name}' 不存在")
        
        # 更新文件内容
        payload = {
            "access_token": self.access_token,
            "files": {file_name: {"content": content}}
        }
        
        try:
            response = requests.patch(f"{self.api_url}{self.gist_id}", json=payload)
            if response.status_code == 200:
                # 更新上次读取内容
                self.last_read_content[file_name] = content
                logger.info(f"文件 '{file_name}' 写入成功")
                return True
            else:
                logger.error(f"写入文件失败，状态码：{response.status_code}")
                logger.error(response.text)
        except Exception as e:
            logger.error(f"网络错误：{str(e)}")
        
        return False
    
    def check_internet(self) -> bool:
        """
        检查网络连接是否正常
        """
        try:
            response = requests.get(f"{self.api_url}mva7dgrzfkxw58b9ipet383",
                                    params={"access_token": self.access_token},
                                    timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def find_session_id(self, description: str, 
                        needs_waiting: bool = True) -> Optional[str]:
        """
        查找指定描述的会话ID

        :param description: 会话描述
        :param needs_waiting: 是否只需要等待状态的会话 现在没啥用好像
        :return session_id: 会话ID，未找到返回None
        """
        try:
            response = requests.get(f"{self.api_url}", params={
                "access_token": self.access_token,
                "since": time.strftime('%Y%m%d'),
                "page": 1,
                "per_page": 15,
            })
            
            if response.status_code == 200:
                gists = response.json()
                for gist in gists:
                    if gist.get("description") == description:
                        if not needs_waiting:
                            return gist.get("id")
                        # 检查是否包含等待状态
                        files = gist.get("files", {})
                        for file_info in files.values():
                            if "waiting" in file_info.get("content", ""):
                                return gist.get("id")
            else:
                logger.error(f"查找会话失败，状态码：{response.status_code}")
        except Exception as e:
            logger.error(f"网络错误：{str(e)}")
        
        return None


class Messager(Gist):
    """注意，main.json只允许你说一句，我说一句，不能说两句！"""

    # 建议调用api间隔：1~3秒，不要过于频繁

    def __init__(self, access_token: str, idt: Literal['home', 'away']):
        super().__init__(access_token)
        self.files = ["main.json"]
        self.idt = idt

    def 开大床房(self, rule_stg: str) -> Optional[bool]:
        room = msglog.askstring("请输入新房间名:")
        if not room:  return None
        if not self.create_session(
            room_name=room, 
            files={i: json.dumps([
                time.time(),
                'waiting',
                rule_stg,
            ]) for i in self.files}
        ):
            return False
        return True

    def 进去了哦(self) -> Optional[str]:
        """返回对方的规则json或None"""
        room = msglog.askstring("请输入对方创建的房间名:")
        if not room:
            msglog.error(msg:='房间名未输入，无法启动联机。')
            return
        ret = self.find_session_id(room, needs_waiting=True)
        if not ret:
            msglog.error(msg:='未找到指定房间，无法启动联机。')
            return
        self.gist_id = ret
        t, s, msg = json.loads(self.read_file("main.json"))
        if s != 'waiting':
            msglog.warning(msg:=f'可能找到了错误的房间，无法同步规则设置，请确保房间已创建，且房间名不要过于常见。\n上一条消息时间：{t}, 发送者：{s}')
            return
        return msg

    def send(self, msg: str) -> bool:
        return self.write_file(
            file_name="main.json",
            content=json.dumps([
                int(time.time()),
                self.idt,
                msg,
            ])
        )

    def get(self) -> Optional[str]:
        t, s, msg = json.loads(self.read_file("main.json"))
        if s == self.idt or s == 'waiting':  return None
        return msg
        