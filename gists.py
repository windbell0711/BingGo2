"""
-*- coding: utf-8 -*-
由BingGo v1.2中gists.py改写
https://gitee.com/api/v5/swagger#/getV5Gists
"""
import requests
import time
from typing import Dict, Optional, Any


class Gist:
    """Gist客户端类，封装Gitee Gist的API操作"""
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
                print(f"创建会话失败，状态码：{response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"网络错误：{str(e)}")
        
        return None
    
    def _get_gist_data(self) -> Optional[Dict[str, Any]]:
        """
        获取Gist数据

        :return data: 获取的Gist数据字典，成功返回字典，失败返回None
        """
        if not self.gist_id:
            print("错误：未设置gist_id")
            return None
            
        try:
            response = requests.get(f"{self.api_url}{self.gist_id}", 
                                   params={"access_token": self.access_token})
            if response.status_code == 200:
                return response.json()
            else:
                print(f"获取Gist数据失败，状态码：{response.status_code}")
        except Exception as e:
            print(f"网络错误：{str(e)}")
        
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
                    print(f"文件 '{file_name}' 已更新")
                    self.last_read_content[file_name] = current_content
                    return current_content
            except FileNotFoundError:
                # 文件可能被删除，但之前存在过，所以等待它重新出现
                pass
            except Exception as e:
                print(f"读取文件时出错：{str(e)}")
            
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
            print("错误：未设置gist_id")
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
                print(f"文件 '{file_name}' 写入成功")
                return True
            else:
                print(f"写入文件失败，状态码：{response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"网络错误：{str(e)}")
        
        return False
    
    def check_internet(self) -> bool:
        """
        检查网络连接
        
        :return: 网络连接正常返回True，否则返回False
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
        :param needs_waiting: 是否只需要等待状态的会话
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
                print(f"查找会话失败，状态码：{response.status_code}")
        except Exception as e:
            print(f"网络错误：{str(e)}")
        
        return None


# 使用示例
if __name__ == "__main__":
    # 初始化Gist客户端
    ACCESS_TOKEN = "f61fe45a79fd154f0702452879068865"  # 请替换为你的访问令牌
    gist = Gist(ACCESS_TOKEN)
    
    # 检查网络连接
    print(f"网络连接: {gist.check_internet()}")
    
    # 示例1: 创建会话
    room_name = "test_room"
    initial_files = {
        "status.txt": "hello gists!",
        "player1.txt": "喵",
        "player2.txt": "喵喵",
    }
    
    gist_id = gist.create_session(room_name, initial_files)
    if gist_id:
        print(f"会话创建成功，ID: {gist_id}")
        gist.gist_id = gist_id  # 设置当前操作的gist_id
    else:
        print("会话创建失败")
        # 使用示例gist_id进行后续测试
        gist.gist_id = "existing_gist_id_here"
    
    try:
        # 示例2: 读取文件
        content = gist.read_file("status.txt")
        print(f"{gist.read_file("status.txt") = }")
        print(f"{gist.read_file("player1.txt") = }")
        print(f"{gist.read_file("player2.txt") = }")
        
        # 示例3: 写入文件
        success = gist.write_file("player1.txt", "啊啊啊啊要不行了")
        print(f"写入结果: {success}")
        print(f"{gist.read_file("status.txt") = }")
        print(f"{gist.read_file("player1.txt") = }")
        print(f"{gist.read_file("player2.txt") = }")
        
        # 示例4: 等待文件更新（需要另一个进程或手动更新文件内容）
        # print("等待player2.txt更新...")
        # 注意：这行代码会阻塞，直到文件内容更新
        # updated_content = gist.wait_for_update("player2.txt")
        # print(f"更新后的内容: {updated_content}")
        
    except FileNotFoundError as e:
        print(f"文件错误: {e}")
    
    # 示例5: 查找会话
    session_id = gist.find_session_id("test_room")
    if session_id:
        print(f"找到会话ID: {session_id}")
