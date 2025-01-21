from pylablib.devices import Thorlabs
import time


stage = Thorlabs.KinesisMotor("/dev/ttyUSB0")  # connect to the stage

stage.jog("+")  # initiate jog (continuous move) in the positive direction


stage.close()
