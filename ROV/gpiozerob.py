import gpiozero
from time  import sleep

# Right Motor pins (BCM)
in1 = gpiozero.OutputDevice(16)
in2 = gpiozero.OutputDevice(26)
en_a = gpiozero.PWMOutputDevice(12)

# Left Motor pins (BCM)
in3 = gpiozero.OutputDevice(5)
in4 = gpiozero.OutputDevice(6)
en_b = gpiozero.PWMOutputDevice(13)






en_a.on()
en_b.on()
while(1):
    '''
    in1.on()
    in2.off()    
    in3.off()
    in4.on()
    en_a.value = 0.0
    en_b.value = 0.0
    sleep(0.5)
    '''
    in1.off()
    in2.on()
    in3.on()
    in4.off()
    en_a.value = 1
    en_b.value = 1
    #sleep(5)


