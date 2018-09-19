navigator.getUserMedia = navigator.getUserMedia ||
    navigator.webkitGetUserMedia ||
    (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) ?
    function (c, os, oe) {
        navigator.mediaDevices.getUserMedia(c).then(os, oe);
    } : null ||
    navigator.msGetUserMedia;

window.URL = window.URL ||
    window.webkitURL ||
    window.msURL ||
    window.mozURL;
/*
hwd:here we define a function of our own in jquery's name space "fn" ,
whose name is "pressEnter",
*/

function registerHbarsHelpers() {
    // http://stackoverflow.com/questions/8853396
    Handlebars.registerHelper('ifEq', function (v1, v2, options) {
        if (v1 === v2) {
            return options.fn(this);
        }
        return options.inverse(this);
    });
}


function sendFrameLoop() {
    if (socket == null || socket.readyState != socket.OPEN ||
        !vidReady || numNulls != defaultNumNulls) {
        return;
    }
   
    if (tok > 0) {
        var canvas = document.createElement('canvas');
        canvas.width = vid.width;
        canvas.height = vid.height;
        var cc = canvas.getContext('2d');
        cc.drawImage(vid, 0, 0, vid.width, vid.height);
        var apx = cc.getImageData(0, 0, vid.width, vid.height);

        var dataURL = canvas.toDataURL('image/jpeg', 1.0);

        var msg = {
            'type': 'FRAME',
            'dataURL': dataURL,
            'identity': defaultPerson
        };
        socket.send(JSON.stringify(msg));
        tok--;
    }
    setTimeout(function () {
        requestAnimFrame(sendFrameLoop)
    }, 250);
}




function getDataURLFromRGB(rgb) {
    var rgbLen = rgb.length;

    var canvas = $('<canvas/>').width(96).height(96)[0];
    var ctx = canvas.getContext("2d");
    var imageData = ctx.createImageData(96, 96);
    var data = imageData.data;
    var dLen = data.length;
    var i = 0,
        t = 0;

    for (; i < dLen; i += 4) {
        data[i] = rgb[t + 2];
        data[i + 1] = rgb[t + 1];
        data[i + 2] = rgb[t];
        data[i + 3] = 255;
        t += 3;
    }
    ctx.putImageData(imageData, 0, 0);

    return canvas.toDataURL("image/png");
}


function sendImageCache() {
    var msg = {
        'type': 'STORE_IMAGES',
        'images': imageCache,
        'employeeId': employeeId
    };
    socket.send(JSON.stringify(msg));
}

function createSocket(address, name) {
    socket = new WebSocket(address);
    socketName = name;
    socket.binaryType = "arraybuffer";
    socket.onopen = function () {
        $("#serverStatus").html("Connected to " + name);
        sentTimes = [];
        receivedTimes = [];
        tok = defaultTok;
        numNulls = 0

        socket.send(JSON.stringify({
            'type': 'NULL'
        }));
        sentTimes.push(new Date());
    }
    socket.onmessage = function (e) {
        console.log(e);
        j = JSON.parse(e.data)
        if (j.type == "NULL") {
            receivedTimes.push(new Date());
            numNulls++;
            if (numNulls == defaultNumNulls) {
                //updateRTT();
                //sendState();
                //sendFrameLoop();
                capImgs();
            } else {
                socket.send(JSON.stringify({
                    'type': 'NULL'
                }));
                sentTimes.push(new Date());
            }
        } else if (j.type == "PROCESSED") {
            tok++;
        } else if (j.type == "NEW_IMAGE") {
            images.push({
                hash: j.hash,
                identity: j.identity,
                image: getDataURLFromRGB(j.content),
                representation: j.representation
            });
            redrawPeople();
        } else if (j.type == "ANNOTATED") {
            $("#detectedFaces").html(
                "<img src='" + j['content'] + "' width='430px'></img>"
            )
        } else if (j.type == "STORE_IMAGES") {
            var h;
            if (j.result) {
                h = "Images have sent to server and saved as .jpg files successfully:!!!";
            }else{
                h = "Images send error:!!!";
            }
            $("#SendResult").html(h);
            console.log("Image save status: " + j.result);
        } else {
            console.log("Unrecognized message type: " + j.type);
        }
    }
    socket.onerror = function (e) {
        console.log("Error creating WebSocket connection to " + address);
        console.log(e);
    }
    socket.onclose = function (e) {
        if (e.target == socket) {
            $("#serverStatus").html("Disconnected.");
        }
    }
}

function umSuccess(stream) {
    if (vid.mozCaptureStream) {
        vid.mozSrcObject = stream;
    } else {
        vid.src = (window.URL && window.URL.createObjectURL(stream)) ||
            stream;
    }
    vid.play();
    vidReady = true;
    //sendFrameLoop();

    //capImgs(); //for test
    //redrawPeople();
}

function redrawPeople() {

}

function changeServerCallback() {
    $(this).addClass("active").siblings().removeClass("active");
    switch ($(this).html()) {
        case "Local":
            socket.close();
            redrawPeople();
            createSocket("wss:" + window.location.hostname + ":9000", "Local");
            break;
        case "CMU":
            socket.close();
            redrawPeople();
            createSocket("wss://facerec.cmusatyalab.org:9000", "CMU");
            break;
        case "AWS East":
            socket.close();
            redrawPeople();
            createSocket("wss://54.159.128.49:9000", "AWS-East");
            break;
        case "AWS West":
            socket.close();
            redrawPeople();
            createSocket("wss://54.188.234.61:9000", "AWS-West");
            break;
        default:
            alert("Unrecognized server: " + $(this.html()));
    }
}