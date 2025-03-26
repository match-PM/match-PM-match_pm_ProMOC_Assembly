class MockDeviceManagerCLI:
    @staticmethod
    def BuildDeviceList():
        pass

    @staticmethod
    def GetDeviceList():
        return []

class MockMotorDirection:
    Forward = 1
    Backward = 2
class MockLongTravelStage:
    @staticmethod
    def CreateLongTravelStage(serial_number):
        return MockLongTravelStage()

    def Connect(self, serial_number):
        pass

    def IsSettingsInitialized(self):
        return True

    def LoadMotorConfiguration(self, serial_number):
        pass

    def StartPolling(self, interval):
        pass

    def EnableDevice(self):
        pass

    def GetDeviceInfo(self):
        class DeviceInfo:
            Name = "Mock LTS300"
        return DeviceInfo()

    def Home(self, timeout):
        pass

class MockDecimal:
    def __init__(self, value):
        self.value = value