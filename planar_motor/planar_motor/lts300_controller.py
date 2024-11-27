import os
import time
import sys
import clr

# Ensure the correct paths are used for the DLLs
clr.AddReference(r"/media/pmlab_mover/1EC636E9C636C137/Program Files/Thorlabs/Kinesis/Thorlabs.MotionControl.DeviceManagerCLI.dll")
clr.AddReference(r"/media/pmlab_mover/1EC636E9C636C137/Program Files/Thorlabs/Kinesis/Thorlabs.MotionControl.GenericMotorCLI.dll")
clr.AddReference(r"/media/pmlab_mover/1EC636E9C636C137/Program Files/Thorlabs/Kinesis/ThorLabs.MotionControl.IntegratedStepperMotorsCLI.dll")

# Import necessary namespaces
from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
from Thorlabs.MotionControl.GenericMotorCLI import LongTravelStage
from Thorlabs.MotionControl.IntegratedStepperMotorsCLI import *
from System import Decimal  # For working with real-world units

def main():
    """Main entry point for the application"""

    # Uncomment this line if using simulations
    # SimulationManager.Instance.InitializeSimulations()

    try:
        # Build the device list
        DeviceManagerCLI.BuildDeviceList()

        # Specify the device's serial number
        serial_no = "45877001"  # Replace with the actual device serial number

        # Connect to the device
        device = LongTravelStage.CreateLongTravelStage(serial_no)
        device.Connect(serial_no)

        # Ensure the device settings are initialized
        if not device.IsSettingsInitialized():
            device.WaitForSettingsInitialized(10000)  # Wait for up to 10 seconds
            assert device.IsSettingsInitialized()

        # Start polling and enable the device
        device.StartPolling(250)  # Poll every 250ms
        time.sleep(0.25)  # Allow some time for polling to start
        device.EnableDevice()
        time.sleep(0.25)  # Wait for device to enable

        # Display device information
        device_info = device.GetDeviceInfo()
        print(f"Device Info: {device_info.Description}")

        # Load motor configuration settings
        motor_config = device.LoadMotorConfiguration(serial_no)

        # Get homing parameters and display them
        home_params = device.GetHomingParams()
        print(f'Homing velocity: {home_params.Velocity}, Homing Direction: {home_params.Direction}')
        home_params.Velocity = Decimal(10.0)  # Set homing velocity to 10 mm/s
        device.SetHomingParams(home_params)

        # Home the device
        print("Homing the device...")
        device.Home(60000)  # Timeout: 60 seconds
        print("Homing complete.")

        # Get velocity parameters, update and set them
        vel_params = device.GetVelocityParams()
        vel_params.MaxVelocity = Decimal(50.0)  # Set max velocity to 50 mm/s (be cautious)
        device.SetVelocityParams(vel_params)

        # Move the device to a new position (e.g., 150 mm)
        new_pos = Decimal(150.0)  # The target position in mm
        print(f"Moving to {new_pos} mm...")
        device.MoveTo(new_pos, 60000)  # Timeout: 60 seconds
        print("Movement complete.")

        # Stop polling and disconnect from the device
        device.StopPolling()
        device.Disconnect()

    except Exception as e:
        print(f"An error occurred: {e}")

    # Uncomment if using simulations
    # SimulationManager.Instance.UninitializeSimulations()

if __name__ == "__main__":
    main()
