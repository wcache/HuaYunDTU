import osTimer
from machine import ExtInt, Pin
from misc import Power


class Manager(object):

    def __init__(
            self,
            dog_gpio=Pin.GPIO12,
            reload_gpio=ExtInt.GPIO29
    ):
        self.dog_pin = Pin(dog_gpio, Pin.OUT, Pin.PULL_DISABLE, 1)
        self.dog_feed_timer = osTimer()

    def start(self):
        self.dog_feed_timer.start(3000, 1, self.__feed)

    def __feed(self, args):
        if self.dog_pin.read():
            self.dog_pin.write(0)
        else:
            self.dog_pin.write(1)


if __name__ == '__main__':
    manager = Manager()
    manager.start()
