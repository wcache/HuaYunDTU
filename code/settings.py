import uos
import ql_fs
import modem
import _thread
from usr.modules.common import Singleton


PROJECT_NAME = "QuecPython-Dtu"
PROJECT_VERSION = "3.0.0"
DEVICE_FIRMWARE_NAME = uos.uname()[0].split("=")[1]
DEVICE_FIRMWARE_VERSION = modem.getDevFwVersion()


DEFAULT = {
    "system_config": {
        "cloud": "onenet",
        "base_function": {
            "sota": True,
            "fota": True
        }
    },
    "tcp_private_cloud_config": {
        "server": "a15fbbd7ce.iot-mqtts.cn-north-4.myhuaweicloud.com",
        "port": "1883",
        "keep_alive": 5,
        "ip_type": "IPv4"
    },
    "onenet_config": {
        "product_id": "pKYswKsPeR",
        "port": 1883,
        "server": "mqtts.heclouds.com",
        "device_id": "device1",
        "access_key": "H2mZK/3XW5Uv/cnN7fEf8TnFG3WTu3V1a6eZpe/1J0s=",
        "keepalive": 60,
        "qos": 0,
        "subscribe": {
            "1": "$sys/pKYswKsPeR/device1/dp/post/json/rejected",
            "0": "$sys/pKYswKsPeR/device1/dp/post/json/accepted"
        },
        "publish": {
            "0": "$sys/pKYswKsPeR/device1/dp/post/json"
        }
    },
    "uart_config": {
        "baudrate": "115200",
        "port": "2",
        "flowctl": "0",
        "parity": "0",
        "rs485_direction_pin": "28",
        "databits": "8",
        "stopbits": "1"
    }
}


class Settings(Singleton):
    GET = 0x01
    SET = 0x02
    DEL = 0x03
    LOCK = _thread.allocate_lock()

    def __init__(self):
        self.path = None
        self.settings = DEFAULT

    @property
    def current_settings(self):
        return self.settings

    def reset(self):
        with self.LOCK:
            self.settings = DEFAULT
            if self.path and ql_fs.path_exists(self.path):
                uos.remove(self.path)
            ql_fs.touch(self.path, self.settings)

    def read_from_json(self, path):
        self.path = path
        self.settings = ql_fs.read_json(path)

    def save(self):
        with self.LOCK:
            ql_fs.touch(self.path, self.settings)

    def get(self, key):
        with self.LOCK:
            return self.execute(self.settings, key.split('.'), operate=self.GET)

    def __getitem__(self, item):
        return self.get(item)

    def set(self, key, value):
        with self.LOCK:
            return self.execute(self.settings, key.split('.'), value=value, operate=self.SET)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def delete(self, key):
        with self.LOCK:
            return self.execute(self.settings, key.split('.'), operate=self.DEL)

    def __delitem__(self, key):
        return self.delete(key)

    def execute(self, dict_, keys, value=None, operate=None):

        if self.settings is None:
            raise ValueError('settings not loaded. pls use `Config.read_from_json` to load settings from a json file.')

        key = keys.pop(0)

        if len(keys) == 0:
            if operate == self.GET:
                return dict_[key]
            elif operate == self.SET:
                dict_[key] = value
            elif operate == self.DEL:
                del dict_[key]
            return

        if key not in dict_:
            if operate == self.SET:
                dict_[key] = {}  # auto create sub items recursively.
            else:
                return

        return self.execute(dict_[key], keys, value=value, operate=operate)


settings = Settings()
settings.read_from_json('/usr/dtu_config.json')
