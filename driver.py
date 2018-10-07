#! -*- coding: utf-8 -*-
from __future__ import division

from logging import (getLogger, StreamHandler, INFO, Formatter)

# ログの設定
#handler = StreamHandler()
#handler.setLevel(INFO)
#handler.setFormatter(Formatter("[%(asctime)s] [%(threadName)s] %(message)s"))
logger = getLogger()
#logger.addHandler(handler)
#logger.setLevel(INFO)

import threading
import time
import queue
#import the PCA9685 module.
import osoyoo_PCA9685
import RPi.GPIO as GPIO

class Driver(threading.Thread):

    def __init__(self,q):
        threading.Thread.__init__(self)
        self.q = q

    def run(self):
        logger.info('driver thread start')
        self.speed1 = 1500  #forward/backward speed
        self.speed2 = 1000  #turn speed
        self.ena = 8
        self.enb = 13
        self.in1 = 9
        self.in2 = 10
        self.in3 = 11
        self.in4 = 12
        # Initialise the PCA9685 using the default address (0x40).
        self.pwm = osoyoo_PCA9685.PCA9685()
        # Set frequency to 60hz.
        self.pwm.set_pwm_freq(240)

        self.drive()

    #Set motor speed. speed max is 4095,min is 0
    def set_speed(self,lspeed,rspeed):
        self.pwm.set_pwm(self.ena,0,lspeed)
        self.pwm.set_pwm(self.enb,0,rspeed)

    def stop(self):
        self.set_speed(0,0)

    def destroy(self):
        self.pwm.set_all_pwm(0,0)

    def go_fwd(self):
        self.set_speed(self.speed1,self.speed1)

        self.pwm.set_pwm(self.in1,0,4095)   #IN1
        self.pwm.set_pwm(self.in2,0,0)      #IN2

        self.pwm.set_pwm(self.in3,0,4095)   #IN3
        self.pwm.set_pwm(self.in4,0,0)      #IN4


    def drive(self):
        while(True):
            handle = self.q.get()
            #logger.info('handle={}'.format(handle))
            if handle == 'stop':
                break
            elif len(handle) == 2:
                self._handle3(*handle)
            elif len(handle) == 3:
                self._handle(*handle)
            elif len(handle) == 6:
                self._handle2(*handle)
            else:
                logger.info('invalid handle value')
                break

        self.stop()
        self.destroy()
        logger.info('driver thread end')

    def _handle(self,lhs,rhs,duration):
        logger.info('lhs={},rhs={},duration={}'.format(lhs,rhs,duration))
        self.set_speed(self.speed1,self.speed1)

        self.pwm.set_pwm(self.in1,0,rhs) #rhs fw
        self.pwm.set_pwm(self.in2,0,0)   #rhs bw
        self.pwm.set_pwm(self.in3,0,lhs) #lhs fw
        self.pwm.set_pwm(self.in4,0,0)   #lhs bw

        time.sleep(duration)

        self.stop()

    def _handle3(self,lhs,rhs):
        logger.info('lhs={},rhs={}'.format(lhs,rhs))
        self.set_speed(self.speed1,self.speed1)

        self.pwm.set_pwm(self.in1,0,rhs) #rhs fw
        self.pwm.set_pwm(self.in2,0,0)   #rhs bw
        self.pwm.set_pwm(self.in3,0,lhs) #lhs fw
        self.pwm.set_pwm(self.in4,0,0)   #lhs bw

    def _handle2(self,bsp,lhf,lhb,rhf,rhb,duration):
        logger.info('bsp={},lhf={},lhb={},rhf={},rhb={},duration={}'.format(bsp,lhf,lhb,rhf,rhb,duration))
        self.set_speed(bsp,bsp)

        self.pwm.set_pwm(self.in1,0,rhf)   #rhs fw
        self.pwm.set_pwm(self.in2,0,rhb)   #rhs bw

        time.sleep(0.1)

        self.pwm.set_pwm(self.in3,0,lhf)   #lhs fw
        self.pwm.set_pwm(self.in4,0,lhb)   #lhs bw

        time.sleep(duration*0.8)

        #durationの最後の2割を速度半分にする
        self.pwm.set_pwm(self.in3,0,int(lhf*0.5))   #lhs fw
        self.pwm.set_pwm(self.in4,0,int(lhb*0.5))   #lhs bw
        self.pwm.set_pwm(self.in1,0,int(rhf*0.5))   #rhs fw
        self.pwm.set_pwm(self.in2,0,int(rhb*0.5))   #rhs bw

        time.sleep(duration*0.2)

        self.stop()


    def driving_judge(self,lrpos,distance):
        st_speed = 1500
        st_dur = 1
        coef = 0.2

        lrpos_m = lrpos * ((1 - distance) )

        #if distance < 0.2:
        #    st_speed = st_speed * 0.7

        lhs = st_speed + st_speed * lrpos * 1.5
        rhs = st_speed - st_speed * lrpos * 1.5

        if distance > 0.7:
            duration = 2
        else:
            duration = st_dur * coef + st_dur * (1-coef) * distance

        return (int(lhs),int(rhs),int(duration*100)/100)

    def driving_judge2(self,lrpos,distance):
        st_speed = 2047
        st_dur = 1
        coef = 0.2

        lrpos_m = lrpos * ((1 - distance) )

        if distance < 0.2:
            st_speed = st_speed * 0.7

        lhs = st_speed + st_speed * lrpos * 1.2
        rhs = st_speed - st_speed * lrpos * 1.2

        return (int(lhs),int(rhs))
