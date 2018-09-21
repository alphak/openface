#!/bin/bash

set -e -u

# function die { echo $1; exit 42; }

cd ~/openface

# crop data parallel
# ./util/align-dlib.py ~/lfw/ align outerEyesAndNose ~/lfw_crop/

# Fallback to deep funneled versions for images that dlib failed to align: lfw experiment
# ./util/align-dlib.py data/lfw/raw/lfw align outerEyesAndNose data/lfw/dlib-affine-sz:96 --size 96 --fallbackLfw data/lfw/deepfunneled/lfw-deepfunneled
# lfw experiment:
# ./batch-represent/main.lua -outDir evaluation/lfw.nn4.small2.v1.reps -model models/openface/nn4.small2.v1.t7 -data data/lfw/dlib-affine-sz:96 -cuda
# lfw experiment:Generate the ROC curve from the evaluation directory with lfw.py command.Generate the ROC curve from the evaluation directory with
# ./lfw.py nn4.small2.v1 lfw.nn4.small2.v1.reps

# for N in {1..16}; do ./util/align-dlib.py ~/cqrcb_empl align outerEyesAndNose ~/cqrcb_crop/ & done
if [ -f ../cqrcb_crop/cache.t7 ]; then rm -rf ../cqrcb_crop/*; fi
if [ -f ../cqrcb_feat/classifier.pkl ]; then rm -rf ../cqrcb_feat/*; fi

# crop the face
./util/align-dlib.py ~/cqrcb_empl align outerEyesAndNose ~/cqrcb_crop

# gen feature of faces 73 img/s and gen lable.csv reps.csv
./batch-represent/main.lua -cuda -outDir ~/cqrcb_feat -data ~/cqrcb_crop

# train 20 img/s and gen classifier.pkl 
./demos/classifier.py --cuda train ~/cqrcb_feat