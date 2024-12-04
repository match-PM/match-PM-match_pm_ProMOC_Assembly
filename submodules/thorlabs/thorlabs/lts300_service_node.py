from thorlabs_apt_device import APTDevice
from thorlabs_apt_device import APTDevice_Motor
import time


#device=/dev/ttyUSB0, 
# manufacturer=Thorlabs, 
# product=APT Stepper Motor Controller, 
# vid=0x0403, pid=0xfaf0, 
# serial_number=45318394, 
# location=1-2.1

def mm_to_nm(millimeters)-> int:
    nanometers = millimeters * 1e6
    return nanometers




device = APTDevice_Motor('/dev/ttyUSB0')
device.set_enabled()
device.home



# device.set_jog_params(50,int(mm_to_nm(50)),int(mm_to_nm(50)),0,0)
# # Move the device to a specific position
# for i in range(100):
#     device.move_jog(0,0,0)



print(device.bays)
print(device.status_)

#device.move_relative(5000)
device.set_home_params(velocity=10, offset_distance=5)
device.home()
device.close()
