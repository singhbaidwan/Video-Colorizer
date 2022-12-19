import os
from flask import Flask, flash, request, redirect, url_for, session,jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS, cross_origin
import logging
import subprocess
import cv2

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger('HELLO WORLD')



UPLOAD_FOLDER = '/Users/dalveersingh/Downloads/College/testing capstone/data_upload'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif','.mp4'])
def runSuperResolution():
    os.chdir('/Users/dalveersingh/Downloads/College/testing capstone/app/server')
    arr2 = ["python3","test.py"]
    subprocess.run(arr2)

def convertToVideo():
    os.chdir(UPLOAD_FOLDER)
    img_array = []
    name = []
    path = "/Users/dalveersingh/Downloads/College/testing capstone/data_upload/Result"
    for f in os.listdir(path):
        filename = path+"/"+f
        name.append(filename)
    name.sort()
    for filename in name:
        img = cv2.imread(filename)
        height, width, layers = img.shape
        size = (width,height)
        img_array.append(img)
    
    out = cv2.VideoWriter('project.avi',cv2.VideoWriter_fourcc(*'DIVX'), 30, size)
 
    for i in range(len(img_array)):
        out.write(img_array[i])
    out.release()


def FrameCapture(path):
    vidObj = cv2.VideoCapture(path)
    count = 0
    success = 1
    while success:
        success, image = vidObj.read()
        if success:
            cv2.imwrite("frame%04d.jpg" % count, image)
        count += 1
  
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/success',methods=['POST','GET'])
def success(name):
   return 'welcome'



@app.route('/upload1', methods=['POST','GET'])
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
    arr=["python", "-m", "tcvc.apply","--input-path","/Users/dalveersingh/Downloads/College/testing capstone/data_upload/ImageData","--input-style", "greyscale", "--model", "/Users/dalveersingh/Downloads/College/testing capstone/weights-greyscale/20-25/netG_LA2_weights_epoch_5.pth"]
    
    subprocess.run(arr)
    
    session['uploadFilePath']=destination
    # extention = ".mp4"
    response = jsonify({'some': 'data'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    if extention == ".mp4":
        convertToVideo()
    return response
    # return response


@app.route('/upload2', methods=['POST'])
def fileUpload2():
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
    print("USING LINE ART")
    os.chdir('/Users/dalveersingh/Downloads/College/testing capstone/app/server/automatic-video-colorization')
    arr=["python", "-m", "tcvc.apply","--input-path","/Users/dalveersingh/Downloads/College/testing capstone/data_upload/ImageData","--input-style", "greyscale", "--model", "/Users/dalveersingh/Downloads/College/testing capstone/weights-line-art/final/netG_LA2_weights_epoch_5.pth"]
    
    subprocess.run(arr)
    
    
    session['uploadFilePath']=destination
    response = jsonify({'some': 'data'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    if extention == ".mp4":
        convertToVideo()
    return response

if __name__ == "__main__":
    app.secret_key = os.urandom(24)
    app.run(debug=True,host="0.0.0.0",port = 4000,use_reloader=False)

flask_cors.CORS(app, expose_headers='Authorization')