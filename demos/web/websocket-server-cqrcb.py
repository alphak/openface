#!/usr/bin/env python2
# #
# Copyright 2015-2016 Carnegie Mellon University
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

start = time.time()

import os
import pickle
import sys
fileDir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(fileDir, "..", ".."))

import txaio
txaio.use_twisted()

from autobahn.twisted.websocket import WebSocketServerProtocol, \
    WebSocketServerFactory
from twisted.internet import task, defer
from twisted.internet.ssl import DefaultOpenSSLContextFactory

from twisted.python import log

import argparse
import cv2
import imagehash
import json
from PIL import Image
import numpy as np
np.set_printoptions(precision=2)
import os
import StringIO
import urllib
import base64

from sklearn.decomposition import PCA
from sklearn.grid_search import GridSearchCV
from sklearn.manifold import TSNE
from sklearn.svm import SVC
from sklearn.mixture import GMM

import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.cm as cm

import openface
import csv

modelDir = os.path.join(fileDir, '..', '..', 'models')
dlibModelDir = os.path.join(modelDir, 'dlib')
openfaceModelDir = os.path.join(modelDir, 'openface')
classifierFilelDir = os.path.join(fileDir, '..','..','..','cqrcb_feat')
# csvFilelDir = os.path.join(fileDir, '..','..','..','cqrcb_empl')
initSaveFilelDir = os.path.join(fileDir, '..','..','..','cqrcb_csv')
csv_file = os.path.join(initSaveFilelDir, 'epinfo.csv')

# For TLS connections
tls_crt = os.path.join(fileDir, 'tls', 'server.crt')
tls_key = os.path.join(fileDir, 'tls', 'server.key')

parser = argparse.ArgumentParser()
parser.add_argument('--dlibFacePredictor', type=str, help="Path to dlib's face predictor.",
                    default=os.path.join(dlibModelDir, "shape_predictor_68_face_landmarks.dat"))
parser.add_argument('--networkModel', type=str, help="Path to Torch network model.",
                    default=os.path.join(openfaceModelDir, 'nn4.small2.v1.t7'))
parser.add_argument('--imgDim', type=int,
                    help="Default image dimension.", default=96)
parser.add_argument('--cuda', action='store_true')
parser.add_argument('--unknown', type=bool, default=False,
                    help='Try to predict unknown people')
parser.add_argument('--port', type=int, default=9000,
                    help='WebSocket Port')
parser.add_argument('--width', type=int, default=400)
parser.add_argument('--height', type=int, default=300)
parser.add_argument('--threshold', type=float, default=0.8)
parser.add_argument(
        '--classifierModel',
        type=str,
        default=os.path.join(classifierFilelDir, 'classifier.pkl'),
        help='The Python pickle representing the classifier. This is NOT the Torch network model, which can be set with --networkModel.')
parser.add_argument('--verbose', action='store_true')

args = parser.parse_args()

align = openface.AlignDlib(args.dlibFacePredictor)
net = openface.TorchNeuralNet(args.networkModel, imgDim=args.imgDim,
                              cuda=args.cuda)


class ClockInfo:

    def __init__(self, emplId, emplName, department, date, clockInTime, clockOutTime, seq):
        self.seq = seq
        self.emplId = emplId
        self.emplName = emplName
        self.department = department
        self.date = date
        self.clockInTime = clockInTime
        self.clockOutTime = clockOutTime

    def __repr__(self):
        return "{{seq: {},emplid: {}, emplName: {},department: {},date: {},clockin: {},clockout: {}}}".format(
            self.seq,
            self.emplId,
            self.emplName,
            self.department,
            self.date,
            self.clockInTime,
            self.clockOutTime
        )


