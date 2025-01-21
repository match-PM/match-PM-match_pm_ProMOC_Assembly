from pylablib.devices import Thorlabs
import time


stage = Thorlabs.KinesisMotor("/dev/ttyUSB0","LTS300")  # connect to the stage


print(stage._model)
print(stage.get_stage())
print(stage._get_step_scale(stage.get_stage()))
print(stage.get_jog_parameters())

i = 1
while i < 100000000:
    stage.jog("+", None, "builtin")  # initiate jog (continuous move) in the positive direction
    i += 1

stage.close()
