import asyncio
import aiohttp
import json
import random
from struct import pack
import zlib
import time
import traceback
import Tools
import os


class DanmakuClient:
    def __init__(self, rid):
        self.heartbeat = b'\x00\x00\x00\x1f\x00\x10\x00\x01\x00\x00\x00\x02\x00\x00\x00\x01\x5b\x6f\x62\x6a\x65\x63\x74\x20' \
                b'\x4f\x62\x6a\x65\x63\x74\x5d '
        self.heartbeatInterval = 60
        self.start_time = None
        self.rid = rid
        self.__ws = None
        self.ws_url = 'wss://broadcastlv.chat.bilibili.com/sub'
        self.__stop = False
        self.filename = self.__init_file_path()
        self.__hs = aiohttp.ClientSession()

    def __init_file_path(self):
        path = f"./res/{self.rid}/"
        if not os.path.exists(path):
            os.makedirs(path)
        filename = f'{time.strftime("%Y-%m-%d-%H-%M", time.localtime())}.csv'
        return os.path.join(path, filename)

    async def init_ws(self):
        reg_datas = await self.get_ws_info()
        self.__ws = await self.__hs.ws_connect(self.ws_url)
        if reg_datas:
            for reg_data in reg_datas:
                await self.__ws.send_bytes(reg_data)

    async def heartbeats(self):
        while not self.__stop and self.heartbeat:
            await asyncio.sleep(self.heartbeatInterval)
            try:
                await self.__ws.send_bytes(self.heartbeat)
            except Exception:
                pass
        Tools.log_info('{} 直播间停止直播，已停止向服务器发送心跳协议。'.format(self.rid))

    async def fetch_danmaku(self):
        while not self.__stop:
            await asyncio.sleep(1)
            await self.init_ws()
            await asyncio.sleep(1)
            async for msg in self.__ws:
                state = self.decode_msg(msg.data, self.filename,
                                        self.start_time, self.rid)
                if state == -1:
                    await self.stop()
                    break
        Tools.log_info('{} 直播间停止直播，已停止持续拉取消息。'.format(self.rid))

    async def start(self):
        self.start_time = time.time()
        await asyncio.gather(
            self.heartbeats(),
            self.fetch_danmaku(),
        )
        Tools.log_info('{} 直播间停止直播，已关闭 wss 连接，停止对其弹幕的爬取。'.format(self.rid))

    async def stop(self):
        self.__stop = True
        await self.__hs.close()

    async def get_ws_info(self):
        url = f'https://api.live.bilibili.com/room/v1/Room/room_init?id={self.rid}'
        reg_datas = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                room_json = json.loads(await resp.text())
                room_id = room_json['data']['room_id']
                data = json.dumps(
                    {
                        'roomid': room_id,
                        'uid': int(1e14 + 2e14 * random.random()),
                        'protover': 1
                    },
                    separators=(',', ':')).encode('ascii')
                data = (pack('>i',
                             len(data) + 16) + b'\x00\x10\x00\x01' +
                        pack('>i', 7) + pack('>i', 1) + data)
                reg_datas.append(data)

        return reg_datas

    def decode_msg(self, data, filename, start_time, roomid):
        try:
            # 获取数据包的长度，版本和操作类型
            if data.hex()[:18] == '000000140010000100000003000000000000':
                return []
            res = []
            packetLen = int(data[:4].hex(), 16)
            ver = int(data[6:8].hex(), 16)
            op = int(data[8:12].hex(), 16)

            # 有的时候可能会两个数据包连在一起发过来，所以利用前面的数据包长度判断，
            if (len(data) > packetLen):
                self.decode_msg(data[packetLen:], filename, start_time, roomid)
                data = data[:packetLen]

            # 有时会发送过来 zlib 压缩的数据包，这个时候要去解压。
            if (ver == 2):
                data = zlib.decompress(data[16:])
                self.decode_msg(data, filename, start_time, roomid)
                return []

            # ver 为1的时候为进入房间后或心跳包服务器的回应。op 为3的时候为房间的人气值。
            if (ver == 1):
                if (op == 3):
                    Tools.log_info('[RENQI] {} 直播间人气 {}'.format(
                        roomid, int(data[16:].hex(), 16)))
                    if int(data[16:].hex(), 16) == 1:
                        return -1
                else:
                    Tools.log_info(data)
                return []

            # ver 不为2也不为1目前就只能是0了，也就是普通的 json 数据。
            # op 为5意味着这是通知消息，cmd 基本就那几个了。
            if op == 5:
                try:
                    jd = json.loads(data[16:].decode('utf-8', errors='ignore'))
                    res.append([time.ctime(), jd])
                    with open(filename, 'a', encoding='utf-8') as f:
                        f.write(str(time.time() - start_time) + ',')
                        f.write(str(time.ctime()) + ',')
                        f.write(str(jd) + '\n')
                    if jd['cmd'] == 'STOP_LIVE_ROOM_LIST':  # 停止直播的直播间列表
                        if roomid in jd['data']['room_id_list']:
                            Tools.log_info(
                                '[STOP_LIVE]  {} 直播间停止直播，即将停止对其弹幕的爬取。'.format(
                                    roomid))
                            return -1
                except Exception as e:
                    Tools.log_error(
                        f'Receive message err:{e.args} \n {traceback.format_exc()}'
                    )
            else:
                jd = json.loads(data[16:].decode('utf-8', errors='ignore'))
                Tools.log_warn(f"OP IS NOT EQUALS 5!\n jd:{jd}")
        except json.decoder.JSONDecodeError as e:
            Tools.log_warn(f"Json decode err: data={data}")
        return []


async def main(rid):
    await DanmakuClient(rid).start()


if __name__ == '__main__':
    ASYNC_LOOP = asyncio.get_event_loop()
    ASYNC_LOOP.run_until_complete(main('21067393'))  #
