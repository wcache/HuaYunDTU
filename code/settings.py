import uos
import ql_fs
import ujson
import modem
import _thread

from usr.modules.common import Singleton
from usr.modules.common import option_lock

PROJECT_NAME = "QuecPython-Dtu"
PROJECT_VERSION = "3.0.0"

DEVICE_FIRMWARE_NAME = uos.uname()[0].split("=")[1]
DEVICE_FIRMWARE_VERSION = modem.getDevFwVersion()

_settings_lock = _thread.allocate_lock()


class Settings(Singleton):

    def __init__(self, settings_file="/usr/dtu_config.json"):
        self.settings_file = settings_file
        self.current_settings = {}
        self.__init_config()

    def __init_config(self):
        try:
            self.__read_config()
            return True
        except:
            return False

    def __read_config(self):
        if ql_fs.path_exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                self.current_settings = ujson.load(f)
                return True
        return False

    def __set_config(self, opt, val):
        if opt in ["fota", "sota", "offline_storage"]:
            self.current_settings["system_config"]["base_function"][opt] = val
            return True
        elif opt in ["uart_config", "aliyun_config", "txyun_config", "hwyun_config", "quecthing_config", "tcp_private_cloud_config", "mqtt_private_cloud_config"]:
            if not isinstance(val, dict):
                return False
            self.current_settings[opt] = val
            return True
        elif opt in ["cloud"]:
            if not isinstance(val, str):
                return False
            self.current_settings["system_config"][opt] = val
            return True

        return False

    def __save_config(self):
        try:
            with open(self.settings_file, "w") as f:
                ujson.dump(self.current_settings, f)
            return True
        except:
            return False

    def __remove_config(self):
        try:
            uos.remove(self.settings_file)
            return True
        except:
            return False

    def __get_config(self):
        return self.current_settings

    @option_lock(_settings_lock)
    def get(self):
        return self.__get_config()

    @option_lock(_settings_lock)
    def set(self, opt, val):
        return self.__set_config(opt, val)

    @option_lock(_settings_lock)
    def save(self):
        return self.__save_config()

    @option_lock(_settings_lock)
    def remove(self):
        return self.__remove_config()

    @option_lock(_settings_lock)
    def reset(self):
        if self.__remove_config():
            if self.__init_config():
                return self.__save_config()
        return False

    def set_multi(self, **kwargs):
        for k in self.current_settings.keys():
            if k in kwargs:
                try:
                    if not self.__set_config(k, kwargs[k]):
                        raise Exception("Set parameter error") 
                except:
                    return False
        return True


settings = Settings()