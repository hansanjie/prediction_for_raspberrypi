"""
Run the online classification system.

Capture an image, classify, do it again.
"""
import time
from picamera import PiCamera
from picamera.array import PiRGBArray
import tensorflow as tf

from pythonosc import osc_message_builder
from pythonosc import udp_client

import cv2
import numpy as np

import threading


#设置全局变量，用于监控预测程序是否运行


class global_var:
    global is_run_prediction
    global the_output_messages
    global labels
    global graph_def
    global fin
    global sess
    global text_show
    global render_text_number
    global linetype
    global font 
    global text_list

    def init_all_varibles():
        global_var.font = cv2.FONT_HERSHEY_SIMPLEX
        global_var.linetype=cv2.LINE_AA
        global_var.the_output_messages = []
        global_var.is_run_prediction = False
        global_var.labels = get_labels()
        global_var.render_text_number = 0
        global_var.text_list = []
        global_var.text_show =np.zeros((240,120,3),np.uint8)

def get_labels():
    """Get a list of labels so we can see if it's an ad or not."""
    with open('retrained_labels.txt', 'r') as fin:
        labels = [line.rstrip('\n') for line in fin]
        #print(labels)
    return labels

def get_graph_def():
    global_var.fin = tf.gfile.FastGFile('retrained_graph.pb', 'rb')
    global_var.graph_def = tf.GraphDef()
    global_var.graph_def.ParseFromString(global_var.fin.read())
    _ = tf.import_graph_def(global_var.graph_def, name='')


def get_sess():
    get_graph_def()
    global_var.sess = tf.Session()


def run_classification_from_cach_sess(frame):
    print("开始缓存测试")
    global_var.is_run_prediction = True
    softmax_tensor = global_var.sess.graph.get_tensor_by_name('final_result:0')
    image = cv2.resize(frame.array, (224, 224))
    decoded_image = image.reshape(1, 224, 224, 3)
    predictions = global_var.sess.run(softmax_tensor, {'Placeholder:0': decoded_image})
    prediction = predictions[0]

    prediction = prediction.tolist()
    max_value = max(prediction)
    max_index = prediction.index(max_value)
    predicted_label = global_var.labels[max_index]
    # 在命令行打印识别到的信息
    print("%s (%.2f%%)" % (predicted_label, max_value * 100))
    messages = [max_index, predicted_label, max_value]
    global_var.text_list.append(predicted_label)
    global_var.render_text_number += 1
    if global_var.render_text_number <19 :
        cv2.putText(global_var.text_show,predicted_label,(20,13*global_var.render_text_number), global_var.font, 0.4,(255,255,255),1,cv2.LINE_AA)
    else:
        global_var.text_show =np.zeros((240,120,3),np.uint8)
        for i in range(20):
            cv2.putText(global_var.text_show,global_var.text_list[0-i],(20,13*(20-i)), global_var.font, 0.4,(255,255,255),1,cv2.LINE_AA)
    #cv2.addText(global_var.text_show,predicted_label,(10,10),global_var.font,color=(255,0,0),style=global_var.linetype)
    #cv2.addText(global_var.text_show,predicted_label,(10,10),global_var.font)
    

    send_osc_message(messages)
    
    # Reset the buffer so we're ready for the next one.
    print("预测结束了")
    # prediction_event.clear()
    # is_run_prediction = False
    global_var.the_output_messages = messages;
    global_var.is_run_prediction = False



def run_classification(labels,frame):
    print("1、运行到这里了，可喜可贺")
    # Unpersists graph from file
    with tf.gfile.FastGFile('retrained_graph.pb', 'rb') as fin:
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(fin.read())
        _ = tf.import_graph_def(graph_def, name='')

    with tf.Session() as sess:
        print("2、运行到这里了，可喜可贺")
        # And capture continuously forever.
        softmax_tensor = sess.graph.get_tensor_by_name('final_result:0')
        image = cv2.resize(frame.array, (224, 224))
        decoded_image = image.reshape(1, 224, 224, 3)
        predictions = sess.run(softmax_tensor, {'Placeholder:0': decoded_image})
        prediction = predictions[0]



        # Get the highest confidence category.
        prediction = prediction.tolist()
        max_value = max(prediction)
        max_index = prediction.index(max_value)
        predicted_label = labels[max_index]
        #在命令行打印识别到的信息
        print("%s (%.2f%%)" % (predicted_label, max_value * 100))

        messages = [max_index, predicted_label, max_value]
        send_osc_message(messages)
        # Reset the buffer so we're ready for the next one.
        print("预测结束了")
        #prediction_event.clear()
        #is_run_prediction = False
        cv2.putText(global_var.text_show,messages)
        global_var.the_output_messages=messages;
        global_var.is_run_prediction =False

def this_is_entrance():
    """Stream images off the camera and process them."""
    with  PiCamera() as camera:
        camera.resolution = (320, 240)
        camera.framerate = 24
        camera.hflip = True
        camera.vflip = True
        rawCapture = PiRGBArray(camera, size=(320, 240))
        time.sleep(0.1)
        
        #开启一个线程用于预测

        for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
            image = frame.array
            #print(image.shape,image.dtype)
            cv2.rectangle(image,(80,60),(240,180),(55,255,155),3)
            combination_image = np.hstack((image,global_var.text_show))
            cv2.imshow("combination_image", combination_image)
            #cv2.imshow("Frame2", text_show)
#            prediction_event =threading.Event()
            #print(prediction_event.isSet)
            if global_var.is_run_prediction is False:
                print("尚未进行预测")
                #mthead = threading.Thread(target=frame_for_prediction,args=(frame,))
                #mthead.start()
                mthead2 = threading.Thread(target=run_classification_from_cach_sess,args=(frame,))
                mthead2.start()
###明天从这里开始
                #mthead.join()
            #判断mthread是否启动
            #判断mthread是否有返回值
            #如果没有，则重启一个线程
            #如果有启动，则将返回值打印到图像上
#            print(global_var.the_output_messages)
#            print(global_var.is_run_prediction)
            key = cv2.waitKey(1) & 0xFF
            rawCapture.truncate(0)
            if key ==ord("q"):
                break

#        while True:
#            time.sleep(5)

def frame_for_prediction(frame):

    global_var.is_run_prediction = True
    print("开始预测")
    #prediction_event.set()
    run_classification(global_var.labels,frame)
    #is_run_prediction = False

def send_osc_message(messages):
    address = "192.168.0.20"
    port = 7000
    osc_name = "/AAAA"
    client = udp_client.SimpleUDPClient(address, port)
    client.send_message(osc_name, messages)

if __name__ == '__main__':
    global_var.init_all_varibles()
    get_sess()
    this_is_entrance()
