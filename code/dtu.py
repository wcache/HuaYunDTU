import _thread
import osTimer
from machine import ExtInt, Pin
from misc import Power
from usr.modules.common import Singleton
from usr.modules.onenetIot import OneNetIot
from usr.modules.socketIot import SocketIot
from usr.modules.serial import Serial
from usr.dtu_transaction import DownlinkTransaction, OtaTransaction, UplinkTransaction, GuiToolsInteraction
from usr.modules.remote import RemotePublish, RemoteSubscribe
from usr.settings import settings, PROJECT_NAME, PROJECT_VERSION, DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION


class Dtu(Singleton):
    def __init__(self):
        self.__ota_timer = osTimer()
        self.__ota_transaction = None

    @staticmethod
    def __cloud_init(protocol):
        if protocol.startswith("onenet"):
            cloud_config = settings.current_settings.get("onenet_config")
            cloud = OneNetIot(
                cloud_config['product_id'],
                cloud_config['device_id'],
                cloud_config['access_key'],
                server=cloud_config['server'],
                port=cloud_config['port'],
                qos=cloud_config['qos'],
                subscribe=cloud_config['subscribe'],
                publish=cloud_config['publish'],
            )
            cloud.init(enforce=True)
            return cloud
        elif protocol.startswith("tcp"):
            cloud_config = settings.current_settings.get("tcp_private_cloud_config")
            cloud = SocketIot(
                ip_type=cloud_config.get("ip_type"),
                keep_alive=cloud_config.get("keep_alive"),
                domain=cloud_config.get("server"),
                port=int(cloud_config.get("port")),
            )
            cloud.init(enforce=True)
            return cloud
        else:
            raise TypeError('protocol \"{}\" not supported!'.format(protocol))

    def __periodic_ota_check(self, args):
        """Periodically check whether cloud have an upgrade plan"""
        self.__ota_transaction.ota_check()

    def start(self):
        """Dtu init flow
        """
        print("PROJECT_NAME: %s, PROJECT_VERSION: %s" % (PROJECT_NAME, PROJECT_VERSION))
        print("DEVICE_FIRMWARE_NAME: %s, DEVICE_FIRMWARE_VERSION: %s" % (DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION))

        uart_setting = settings.current_settings["uart_config"]
        serial = Serial(
            int(uart_setting.get("port")),
            int(uart_setting.get("baudrate")),
            int(uart_setting.get("databits")),
            int(uart_setting.get("parity")),
            int(uart_setting.get("stopbits")),
            int(uart_setting.get("flowctl")),
            uart_setting.get("rs485_direction_pin")
        )

        cloud = self.__cloud_init(settings.current_settings["system_config"]["cloud"])

        gui_tool_inter = GuiToolsInteraction()

        up_transaction = UplinkTransaction()
        up_transaction.add_module(serial)
        up_transaction.add_module(gui_tool_inter)

        down_transaction = DownlinkTransaction()
        down_transaction.add_module(serial)

        ota_transaction = OtaTransaction()

        remote_sub = RemoteSubscribe()
        remote_sub.add_executor(down_transaction, 1)
        remote_sub.add_executor(ota_transaction, 2)
        cloud.addObserver(remote_sub)

        remote_pub = RemotePublish()
        remote_pub.add_cloud(cloud)
        up_transaction.add_module(remote_pub)
        ota_transaction.add_module(remote_pub)

        ota_transaction.ota_check()
        self.__ota_transaction = ota_transaction
        self.__ota_timer.start(1000 * 600, 1, self.__periodic_ota_check)

        try:
            _thread.start_new_thread(up_transaction.uplink_main, ())
        except:
            raise self.Error(self.error_map[self.ErrCode.ESYS])


class Manager(object):

    def __init__(
            self,
            dog_gpio=Pin.GPIO12,
            reload_gpio=ExtInt.GPIO29
    ):
        self.dog_pin = Pin(dog_gpio, Pin.OUT, Pin.PULL_DISABLE, 1)
        self.dog_feed_timer = osTimer()

        self.reload_pin = ExtInt(reload_gpio, ExtInt.IRQ_RISING_FALLING, ExtInt.PULL_PU, self.reload_callback)
        self.reload_timer = osTimer()
        self.dtu = Dtu()

    def start(self):
        self.dog_feed_timer.start(3000, 1, self.__feed)
        self.reload_pin.enable()
        self.dtu.start()

    def __feed(self, args):
        if self.dog_pin.read():
            self.dog_pin.write(0)
        else:
            self.dog_pin.write(1)

    def reload_callback(self, args):
        if args[1]:
            self.reload_timer.start(3000, 0, self.reset)
        else:
            self.reload_timer.stop()

    @staticmethod
    def reset(args):
        settings.reset()
        Power.powerRestart()


if __name__ == "__main__":
    manager = Manager()
    manager.start()