class OpenFaceServerProtocol(WebSocketServerProtocol):
    def __init__(self):
        super(OpenFaceServerProtocol, self).__init__()
        self.clockTable = {}
        self.lastDate = time.strftime("%Y-%m-%d", time.localtime())
        self.today = time.strftime("%Y-%m-%d", time.localtime())
        if args.unknown:
            self.unknownImgs = np.load("./examples/web/unknown.npy")

    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))
        # self.training = True

    def onOpen(self):
        print("WebSocket connection open.")

    def onMessage(self, payload, isBinary):
        raw = payload.decode('utf8')
        msg = json.loads(raw)
        print("Received {} message of length {}.".format(
            msg['type'], len(raw)))

        self.today = time.strftime("%Y-%m-%d", time.localtime())
        if self.today != self.lastDate:
            # print current clock table,then init clock table for today
            self.printClockTable()
            self.initClockTable(csv_file)
            self.lastDate = self.today

        if msg['type'] == "NULL":
            self.sendMessage('{"type": "NULL"}')
        elif msg['type'] == "FRAME":
            self.processFrame(msg['dataURL'])
            self.sendMessage('{"type": "PROCESSED"}')
        elif msg['type'] == "SYNC":
            # send all clock info 
            clockList = []
            for key, value in self.clockTable.items():
                clockList.append(value)
            msg = {
                "type": "SYNCDATA",
                "data": clockList
            }
            self.sendMessage(json.dumps(msg))
        elif msg['type'] == 'STORE_IMAGES':
            emplId = msg['employeeId']
            isSuc = mkdir(emplId)
            if isSuc:
                # store images in employee's folder
                for jsImage in msg['images']:
                    dataURL = jsImage['data']
                    dataSeq = jsImage['seq']
                    print("image of {} with seq number {} will be stored.".format(emplId,dataSeq))
                    head = "data:image/jpeg;base64,"
                    assert(dataURL.startswith(head))
                    imgdata = base64.b64decode(dataURL[len(head):])
                    imgF = StringIO.StringIO()
                    imgF.write(imgdata)
                    imgF.seek(0)
                    img = Image.open(imgF)

                    buf = np.fliplr(np.asarray(img))
                    rgbFrame = np.zeros((300, 400, 3), dtype=np.uint8)
                    rgbFrame[:, :, 0] = buf[:, :, 2]
                    rgbFrame[:, :, 1] = buf[:, :, 1]
                    rgbFrame[:, :, 2] = buf[:, :, 0]
                    rgbFrame[:, :, 2] = buf[:, :, 0]
                    cv2.imwrite("../cqrcb_empl/"+str(emplId) +
                                "/"+str(dataSeq)+".jpg", rgbFrame)
                msg = {
                    "type": "STORE_IMAGES",
                    "result": isSuc
                }
                self.sendMessage(json.dumps(msg))
            else:
                print("Warning:message type: {},message content is illegal".format(msg['type']))
        else:
            print("Warning: Unknown message type: {}".format(msg['type']))

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))    
    
    def processFrame(self, dataURL):
        head = "data:image/jpeg;base64,"
        assert(dataURL.startswith(head))
        imgdata = base64.b64decode(dataURL[len(head):])
        imgF = StringIO.StringIO()
        imgF.write(imgdata)
        imgF.seek(0)
        img = Image.open(imgF)

        buf = np.fliplr(np.asarray(img))
        rgbFrame = np.zeros((300, 400, 3), dtype=np.uint8)
        rgbFrame[:, :, 0] = buf[:, :, 2]
        rgbFrame[:, :, 1] = buf[:, :, 1]
        rgbFrame[:, :, 2] = buf[:, :, 0]

        annotatedFrame = np.copy(buf)

        # cv2.imshow('frame', rgbFrame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     return
        confidenceList = []
        persons, confidences, bbs = infer(rgbFrame, args)
        print("P: " + str(persons) + " C: " + str(confidences))
        try:
            # append with two floating point precision
            confidenceList.append('%.2f' % confidences[0])
        except:
            # If there is no face detected, confidences matrix will be empty.
            # We can simply ignore it.
            pass

        for i, c in enumerate(confidences):
            if c <= args.threshold:  # 0.7 is kept as threshold for known face.
                persons[i] = "_unknown"
            else:
                #emply clock in & clock out    
                strdate = time.strftime("%Y-%m-%d", time.localtime())
                strtime = time.strftime("%H:%M:%S", time.localtime())
                clock_info_i = self.clockTable[persons[i]]
                #clock in 
                if int(strTime) >= 0 and int(strTime) <=90000:                    
                    if clock_info_i['clockin'] == 'NaN':
                        clock_info_i['clockin'] = strtime
                    msg = {
                        "type": "CLOCKIN",
                        "data": clock_info_i
                    }
                    self.sendMessage(json.dumps(msg))
                #clock out
                elif int(strTime) >= 153000 and int(strTime) <=235959:
                    if clock_info_i['clockout'] == 'NaN':
                        clock_info_i['clockout'] = strtime
                    msg = {
                        "type": "CLOCKOUT",
                        "data": clock_info_i
                    }
                    self.sendMessage(json.dumps(msg))
                else:#not clock time
                    pass
                    # self.sendMessage('{"type": "WCT"}')

        # Print the person name and conf value on the frame next to the person
        # Also print the bounding box
        for idx,person in enumerate(persons):
            cv2.rectangle(annotatedFrame, (bbs[idx].left(), bbs[idx].top()), (bbs[idx].right(), bbs[idx].bottom()), (0, 255, 0), 2)
            cv2.putText(annotatedFrame, "{} @{:.2f}".format(person, confidences[idx]),
                        (bbs[idx].left(), bbs[idx].bottom()+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
        plt.figure()
        plt.imshow(annotatedFrame)
        plt.xticks([])
        plt.yticks([])

        imgdata = StringIO.StringIO()
        plt.savefig(imgdata, format='png')
        imgdata.seek(0)
        content = 'data:image/png;base64,' + \
            urllib.quote(base64.b64encode(imgdata.buf))
        msg = {
            "type": "ANNOTATED",
            "content": content
        }
        plt.close()
        self.sendMessage(json.dumps(msg))

    #init clock table from csv file
    def initClockTable(self, csvfile):
        with open(csvfile) as f:
            rowdatas = csv.DictReader(f)
            for row in rowdatas:
                # data.line_num
                # print("{}",row['emid'] row['name'] row['dep'] row['today'] row['int'] row['out'])
                # row['date'] = time.strftime("%Y-%m-%d", time.localtime())
                # row['clockin']='NaN'
                # row['clockout']='NaN'
                self.clockTable[row['emplid']] = ClockInfo(rowdatas.line_num,
                                                            row['emplid'],
                                                            row['emplName'],
                                                            row['department'],
                                                            time.strftime("%Y-%m-%d", time.localtime()),
                                                            'NaN',
                                                            'NaN')
    
    def printClockTable(self):
        headers = ['seq', 'emplid', 'emplName', 'department', 'date', 'clockin', 'clockout']
        csv_save_file = os.path.join(initSaveFilelDir, self.lastDate+"print.csv")
        with open(csv_save_file, 'w', newline='') as f:
            # header
            writer = csv.DictWriter(f, headers)
            writer.writeheader()
            # data write
            # for key in clockTable.keys():
            #     print(key)
            for key, value in self.clockTable.items():
                writer.writerow(value)
                # print(value)        

def mkdir(emplid):
    print("empl id is {}.".format(emplid))
    print("current file dir is {} .".format(fileDir))
    if not emplid:
        return False
    else:
        foldername = "../cqrcb_empl/"+str(emplid)
        isCreated = os.path.exists(foldername)
        if not isCreated:
            os.makedirs(foldername)
            return True
        else:
            print("folder has already existed!")
            return True

def getRep(bgrImg):
    start = time.time()
    if bgrImg is None:
        raise Exception("Unable to load image/frame")

    rgbImg = cv2.cvtColor(bgrImg, cv2.COLOR_BGR2RGB)

    if args.verbose:
        print("  + Original size: {}".format(rgbImg.shape))
    if args.verbose:
        print("Loading the image took {} seconds.".format(time.time() - start))

    start = time.time()

    # Get the largest face bounding box
    # bb = align.getLargestFaceBoundingBox(rgbImg) #Bounding box

    # Get all bounding boxes
    bb = align.getAllFaceBoundingBoxes(rgbImg)

    if bb is None:
        # raise Exception("Unable to find a face: {}".format(imgPath))
        return None
    if args.verbose:
        print("Face detection took {} seconds.".format(time.time() - start))

    start = time.time()

    alignedFaces = []
    for box in bb:
        alignedFaces.append(
            align.align(
                args.imgDim,
                rgbImg,
                box,
                landmarkIndices=openface.AlignDlib.OUTER_EYES_AND_NOSE))

    if alignedFaces is None:
        raise Exception("Unable to align the frame")
    if args.verbose:
        print("Alignment took {} seconds.".format(time.time() - start))

    start = time.time()

    reps = []
    for alignedFace in alignedFaces:
        reps.append(net.forward(alignedFace))

    if args.verbose:
        print("Neural network forward pass took {} seconds.".format(
            time.time() - start))

    # print (reps)
    return (reps, bb)


def infer(img, args):
    with open(args.classifierModel, 'r') as f:
        if sys.version_info[0] < 3:
                (le, clf) = pickle.load(f)  # le - label and clf - classifer
        else:
                (le, clf) = pickle.load(f, encoding='latin1')  # le - label and clf - classifer

    repsAndBBs = getRep(img)
    reps = repsAndBBs[0]
    bbs = repsAndBBs[1]
    persons = []
    confidences = []
    for rep in reps:
        try:
            rep = rep.reshape(1, -1)
        except:
            print("No Face detected")
            return (None, None)
        start = time.time()
        predictions = clf.predict_proba(rep).ravel()
        # print (predictions)
        maxI = np.argmax(predictions)
        # max2 = np.argsort(predictions)[-3:][::-1][1]
        persons.append(le.inverse_transform(maxI))
        # print (str(le.inverse_transform(max2)) + ": "+str( predictions [max2]))
        # ^ prints the second prediction
        confidences.append(predictions[maxI])
        if args.verbose:
            print("Prediction took {} seconds.".format(time.time() - start))
            pass
        # print("Predict {} with {:.2f} confidence.".format(person.decode('utf-8'), confidence))
        if isinstance(clf, GMM):
            dist = np.linalg.norm(rep - clf.means_[maxI])
            print("  + Distance from the mean: {}".format(dist))
            pass
    return (persons, confidences, bbs)

def main(reactor):
    log.startLogging(sys.stdout)
    factory = WebSocketServerFactory()
    factory.protocol = OpenFaceServerProtocol
    ctx_factory = DefaultOpenSSLContextFactory(tls_key, tls_crt)
    reactor.listenSSL(args.port, factory, ctx_factory)
    return defer.Deferred()


if __name__ == '__main__':
    task.react(main)
