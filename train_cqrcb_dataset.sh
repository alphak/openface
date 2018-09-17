#!/bin/bash

set -e -u

# function die { echo $1; exit 42; }

cd ~/openface

#crop data
#./util/align-dlib.py ~/lfw/ align outerEyesAndNose ~/lfw_crop/

#gen feature of faces 73 img/s  
rm ../lfw_crop/cache.t7
./batch-represent/main.lua -cuda -outDir ~/lfw_feat -data ~/lfw_crop/

#train 20 img/s
./demos/classifier.py --cuda train ~/lfw_feat/

