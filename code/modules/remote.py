import _thread
from usr.modules.common import Observable, CloudObserver


class RemoteSubscribe(CloudObserver):
    """This class is for distribute cloud downlink messages"""
    def __init__(self):
        self.__executor = None
        self.__ota_executor = None

    def __raw_data(self, args):
        """Handle cloud transparent data transmission."""
        return self.__executor.downlink_main(args) if self.__executor else False

    def __query(self, *args, **kwargs):
        """Handle cloud object model quering message"""
        return self.__executor.event_query(*args, **kwargs) if self.__executor else False

    def __ota_plain(self, *args, **kwargs):
        """Handle cloud OTA plain"""
        return self.__ota_executor.event_ota_plain(*args, **kwargs) if self.__ota_executor else False

    def __ota_file_download(self, *args, **kwargs):
        """Handle cloud OTA file fragment download"""
        # TODO: To Download OTA File For MQTT Association (Not Support Now.)
        print("ota_file_download: %s" % str(args))
        if self.__ota_executor and hasattr(self.__ota_executor, "ota_file_download"):
            return self.__ota_executor.event_ota_file_download(*args, **kwargs)
        else:
            return False

    def __thread_execute(self, option_fun, opt_args, opt_kwargs):
        return option_fun(*opt_args, **opt_kwargs)

    def add_executor(self, executor, executor_id):
        """Add cloud downlink messages executor"""
        if executor:
            if executor_id == 1:
                self.__executor = executor
                return True
            elif executor_id == 2:
                self.__ota_executor = executor
                return True
        return False

    def execute(self, cloud, method, *args, **kwargs):
        opt_attr = "__" + method
        if hasattr(self, opt_attr):
            option_fun = getattr(self, opt_attr)
            _thread.start_new_thread(self.__thread_execute, (option_fun, args, kwargs))
        else:
            print("RemoteSubscribe Has No Attribute [%s]." % opt_attr)


class RemotePublish(Observable):
    def __init__(self):
        """
        cloud:
            CloudIot Object
        """
        super().__init__()
        self.__cloud = None

    def __cloud_conn(self, enforce=False):
        """Cloud connect"""
        return self.__cloud.init(enforce=enforce) if self.__cloud else False

    def __cloud_post(self, data, topic_id):
        """Cloud publish object model data"""
        try:
            return self.__cloud.through_post_data(data, topic_id) if self.__cloud else False
        except Exception as e:
            print("cloud post fault:", e)

    def add_cloud(self, cloud):
        """Add Cloud object"""
        if hasattr(cloud, "init") and \
                hasattr(cloud, "post_data") and \
                hasattr(cloud, "ota_request") and \
                hasattr(cloud, "ota_action"):
            self.__cloud = cloud
            return True
        return False

    def cloud_ota_check(self):
        """Check ota plain"""
        return self.__cloud.ota_request() if self.__cloud else False

    def cloud_ota_action(self, action=1, module=None):
        """Confirm ota upgrade"""
        return self.__cloud.ota_action(action, module) if self.__cloud else False

    def cloud_device_report(self):
        """Device & project version report"""
        return self.__cloud.device_report() if self.__cloud else False

    def cloud_rrpc_response(self, message_id, data):
        """RRPC response"""
        return self.__cloud.rrpc_response(message_id, data) if self.__cloud else False

    def post_data(self, data, topic_id):
        res = True
        if self.__cloud_conn():
            if not self.__cloud_post(data, topic_id):
                if self.__cloud_conn(enforce=True):
                    if not self.__cloud_post(data, topic_id):
                        res = False
                else:
                    print("Cloud Connect Failed.")
                    res = False
        else:
            print("Cloud Connect Failed.")
            res = False
        
        if res is False:
            self.notifyObservers(topic_id, data)
            print('wait net connect, try cfun switch.')

        return res
