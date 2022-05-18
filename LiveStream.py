import requests
import time
import random
import os
import Tools

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
# 取消注释可以去掉出现的警告


class LiveVideoDownload(object):
    def __init__(self, rid):
        self.headers = {
            'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.18362'
        }
        self.rid = rid
        self.filename = self.__init_file_path()

    def __init_file_path(self):
        path = f"./res/{self.rid}/"
        if not os.path.exists(path):
            os.makedirs(path)
        filename = f'{time.strftime("%Y-%m-%d-%H-%M", time.localtime())}.flv'
        return os.path.join(path, filename)

    def get_real_url(self):
        # 先获取直播状态和真实房间号
        url = f'https://api.live.bilibili.com/room/v1/Room/room_init?id={self.rid}'
        with requests.Session() as s:
            res = s.get(url).json()
        if res['code'] == 0:
            if res['data']['live_status'] == 1:  # 正在直播 可以获取视频流
                room_id = res['data']['room_id']
                f_url = 'https://api.live.bilibili.com/xlive/web-room/v1/playUrl/playUrl'
                params = {'cid': room_id, 'platform': 'web', 'qn': 250}
                resp = s.get(f_url, params=params).json()
                return resp['data']['durl'][0]['url']
            else:
                return '未开播'
        elif res['code'] == -412:
            raise Exception('请求被拦截')
        elif res['code'] == 60004:
            raise Exception('房间不存在')
        else:
            print(res)

    def download(self):
        headers = self.headers
        # 下载
        size = 0
        chunk_size = 1024
        size_scope = 1024 * 1024
        with requests.Session() as s:
            with open(self.filename, 'wb') as f:
                i = 0
                while i <= 100:
                    i += 1
                    Tools.log_info(
                        f'{self.rid} Connecting to server. Try Times:{i}')
                    url = self.get_real_url()
                    if url == "未开播":
                        Tools.log_warn(f"{self.rid} was not on live.")
                        break
                    res = s.get(url, headers=headers, stream=True)
                    for chunk in res.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            size += len(chunk)
                            if size >= size_scope:
                                Tools.log_info(
                                    f"{self.rid} 下载中，已完成 {size / 1024 / 1024} MB "
                                )
                                size_scope += size_scope * random.random()
                    if res.status_code == 200:
                        Tools.log_info(
                            f'{self.rid} 下载完成，共计 {size / 1024 / 1024} MB ...')
                    time.sleep(1)
                if i > 50:
                    Tools.log_warn(
                        f'{self.rid} 下载失败，请检查网络环境,或者进入直播间查看直播状态，尝试次数过多（{i} 次），请稍后再试'
                    )
        Tools.log_info(f'已结束对 {self.rid} 直播间视频的爬取。')


if __name__ == '__main__':
    rid = '21809291'  # rid 号
    liveVideo = LiveVideoDownload(rid=rid)
    liveVideo.download()
