import _thread
import osTimer
from usr.modules.common import Singleton
from usr.modules.onenetIot import OneNetIot

from usr.settings import settings
from usr.modules.serial import Serial
from usr.dtu_transaction import DownlinkTransaction, OtaTransaction, UplinkTransaction, GuiToolsInteraction
from usr.modules.remote import RemotePublish, RemoteSubscribe
from usr.settings import PROJECT_NAME, PROJECT_VERSION, DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION



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
        else:
            raise TypeError('protocol \"{}\" not supported!'.format(protocol))

    def __periodic_ota_check(self, args):
        """Periodically check whether cloud have an upgrade plan"""
        self.__ota_transaction.ota_check()

    def start(self):
        """Dtu init flow
        """
        print("PROJECT_NAME: %s, PROJECT_VERSION: %s" % (PROJECT_NAME, PROJECT_VERSION))
        print(
            "DEVICE_FIRMWARE_NAME: %s, DEVICE_FIRMWARE_VERSION: %s" % (DEVICE_FIRMWARE_NAME, DEVICE_FIRMWARE_VERSION))

        uart_setting = settings.current_settings["uart_config"]
        # Serial initialization
        serial = Serial(
            int(uart_setting.get("port")),
            int(uart_setting.get("baudrate")),
            int(uart_setting.get("databits")),
            int(uart_setting.get("parity")),
            int(uart_setting.get("stopbits")),
            int(uart_setting.get("flowctl")),
            uart_setting.get("rs485_direction_pin")
        )

        # Cloud initialization
        cloud = self.__cloud_init(settings.current_settings["system_config"]["cloud"])

        # GuiToolsInteraction initialization
        gui_tool_inter = GuiToolsInteraction()

        # UplinkTransaction initialization
        up_transaction = UplinkTransaction()
        up_transaction.add_module(serial)
        up_transaction.add_module(gui_tool_inter)

        # DownlinkTransaction initialization
        down_transaction = DownlinkTransaction()
        down_transaction.add_module(serial)

        # OtaTransaction initialization
        ota_transaction = OtaTransaction()

        # RemoteSubscribe initialization
        remote_sub = RemoteSubscribe()
        remote_sub.add_executor(down_transaction, 1)
        remote_sub.add_executor(ota_transaction, 2)
        cloud.addObserver(remote_sub)

        # RemotePublish initialization
        remote_pub = RemotePublish()
        remote_pub.add_cloud(cloud)
        up_transaction.add_module(remote_pub)
        ota_transaction.add_module(remote_pub)

        # Send module release information to cloud. After receiving this information, 
        # the cloud server checks whether to upgrade modules
        ota_transaction.ota_check()
        # Periodically check whether cloud have an upgrade plan
        self.__ota_transaction = ota_transaction
        self.__ota_timer.start(1000 * 600, 1, self.__periodic_ota_check)

        # Start uplink transaction
        try:
            _thread.start_new_thread(up_transaction.uplink_main, ())
        except:
            raise self.Error(self.error_map[self.ErrCode.ESYS])


def FeedDog(args):
    from machine import Pin
    dog_pin = Pin(Pin.GPIO12, Pin.OUT, Pin.PULL_DISABLE, 1)
    if dog_pin.read():
        dog_pin.write(0)
    else:
        dog_pin.write(1)


if __name__ == "__main__":
    feed_dog_timer = osTimer()
    feed_dog_timer.start(3000, 1, FeedDog)
    dtu = Dtu()
    dtu.start()