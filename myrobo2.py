#! -*- coding: utf-8 -*-

from logging import (getLogger, StreamHandler, INFO, Formatter)
import sys

# ログの設定
handler = StreamHandler()
handler.setLevel(INFO)
handler.setFormatter(Formatter("[%(asctime)s] [%(threadName)s] %(message)s"))
logger = getLogger()
logger.addHandler(handler)
logger.setLevel(INFO)

from threading import (Event, Thread)
import time
import numpy as np
import queue
import cv2


#サイコロ検出
def detect_dice(img):

    scale = 1.02
    Cascade = cv2.CascadeClassifier('cascade2.xml')
    point = Cascade.detectMultiScale(img,scale,3)
    logger.info('degected point={}'.format(len(point)))

    #検出したサイコロを矩形で囲む
    if len(point) > 0:
        for rect in point:
            cv2.rectangle(img, tuple(rect[0:2]), tuple(rect[0:2]+rect[2:4]), (0, 0,255), thickness=2)

    #検出の有無にかかわらず、画像保存
    #保存するファイル名はimg/imgxxxxx.jpg
    cnt = videocapturer.get_counter()
    filename = 'img/img{:05d}'.format(cnt) + '.jpg'
    videocapturer.save_counter(cnt+1)
    cv2.imwrite(filename,img)
    logger.info(filename)

    return point,img.shape[:2]

#pointに含まれるすべての矩形の中心が一番矩形に含まれるかどうか
#True: すべて含まれる False: 一つ以上含まれないものがある
def isSame(point):
    #矩形エリアの広い順にソート
    ll = sorted(point,key=lambda x:x[2]*x[3])[::-1]
    #llの2番目の要素以降の中心座標のリスト
    center = [(x[0]+x[2]/2,x[1]+x[3]/2) for x in ll[1:]]

    #入力されたx,yがll[0]の矩形に含まれるか判定する関数
    def isIn(x,y):
        return (ll[0][0]< x) and (x < (ll[0][0]+ll[0][2])) and (ll[0][1]< y) and (y < (ll[0][1]+ll[0][3]))

    #全要素のisInの論理歴
    if all([isIn(*x) for x in center]):
        #一番大きな矩形を返す
        logger.info('isSame!!!')
        return [ll[0]]
    else:
        return None

# 検出点が一つならそのままpointを
# 複数であっても一つとみなせる（isSame）なら一番大きな矩形を
# それいがならNoneを返す
def validation(point):
    if len(point) == 1:
        return point
    elif len(point) > 1:
        return isSame(point)
    else:
        return None

###################
#メイン処理

#ビデオキャプチャスレッド開始
import videocapturer
vcap = videocapturer.VideoCapturer()
vcap.start()

#ドライバースレッド開始
import driver
p = queue.Queue()
driver = driver.Driver(p)
driver.start()

#単なる待ち
#ただ、vcapスレッド起動完了まで、2秒程度は待ちたい
time.sleep(7)

detected = False

logger.info('========================')
logger.info('detection phaze')
logger.info('========================')

#引数で指定されたものに従って処理を分ける
args = sys.argv
if len(args) == 2:
    mode = args[1]
if mode == "test":
    img = vcap.get_view()
    bbox = cv2.selectROI(img, False)
    cv2.destroyAllWindows()
    detected = True
    point = [bbox]

    logger.info('wait...')
    time.sleep(5)

else:
    #チャンスは2回
    for i in range(2):
        img = vcap.get_view()
        point,size = detect_dice(img)
        logger.info('point={},size={}'.format(point,size))

        point = validation(point)

        #有効に検出できなければ
        if point is None:
            if i == 1:
                break
            #検出失敗一度目はとりあえずちょっと進んでみる
            logger.info('go, anyway...')
            p.put((2048,2048,0.3))

#検出できたらtracking modeに移行
if detected:
    logger.info('========================')
    logger.info('tracking phaze')
    logger.info('========================')

    #トラッキングモード起動
    vcap.goTrackingMode(img,tuple(point[0]))

    #見失った回数
    miss_count = 0

    while(True):

        x,y,w,h = vcap.get_bbox()
        size = vcap.cap_size

        #トラッキングが外れたときの処理
        if (x,y,w,h) == (0,0,0,0):
            #10回連続でトラッキングできなかったらbreakする
            if miss_count == 5:
                break
            logger.info('missed!! count={}'.format(miss_count))
            miss_count += 1
            #トラッキングできたときの処理は行わず、次のトラッキング結果を待つ
            continue
        #ちゃんとトラッキングできたときにはmiss_countをクリア
        miss_count = 0

        #左右どちらにどれだけ寄っているか
        #-0.5 ～ 0.5の範囲で示す
        lrpos = ((x+w/2) - size[0] /2) / size[0]

        #検出物が画面下端にどれだけ近いか
        #0ならすぐそば 画面上端にあれば1に近い数になる
        distance = (size[1] - (y + h)) / size[1]

        logger.info('lrpos={},distance={}'.format(lrpos,distance))
        handle = driver.driving_judge2(lrpos,distance)
        p.put(handle)

#スレッドを止める
vcap.stop()
p.put('stop')

vcap.join()
driver.join()
logger.info('finished')
