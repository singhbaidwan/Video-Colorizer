import os
from flask import Flask, flash, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from flask_cors import CORS, cross_origin
import logging
import subprocess
import cv2

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('HELLO WORLD')



UPLOAD_FOLDER = '/Users/dalveersingh/Downloads/College/testing capstone/data_upload'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','.mp4'])
def FrameCapture(path):
    vidObj = cv2.VideoCapture(path)
    count = 0
    success = 1
    while success:
        success, image = vidObj.read()
        cv2.imwrite("frame%04d.jpg" % count, image)
        count += 1
  
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/upload', methods=['POST'])
def fileUpload():
    target=os.path.join(UPLOAD_FOLDER,'test_docs')
    if not os.path.isdir(target):
        os.mkdir(target)
    logger.info("welcome to upload`")
    file = request.files['file'] 
    filename = secure_filename(file.filename)
    destination="/".join([target, filename])
    file.save(destination)
    #Create Image Data folder
    subprocess.run(
        ["mkdir","{}".format(UPLOAD_FOLDER+"/"+"ImageData")]
    )
    subprocess.run(
        ["mkdir","{}".format(UPLOAD_FOLDER+"/"+"Result")]
    )
    root, extention = os.path.splitext(destination)
    if extention == ".mp4":
        os.chdir(UPLOAD_FOLDER+"/"+"ImageData")
        FrameCapture(destination)
    else:
        subprocess.run(["mv",destination,UPLOAD_FOLDER+"/"+"ImageData"])
        
    os.chdir('/Users/dalveersingh/Downloads/College/testing capstone/app/server/automatic-video-colorization')
    arr=["python", "-m", "tcvc.apply","--input-path","/Users/dalveersingh/Downloads/College/testing capstone/data_upload/ImageData","--input-style", "greyscale", "--model", "/Users/dalveersingh/Downloads/College/testing capstone/weights-greyscale/16-20/netG_LA2_weights_epoch_5.pth"]
    subprocess.run(arr)
    session['uploadFilePath']=destination
    response="Whatever you wish too return"
    return response

if __name__ == "__main__":
    app.secret_key = os.urandom(24)
    app.run(debug=True,host="0.0.0.0",port = 4000,use_reloader=False)

flask_cors.CORS(app, expose_headers='Authorization')