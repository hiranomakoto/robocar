#! -*- coding: utf-8 -*-

from logging import (getLogger, StreamHandler, INFO, Formatter)

# ログの設定
#handler = StreamHandler()
#handler.setLevel(INFO)
#handler.setFormatter(Formatter("[%(asctime)s] [%(threadName)s] %(message)s"))
logger = getLogger()
#logger.addHandler(handler)
#logger.setLevel(INFO)


#カウンターを取得
def get_counter():
    try:
        f = open('counter','r')
    except FileNotFoundError:
        return 0

    val = int(f.read().rstrip('\n'))
    f.close()
    return val

#カウンターを保存
def save_counter(val):
    f = open('counter','w')
    f.write(str(val))
    f.close()


#############################
#画像処理関連
#############################

from threading import (Event, Thread)
import time
import cv2
import numpy as np
import queue

class VideoCapturer(Thread):
    def __init__(self,flip = True):
        Thread.__init__(self)
        self.flip = flip

    def run(self):
        self.startupEvent = Event() #スレッド起動待ち用
        self.event = Event() #シャッタートリガ用
        self.q = queue.LifoQueue()
        self.q4track = queue.LifoQueue()
        self.stop_flg = False #スレッド停止フラグ
        self.trackingMode = False #トラッキングモードフラグ
        self.test_mode = False #テストモード

        #画像サイズ
        self.cap_size = (320,180)

        self.cap = cv2.VideoCapture(0)
        logger.info('camera setup w={},h={},fps={}'.format(self.cap.get(3),self.cap.get(4),self.cap.get(5)))

        #最初の1秒分画像を捨てる
        for _ in range(30):
            ret, frame = self.cap.read()

        logger.info('videoCapturer thread start')

        #スレッド起動をメインスレッドに通知
        self.startupEvent.set()

        #トリガを受けて画像を返すモードに移行
        self.waitTrigger()

        #トラッキングモードに移行
        if self.trackingMode:
            self.trackTarget()

        #後始末
        self.cap.release()
        cv2.destroyAllWindows()

    def waitTrigger(self):
        while (not self.stop_flg) and (not self.trackingMode):
            ret, frame = self.cap.read()
            #メインスレッドからeventがsetされたら動作する
            if self.event.wait(0.01):
                logger.info('put view')
                #インプット画像が左右反転しているため、flipで反転
                #処理量節約のため、ここでcap_sizeまで圧縮
                if self.flip:
                    frame = cv2.flip(frame,1)
                self.q.put(cv2.resize(frame,self.cap_size))
                self.event.clear()

    def trackTarget(self):
        logger.info('tracking mode!!')
        tracker = cv2.TrackerKCF_create()
        ok = tracker.init(self.targetView, self.bbox)
        counter = get_counter()
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter('img/trackingLog{:05d}.avi'.format(counter), fourcc, 20, self.cap_size)
        save_counter(counter + 1)

        #最初の1秒分画像を捨てる
        for _ in range(30):
            ret, frame = self.cap.read()

        #何frameに一度判定するか？
        frame_tobe_track = 1
        frame_cnt = 1

        while not self.stop_flg:
            ret, frame = self.cap.read()

            #判定すべきframeか？
            if not (frame_cnt % frame_tobe_track == 0):
                frame_cnt = 1
                contnue
            frame_cnt += 1

            #左右反転とリサイズ
            if self.flip:
                frame = cv2.flip(frame,1)
            frame = cv2.resize(frame,self.cap_size)
            # Start timer
            #timer = cv2.getTickCount()
            # トラッカーをアップデートする
            track, bbox = tracker.update(frame)
            # FPSを計算する
            #fps = cv2.getTickFrequency() / (cv2.getTickCount() - timer);

            # 検出した場所に四角を書く
            if track:
                # Tracking success
                p1 = (int(bbox[0]), int(bbox[1]))
                p2 = (int(bbox[0] + bbox[2]), int(bbox[1] + bbox[3]))
                cv2.rectangle(frame, p1, p2, (0,255,0), 2, 1)
            else :
                # トラッキングが外れたら警告を表示する
                cv2.putText(frame, "Failure", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1, cv2.LINE_AA)
                # トラッキングが外れたらbboxを無効値に設定する
                bbox = (0,0,0,0)

            # FPSを表示する
            #cv2.putText(frame, "FPS : " + str(int(fps)), (10,20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1, cv2.LINE_AA)

            #検出したbboxをメインスレッドに返す
            self.q4track.put(bbox)

            # 加工済の画像を表示/保存する
            if self.test_mode:
                cv2.imshow("Tracking", frame)
                k = cv2.waitKey(1)
                if k == 27 :
                    break

            out.write(frame)

            # 1ms waitを入れておく
            time.sleep(0.001)



    #画像取得
    def get_view(self):
        logger.info('get_view')
        self.event.set()
        img = self.q.get()
        #キューを空にしておく
        while not self.q.empty():
            self.q.get()
        return img

    #bbox取得
    def get_bbox(self):
        bbox = self.q4track.get()
        #キューを空にしておく
        while not self.q4track.empty():
            self.q4track.get()
        return bbox

    def goTrackingMode(self,img,bbox):
        self.targetView = img
        self.bbox = bbox
        self.trackingMode = True

    #スレッド停止
    def go_test_mode(self):
        self.test_mode = True

    #スレッド停止
    def stop(self):
        self.stop_flg = True

    #スレッド起動待ち
    def wait_thread_startup(self):
        if self.startupEvent.wait(20):
            self.startupEvent.clear()
            return True
        else:
            return False
