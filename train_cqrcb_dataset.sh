#!/bin/bash

set -e -u

# function die { echo $1; exit 42; }

cd ~/openface

#crop data parallel
#./util/align-dlib.py ~/lfw/ align outerEyesAndNose ~/lfw_crop/
for N in {1..16}; do ./util/align-dlib.py ~/lfw align outerEyesAndNose ~/lfw_crop/ --fallbackLfw data/lfw/deepfunneled/lfw-deepfunneled & done

#gen feature of faces 73 img/s  
rm ../lfw_crop/cache.t7
./batch-represent/main.lua -cuda -outDir ~/lfw_feat -data ~/lfw_crop/

#train 20 img/s
./demos/classifier.py --cuda train ~/lfw_feat/

#Fallback to deep funneled versions for images that dlib failed to align: lfw experiment
#./util/align-dlib.py data/lfw/raw/lfw align outerEyesAndNose data/lfw/dlib-affine-sz:96 --size 96 --fallbackLfw data/lfw/deepfunneled/lfw-deepfunneled
#lfw experiment:
#./batch-represent/main.lua -outDir evaluation/lfw.nn4.small2.v1.reps -model models/openface/nn4.small2.v1.t7 -data data/lfw/dlib-affine-sz:96 -cuda
#lfw experiment:Generate the ROC curve from the evaluation directory with lfw.py command.Generate the ROC curve from the evaluation directory with
#./lfw.py nn4.small2.v1 lfw.nn4.small2.v1.reps

