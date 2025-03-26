class MockDecimal:
    def __init__(self, value):
        self.value = value

class MockLongTravelStage:
    def __init__(self):
        self.position = 0.0
        self.is_homed = False

    @staticmethod
    def CreateLongTravelStage(serial_no):
        print(f"Mock: Creating LongTravelStage with serial number {serial_no}")
        return MockLongTravelStage()

    def Connect(self, serial_no):
        print(f"Mock: Connecting to device with serial number {serial_no}")

    def IsSettingsInitialized(self):
        return True

    def LoadMotorConfiguration(self, serial_no):
        print(f"Mock: Loading motor configuration for {serial_no}")

    def StartPolling(self, interval):
        print(f"Mock: Starting polling with interval {interval}")

    def EnableDevice(self):
        print("Mock: Enabling device")

    def Home(self, timeout):
        print(f"Mock: Homing device with timeout {timeout}")
        self.is_homed = True
        self.position = 0.0

    def MoveTo(self, position, timeout):
        print(f"Mock: Moving to position {position} with timeout {timeout}")
        self.position = float(position)

    def GetPosition(self):
        return MockDecimal(self.position)

    def GetDeviceInfo(self):
        class MockDeviceInfo:
            Name = "Mock LTS300"
        return MockDeviceInfo()

class MockDeviceManagerCLI:
    @staticmethod
    def BuildDeviceList():
        print("Mock: Building device list")

    @staticmethod
    def GetDeviceList():
        return ["Mock Device 1", "Mock Device 2"]

    @staticmethod
    def IsDeviceConnected(serial_no):
        return True

class MockMotorDirection:
    Forward = 1
    Backward = 2