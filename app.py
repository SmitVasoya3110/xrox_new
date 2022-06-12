# from crypt import methods
import errno
import time
import os
import subprocess
import json
import configparser
import  logging
import uuid
# import socket
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, decode_token
from jinja2 import Environment, PackageLoader, select_autoescape
import datetime
from flask_cors import CORS
import magic
from flask_mysqldb import MySQL
import PyPDF2 as pypdf
from flask_mail import Mail, Message
import threading
import stripe
from stripe import error as stripe_error
import mimetypes

from flask import Flask, request, redirect, jsonify, copy_current_request_context
from werkzeug.utils import secure_filename

from square.client import Client

welcome_message = "Welcome to Online Printing. You have successfully registered with us.\nThank you..."

stripe.api_key = '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'
# stripe.api_key = 'sk_test_51KNpBmDiddQAhMW0bxLCLiUvtVWYguCrcucBj9bJmdPc9X85uGqMWD098FAyDaLqDjeG1iCVGWLuiP1a2qqB8Hm300FR6q18Dv'
endpoint_secret = ''


# SQUARE PAYMENT METHOD SETUP
config = configparser.ConfigParser()
config.read('config.ini')
CONFIG_TYPE = config.get("DEFAULT", "environment").upper()
"""PAYMENT_FROM_URL = (
"https://web.squarecdn.com/v1/square.js" # change accordingly
    if CONFIG_TYPE == "PRODUCTION"
    else "https://sandbox.web.squarecdn.com/v1/square.js" # change accordingly
)"""

APPLICATION_ID = config.get(CONFIG_TYPE, "square_application_id")
LOCATION_ID = config.get(CONFIG_TYPE, "square_location_id")
ACCESS_TOKEN = config.get(CONFIG_TYPE, "square_access_token")
client = Client(access_token=ACCESS_TOKEN,
    environment=config.get("DEFAULT", "environment"))
ACCOUNT_CURRENCY = "AUD"


app = Flask(__name__)
CORS(app)

jnj_env = Environment(
    loader=PackageLoader("app"),
    autoescape=select_autoescape()
)

app.config['SECRET_KEY'] = 'smit-->p-->this__is~secret886651234'
jwt = JWTManager(app)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'ssssmmmmiiiitttt@gmail.com'
app.config['MAIL_PASSWORD'] = 'dbzxmyxliwpgdjyh'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['ORDER_MAIL'] = "smitvasoya3110@gmail.com"
mail = Mail(app)

app.config['MYSQL_HOST'] = 'db'  # db
app.config['MYSQL_USER'] = 'root'  # root
# app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_PASSWORD'] = 'print1234'  # print1234
app.config['MYSQL_DB'] = "print"
mysql = MySQL(app)
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 24

MIME = ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword',
        'application/vnd.oasis.opendocument.text-master']
ABN = 16612402767
COMPANY = "Printing 7 Bondi"


@app.errorhandler(413)
def too_large(e):
    return {"message": "File/s is/are too large. limit is 24 MB", "limit": "24 MB"}, 413


@app.errorhandler(500)
def internal_error(e):
    return {"error": "There is Internal Server Error"}


@app.errorhandler(401)
def unauthorized(e):
    return {"error":"Unauthorized attempt...Please login again and try"}

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}


def check_email(email):
    qry = "select Email_Id from Customer_Master where Email_Id = %s"
    # cur = mysql2.connection.cursor()
    cur = mysql.connection.cursor()
    cur.execute(qry, (email,))
    result = cur.fetchone()
    cur.close()
    if result:
        return 1
    else:
        return 0


def A4_BC(num: int):
    if 1 <= num <= 3:
        cost = 3
        return cost
    if 3 <= num < 30:
        cost = 3 + (num - 3) * 0.3
        return cost
    if 30 <= num < 100:
        cost = (29 * 0.3) + (num - 29) * 0.2
        return cost
    if num >= 100:
        cost = (99 * 0.2) + (num - 99) * 0.1
        return cost
    if num<=0:
        return 0.0

def A3_BC(num: int):
    if 1 <= num <= 3:
        cost = 3
        return cost
    if 3 < num < 30:
        cost = 3 + (num - 3) * 0.6
        return cost
    if 30 <= num < 100:
        cost = (29 * 0.6) + (num - 29) * 0.4
        return cost
    if num >= 100:
        cost = (99 * 0.4) + (num - 99) * 0.2
        return cost
    if num<=0:
        return 0.0


def A4_C(num: int):
    if 1 <= num <= 3:
        cost = 3
        return cost
    if 3 <= num < 30:
        cost = 3 + (num - 3) * 0.8
        return cost
    if 30 <= num < 100:
        cost = (29 * 0.8) + (num - 29) * 0.5
        return cost
    if num >= 100:
        cost = (99 * 0.5) + (num - 99) * 0.3
        return cost
    if num<=0:
        return 0.0

def A3_C(num: int):
    if num == 1:
        cost = 3
        return cost
    if 2 <= num < 30:
        cost = 3 + (num - 1) * 1.6
        return cost
    if 30 <= num < 100:
        cost = (29 * 1.6) + (num - 29) * 1.0
        return cost
    if num >= 100:
        cost = (99 * 1.0) + (num - 99) * 0.6
        return cost
    if num<=0:
        return 0.0

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/CustomerLogin', methods=['POST'])
def CustomerLogin():
    json_data = request.json
    email = json_data.get('Email_Id', '')
    password = json_data.get('Password', '')
    if not email or not password:
        return jsonify({"message": "Credential Needed"})
    try:
        cur = mysql.connection.cursor()
        # cur = con.cursor(pymysql.cursors.DictCursor)
        sql = """SELECT *
                 FROM `Customer_Master`
                 where Email_Id='""" + email + """' and Password='""" + password + """' and status='1'
              """
        # data = (Email_Id, password)
        cur.execute(sql)
        rows = cur.fetchone()
        cur.close()
        print(rows)

        if not rows:
            return jsonify({"message": "Enter Valid Email_Id or Password"}), 401

        # mysql.connection.close()
        if len(rows) > 0:
            dic1 = {}

            dic2 = {}
            dic3 = {}
            expires = datetime.timedelta(hours=2)
            dic1["access_token"] = create_access_token(identity=rows[3], expires_delta=expires)
            # dic1["refresh_token"] = create_refresh_token(identity=i[3])

            dic2["role"] = "Customer"
            dic2["uuid"] = rows[0]

            dic3["displayName"] = rows[1]
            dic3["email"] = rows[3]
            dic3["photoURL"] = ""

            dic2["data"] = dic3

            dic1["user"] = dic2

            # res = jsonify(dic1)
            # res.status_code = 200
            print(dic1)
            if not os.path.isdir(os.path.join(app.config['UPLOAD_FOLDER'], str(dic2['uuid']))):
                os.mkdir(os.path.join(app.config['UPLOAD_FOLDER'], str(dic2['uuid'])))
            return dic1

            # return res


    except Exception as e:
        print(e)
        return ({"error": "There was an error"})


@app.route("/Customer", methods=["POST"])
def register_user():  # add new Customer -- MYSQL table : Customer_Master
    try:
        @copy_current_request_context
        def send_email(receiver):
            msg = Message('Welcome to Print', sender=app.config['MAIL_USERNAME'], recipients=[receiver])
            print(msg)
            msg.body = welcome_message
            mail.send(msg)

        now = datetime.datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        json_data = request.json
        email = json_data.get('Email_Id', '')
        first_name = json_data.get('FirstName', '')
        last_name = json_data.get('LastName', '')
        password = json_data.get('Password', '')
        mobile = json_data.get('Mobile', 0)
        if not email or not first_name or not last_name or not password:
            return {"message": "Fields are missing"}
        if check_email(email):
            return {"message": "Email is already in use"}
        status = 1
        sql = """INSERT INTO `Customer_Master` (`FirstName`, `LastName`, `Email_Id`, `Password`, `status`, `dateAdded`, `mobile`)
                 VALUES (%s,%s,%s,%s,%s,%s,%s);"""
        data = (first_name, last_name, email, password, status, dt_string, mobile)
        print("SQL QUERY AND DATA ", sql, data)
        cur = mysql.connection.cursor()
        cur.execute(sql, data)
        mysql.connection.commit()
        cur.close()
        threading.Thread(target=send_email, args=(email,)).start()

        resp = jsonify({'message': 'Customer Is Added Successfully'})
        resp.status_code = 200
        return resp
    except Exception as e:

        print(e)
        return {}, 400


# @app.route('/register', methods=['POST'])
# def register():
#     @copy_current_request_context
#     def send_email(receiver):
#         msg = Message('Welcome to Print', sender=app.config['MAIL_USERNAME'], recipients=[receiver])
#         print(msg)
#         msg.body = welcome_message
#         mail.send(msg)
#
#     start = time.perf_counter()
#     if request.method == 'POST':
#         content_type = request.headers.get('Content-Type')
#         if content_type == 'application/json':
#             json_data = request.json
#             email = json_data.get('email', 0)
#             first_name = json_data.get('first_name', 0)
#             last_name = json_data.get('last_name', 0)
#             password = json_data.get('password', 0)
#             mobile = int(json_data.get('mobile', 0))
#             print(email, first_name, last_name, password, mobile)
#             if email and first_name and last_name and password and mobile:
#                 qry = "insert into user (email, password, first_name, last_name, mobile) values (%s,%s,%s,%s,%s)"
#                 values = (email, password, first_name, last_name, mobile)
#                 cur = mysql.connection.cursor()
#                 cur.execute(qry, values)
#                 mysql.connection.commit()
#                 # t1 = Process(target=send_email, args=(email,))
#                 # t1.start()
#                 # # t1.join()
#                 # send_email(email)
#                 thread = threading.Thread(target=send_email, args=(email,))
#                 thread.start()
#                 return {"Success": "Inserted Successfully"}
#             else:
#                 print("Seconds", time.perf_counter() - start)
#                 return "Values are missing or not correct"
#         else:
#             return 'Content-Type not supported!'
#
#     return "Server is Up and running"

@app.route('/multiple-files-upload', methods=['POST'])
def upload_file():
    try:
        print("In Upload API")
        # check if the post request has the file part
        size, typ = request.form['docFormat'].split('_')
        page_format = request.form['pageFormat']
        if 'files[]' not in request.files:
            resp = jsonify({'message': 'No file part in the request'})
            resp.status_code = 400
            return resp

        files = request.files.getlist('files[]')

        num_dict = {'numbers': []}
        if False in [allowed_file(file.filename) for file in files]:
            return jsonify({"message": "check your file type", "allowed": list(ALLOWED_EXTENSIONS)}), 422
        total_pages = 0
        for file in files:

            filename = secure_filename(file.filename)
            print(file.mimetype)

            if file.mimetype == "application/pdf":
                npath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(npath)
                with open(npath, 'rb') as fpath:
                    read_pdf = pypdf.PdfFileReader(fpath)
                    num_pages = read_pdf.getNumPages()
                    num_dict['numbers'].append({"filename": filename, 'pages': num_pages})
                    print("NUM DICT +++", num_dict)
                    total_pages += num_pages

            if file.mimetype == "image/jpeg" or file.mimetype == "image/png" or file.mimetype == "image/jpg":
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename)))
                if 'Total_Images' in num_dict.keys():
                    num_dict['Total_Images'] += 1
                else:
                    num_dict['Total_Images'] = 1
                total_pages += 1

            if file.mimetype in MIME:
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                source = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                destination = app.config['UPLOAD_FOLDER']
                output = subprocess.run(
                    ["libreoffice", '--headless', '--convert-to', 'pdf', source, '--outdir', destination])
                print(output)
                new_dest = os.path.splitext(destination + f'/{filename}')[0] + ".pdf"
                with open(new_dest, 'rb') as fpath:
                    read_pdf = pypdf.PdfFileReader(fpath)
                    num_pages = read_pdf.getNumPages()
                    num_dict['numbers'].append({"filename": filename, 'pages': num_pages})
                    print(num_pages)
                    total_pages += num_pages
                print("On Going")

        num_dict['Total_Pages'] = total_pages
        if size == "A4" and typ.lower() == 'color':
            num_dict['Total_cost'] = round(A4_C(total_pages), 2)
        if size == "A4" and typ.lower() == 'bw':
            num_dict['Total_cost'] = round(A4_BC(total_pages), 2)
        if size == "A3" and typ.lower() == 'color':
            num_dict['Total_cost'] = round(A3_C(total_pages), 2)
        if size == "A3" and typ.lower() == 'bw':
            num_dict['Total_cost'] = round(A3_BC(total_pages), 2)
        num_dict['page_format'] = page_format
        # if success and errors:
        #     errors['message'] = 'File(s) successfully uploaded'
        #     resp = jsonify({"errors": errors, "number": num_dict})
        #     resp.status_code = 500
        #     return resp

        resp = jsonify({'message': 'Files successfully uploaded', "numbers": num_dict})
        resp.status_code = 201
        return resp
    except Exception as e:
        print(e)
        return {"message": "There was an error"}, 500


job_msg = "Your job as an email posted"


@app.route('/place/order', methods=["POST"])
def place_order():
    try:
        try:
            json_data = request.json
            user_id = json_data.get('user_id')
            # size, typ = json_data.get('type', ' _ ').split('_')
            files = json_data.get('files', [])
            amount = json_data.get('amount')
            # sides = json_data.get('pageFormat')
        except Exception as e:
            print(e)
            return {"message": "Invalid data sent"}, 402

        print(type(json.dumps(files)))
        # print("++" * 20, type(user_id), size, typ, type(files), amount)
        try:
            qry = "insert into orders (user_id, size, type, sides, files, amount) values (%s,%s,%s,%s,%s,%s)"
            values = (user_id, 'various', "various", "various", json.dumps(files), amount)
            cur = mysql.connection.cursor()
            cur.execute(qry, values)
            mysql.connection.commit()
            last_id = cur.lastrowid
        except Exception as e:
            print(e)
            return {"message": "There is an error in Database"}, 500

        return jsonify({"message": "OK", "order_id": last_id, "amount": amount}), 200

    except Exception as e:
        return {"message": "Internal Server Error"}, 500


#
# @app.route("/get", methods=["GET"])
# def fun():
#     qry = "select * from orders"
#     cur = mysql.connection.cursor()
#     cur.execute(qry)
#     res = list(cur.fetchall())
#     for items in res:
#         items = list(items)
#         items[4] = json.loads(items[4], object_hook=str)
#         print(items[4])
#
#     print(res)
#     return {"Res": res}



@app.route('/confirm/order', methods=["POST"])
def confirm_payment():
    
    @copy_current_request_context
    def send_attachment(order_id: int, files: list, psize: str, side: str, amount: float, receiver: str, timestamp:str):
        msg = Message('Order', sender=app.config['MAIL_USERNAME'], recipients=[app.config['ORDER_MAIL']])
        msg.body = f"Order has been received with <order_id:{order_id}> from <{receiver}>"
        fpath = []
        # rel_files = []
        print(files)
        for file in files:
            file = secure_filename(file)
            print(file)
            nme = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id), timestamp,file)
            fpath.append(nme)
            print("Full Path.....=>", nme)
            buf = open(nme, 'rb').read()
            print(magic.from_buffer(buf, mime=True))
            msg.attach(file, magic.from_buffer(buf, mime=True), buf)
            # rel_files.append(file.split('_')[6])
        print("Sending Mail")
        mail.send(msg)
        print("successful sending")
        msg = Message("Customer Receipt", sender=app.config['MAIL_USERNAME'], recipients=[receiver])
        main_ = F"Details of the Order Placed:\n\n Order Id: {order_id} \n Total Price: ${amount}"
        msg.body = main_
        for file in files:
            uid, mimet, size, typ, side_, dstamp, filename = file.split('_', 6)
            msg.body +=f"File-Details: {filename}, type: {typ}, size: {size}, sides: {side_} \n"
        msg.body += f"ABN: {ABN} \n Company: {COMPANY}"    
        mail.send(msg)
        print("to the client")

        for pth in fpath:
            if os.path.isfile(pth) and os.path.exists(pth):
                os.remove(pth)
                continue
            continue


    json_data = request.json
    order_id = json_data.get('order_id')
    files = json_data.get('files')
    user_id = json_data.get('user_id')
    email = json_data.get('email')
    amount = json_data.get('amount')
    tstamp = json_data.get('order_id')
    if order_id and files and amount and email:
        qry = "insert into payments (order_id, user_id,amount, is_successful) values (%s, %s, %s, %s)"
        cur = mysql.connection.cursor()
        cur.execute(qry, (order_id, user_id, amount, 1))
        mysql.connection.commit()
        # threading.Thread(target=send_attachment, args=(order_id, files, psize, sides, amount, email)).start()
       
        ftch = "SELECT sides, size, type from orders WHERE order_id = %s"
        cur.execute(ftch, (order_id,))
        res = cur.fetchone()
        cur.close()
        sides = res[0]
        psize = res[1]+"_"+res[2]
        threading.Thread(target=send_attachment, args=(order_id, files, psize, sides, amount, email, tstamp)).start()

# 
# @app.route('/uploads', methods=["POST"])
# def attach_mail():
#     files_details = []
#
#     @copy_current_request_context
#     def send_with_attachment(receiver, files):
#         msg = Message(job_msg, sender=app.config['MAIL_USERNAME'], recipients=[receiver])
#         print(msg)
#         msg.body = "Your files"
#         for file in files:
#             msg.attach(file[0].filename, file[1],
#                        open(os.path.join(app.config['UPLOAD_FOLDER'], file[0].filename), 'rb').read())
#         mail.send(msg)
#
#     for files in request.files.getlist('files[]'):
#         files_details.append([files, files.mimetype])
#     print(files_details)
#     threading.Thread(target=send_with_attachment, args=('ssssmmmmiiiitttt@gmail.com', files_details)).start()
#     return jsonify({"message": "OK"})


@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    @copy_current_request_context
    def send_email(receiver, url):
        msg = Message(sender=app.config['MAIL_USERNAME'], recipients=[receiver])
        print(msg)
        msg.body = "Following is the reset password link. It will be expired in 2 hours\n" + str(url)
        mail.send(msg)

    # print("..",_doc_(request))

    # url = request.host_url + 'Reset'
    url = "https://printing7.com/Reset/"
    body = request.get_json()
    Email_Id = body.get('Email_Id')
    if not Email_Id:
        return {"message": "Email_Id is requred"}, 400

    sql = """
     SELECT * FROM `Customer_Master` where Email_Id = '""" + str(Email_Id) + """' and status='1'
     """
    cur = mysql.connection.cursor()
    cur.execute(sql)
    result = cur.fetchone()
    cur.close()
    if not result:
        return {"message": "Invalid Email ID"}, 400
    print("result", result)
    print("headers", request.headers)

    expires = datetime.timedelta(hours=1)
    reset_token = create_access_token(str(result[3]), expires_delta=expires)
    # return 0
    url += str(reset_token)
    print("url", url)
    thread = threading.Thread(target=send_email, args=(Email_Id, url)).start()
    # thread.start()
    return {"message": "email was send for reset password"}


@app.route('/reset-password', methods=['POST'])
def reset_password():
    body = request.json
    print("body", body)
    if body is None:
        return {"message": "Invalid JSON"}, 400
    reset_token = body.get('reset_token')
    Password = body.get('Password')
    if not reset_token or not Password:
        return {"message": "Plz Provide reset_token and password"}, 400

    user_id = decode_token(reset_token)['sub']
    print(user_id)
    print("user_id", user_id)
    if not user_id:
        return {"message": "Invalid Reset Token"}, 400

    if not check_email(user_id):
        return {"message": "Invalid User"}
    # sql = """
    #  SELECT * FROM `Customer_Master` where id = '"""+str(user_id)+"""' and status='1'
    #  """
    # cur = mysql.connection.cursor()
    # cur.execute(sql)
    # result = cur.fetchone()
    # cur.close()
    # if not result:
    #     return {"message":"Invaild User"},400

    sql = """
    update Customer_Master set Password='""" + str(Password) + """'
    where Email_Id='""" + str(user_id) + """' and status='1'
    """
    cur = mysql.connection.cursor()
    cur.execute(sql)
    mysql.connection.commit()
    # result = cursor.fetchone()
    cur.close()
    return {"message": "Password was reset"}


@app.route('/refresh-token', methods=['POST', 'GET'])
def refresh_token():
    # retrive the user's identity from the refresh token using a Flask-JWT-Extended built-in method
    current_user = get_jwt_identity()
    # return a non-fresh token for the user
    new_token = create_access_token(identity=current_user)
    return {'access_token': new_token}, 200


@app.route('/pay', methods=['POST'])
def pay():
    @copy_current_request_context
    def send_attachment(order_id: int, files: list, psize: str, side: str, amount: float, receiver: str, timestamp:str):
            msg = Message('Order', sender=app.config['MAIL_USERNAME'], recipients=[app.config['ORDER_MAIL']])
            msg.body = f"Order has been received with <order_id:{order_id}> from <{receiver}>"
            fpath = []
            # rel_files = []
            print(files)
            for file in files:
                quantity = file['quantity']
                filen = secure_filename(file['file'])
                print(filen)
                nme = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id), timestamp,filen)
                fpath.append(nme)
                print("Full Path.....=>", nme)
                buf = open(nme, 'rb').read()
                print(magic.from_buffer(buf, mime=True))
                filen = f'{quantity}_copies_' + filen
                msg.attach(filen, magic.from_buffer(buf, mime=True), buf)
                # rel_files.append(file.split('_')[6])
            print("Sending Mail")
            mail.send(msg)
            print("successful sending")
            msg = Message("Customer Receipt", sender=app.config['MAIL_USERNAME'], recipients=[receiver])
            main_ = F"Details of the Order Placed"
            msg.body = main_
            array_html = []
            for file in files:
                quantity = file['quantity']
                uid, mimet, size, typ, side_, dstamp, filename = file['file'].split('_', 6)
                temp_dict = {'filename':filename, 'size':size, 'side':side_, 'color':typ, 'copies':quantity}
                array_html.append(temp_dict)
            template = jnj_env.get_template('emailer.html')
            msg.html = template.render(order_id=order_id, amount=amount, files=array_html)     
            mail.send(msg)
            print("to the client")

            for pth in fpath:
                if os.path.isfile(pth) and os.path.exists(pth):
                    os.remove(pth)
                    continue
                continue

    try:
        jsdata = request.get_json()
        print("THIS IS JSON DATA", jsdata)
        email = jsdata.get('email')
        amount = jsdata.get('amount')
        user_id = jsdata.get('user_id')
        files = jsdata.get('files')
        order_id = jsdata.get('order_id')
        tstamp = jsdata.get('timestamp')
        token = jsdata.get('token')

        if not email:
            return 'You need to send an Email!', 400

        create_payment_response = client.payments.create_payment(
            body={
                "source_id": token,
                "idempotency_key": str(uuid.uuid4()),
                "amount_money": {
                    "amount": amount * 100,
                    "currency": ACCOUNT_CURRENCY,
                }
            }
        )
        if create_payment_response.is_success():
            res = create_payment_response.body

            print("create_payment_response", create_payment_response)
            sqlq = "INSERT INTO payments (user_id,order_id,amount, charged_id, is_successful) VALUES (%s,%s,%s,%s,%s)"
            insert_data = (user_id, order_id, amount, res['checkout']['id'], 1)
            print(insert_data)
            cur = mysql.connection.cursor()
            cur.execute(sqlq, insert_data)
            mysql.connection.commit()

            ftch = "SELECT sides, size, type, files from orders WHERE order_id = %s"
            cur.execute(ftch, (order_id,))
            res = cur.fetchone()
            cur.close()
            sides = res[0]
            psize = res[1]+"_"+res[2]
            files = json.loads(res[3])
            threading.Thread(target=send_attachment, args=(order_id, files, psize, sides, amount, email, tstamp)).start()
            return create_payment_response.body
        elif create_payment_response.is_error():
            # return create_payment_response
            print("==ERROR=="*20)
            print("create_payment_response", create_payment_response)

        return {"message": "Your payment is not succeeded. Try again with reducing files or with short filenames"}, 500

    #     intent = stripe.PaymentIntent.create(
    #         amount=int(amount*100),
    #         currency='aud',
    #         receipt_email=email,
    #         metadata={
    #             'order_id': order_id,
    #             'user_id': user_id,
    #             'email': email,
    #             'amount': amount,
    #             'timestamp':str(tstamp)
    #         }
    #     )
    #
    #     return {"client_secret": intent['client_secret']}, 200
    except Exception as e:
        return {"message": "Your payment is not succeeded. Try again with reducing files or with short filenames"}

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        @copy_current_request_context
        def send_attachment(order_id: int, files: list, psize: str, side: str, amount: float, receiver: str, timestamp:str):
            msg = Message('Order', sender=app.config['MAIL_USERNAME'], recipients=[app.config['ORDER_MAIL']])
            msg.body = f"Order has been received with <order_id:{order_id}> from <{receiver}>"
            fpath = []
            # rel_files = []
            print(files)
            for file in files:
                quantity = file['quantity']
                filen = secure_filename(file['file'])
                print(filen)
                nme = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id), timestamp,filen)
                fpath.append(nme)
                print("Full Path.....=>", nme)
                buf = open(nme, 'rb').read()
                print(magic.from_buffer(buf, mime=True))
                filen = f'{quantity}_copies_' + filen
                msg.attach(filen, magic.from_buffer(buf, mime=True), buf)
                # rel_files.append(file.split('_')[6])
            print("Sending Mail")
            mail.send(msg)
            print("successful sending")
            msg = Message("Customer Receipt", sender=app.config['MAIL_USERNAME'], recipients=[receiver])
            main_ = F"Details of the Order Placed"
            msg.body = main_
            array_html = []
            for file in files:
                quantity = file['quantity']
                uid, mimet, size, typ, side_, dstamp, filename = file['file'].split('_', 6)
                temp_dict = {'filename':filename, 'size':size, 'side':side_, 'color':typ, 'copies':quantity}
                array_html.append(temp_dict)
            template = jnj_env.get_template('emailer.html')
            msg.html = template.render(order_id=order_id, amount=amount, files=array_html)     
            mail.send(msg)
            print("to the client")

            for pth in fpath:
                if os.path.isfile(pth) and os.path.exists(pth):
                    os.remove(pth)
                    continue
                continue


        payload = request.get_json()
        print("In WebHook")
        print(payload)
        metadata = payload['data']['object']['charges']['data'][0]['metadata']
        order_id = int(metadata['order_id'])
        charge_id = payload['data']['object']['charges']['data'][0]['id']
        sig_header = request.headers.get('Stripe_Signature', None)
        # files = json.loads(metadata['files'])
        user_id = int(metadata['user_id'])
        amount = float(metadata['amount'])
        tstamp = metadata['timestamp']

        # if not sig_header:
        #     return 'No Signature Header!', 400

        # try:
        #     event = stripe.Webhook.construct_event(
        #         payload, sig_header, endpoint_secret
        #     )
        # except ValueError as e:
        #     # Invalid payload
        #     return 'Invalid payload', 400
        # except stripe.error.SignatureVerificationError as e:
        #     # Invalid signature
        #     return 'Invalid signature', 400

        if payload['type'] == 'payment_intent.succeeded':
            print("In payload Part")
            email = payload['data']['object'][
                'receipt_email']  # contains the email that will recive the recipt for the payment (users email usually)
            sqlq = "INSERT INTO payments (user_id,order_id,amount, charged_id, is_successful) VALUES (%s,%s,%s,%s,%s)"
            insert_data = (user_id, order_id, amount, charge_id, 1)
            cur = mysql.connection.cursor()
            cur.execute(sqlq, insert_data)
            mysql.connection.commit()

            ftch = "SELECT sides, size, type, files from orders WHERE order_id = %s"
            cur.execute(ftch, (order_id,))
            res = cur.fetchone()
            cur.close()
            sides = res[0]
            psize = res[1]+"_"+res[2]
            files = json.loads(res[3])
            threading.Thread(target=send_attachment, args=(order_id, files, psize, sides, amount, email, tstamp)).start()

            return {"message":"OK"},200
        else:
            print("In Else Part")
            return 'Unexpected event type', 400
    except Exception as e:
        print(e)
        return '', 500






@app.route('/user', methods=['GET'])
def user():
    return "OK", 200


@app.route('/upload-to-cart', methods=['POST'])
def upload_to_cart():
    # json_data = request.get_json()
    user_id = request.form.get('user_id')
    files = request.files.getlist('files[]')
    size, typ = request.form.get('pageFormat').split('_')
    side = request.form.get('docFormat')

    if side.lower() == "double side": side = "Double-Side"
    else: side = "Single-Side"
    tstamp = request.form.get('timestamp')
    server_stamp = str(time.time())
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id), str(tstamp))

    if not os.path.exists(file_path):
        try:
            os.makedirs(file_path, 0o700)
        except OSError as e:
            if e.errno != errno.EEXIST:
                print(e)
                pass

    if False in [allowed_file(file.filename) for file in files]:
        return jsonify({"message": "check your file type", "allowed": list(ALLOWED_EXTENSIONS)}), 422

    for file in files:
        print(">}>}" * 20, file)
        mimet =""
        if file.mimetype == "application/pdf":
            mimet = "pdf"
        if file.mimetype in MIME:
            mimet = 'doc'
        if file.mimetype in ("image/jpeg", "image/jpg", "image/png"):
            mimet ="image"
        filename = str(user_id)+"_"+mimet+"_"+size + "_" + typ + "_" + side + "_" + server_stamp + "_" + secure_filename(file.filename)
        print(filename)
        npath = os.path.join(file_path, filename)
        file.save(npath)

    return jsonify({"Message": "Your files have been successfully uploaded"}), 200


@app.route('/fetch-user-files', methods=["POST"])
def fetch_user_files():
    json_data = request.get_json()
    user_id = json_data.get('user_id', 0)
    tstamp = json_data.get('timestamp', 0)
    if not user_id or not tstamp:
        return jsonify({"message":"provide user_id and timestamp properly"}), 402
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], str(user_id), str(tstamp))
    list_files = os.listdir(file_path)
    file_res = []
    for file in list_files:
        uid,mimt,size,typ,page_format,dstamp,filename = file.split('_',6)
        dict_file = {
            "size": size,
            "type": typ,
            "page_format": page_format,
            "filename": filename,
            "server_file_name": file
        }
        file_res.append(dict_file)
    return jsonify({"files": file_res}), 200


def decide_key(typ, size):
    if typ.lower() == "color" and size == "A3":
        print("IN 1") 
        return "A3_C"
    if typ.lower() == "color" and size == "A4":
        print("IN 2") 
        return "A4_C"
    if typ.lower() == "bw" and size == "A3": 
        print("IN 3") 
        return "A3_BW"
    if typ.lower() == "bw" and size == "A4": 
        return "A4_BW"


@app.route('/calcuate-final-cart', methods=["POST"])
def calculate_cart():
    num_dict = {"numbers":[], "Total_Cost":0, "A3_BW":0.00,"A3_C":0.00, "A4_BW":0.00, "A4_C":0.00}
    total_pages = 0
    json_data = request.get_json()
    user_id = json_data.get('user_id', 0)
    tstamp = json_data.get('timestamp', 0)
    files: list = json_data.get("files", [])
    if not user_id or not tstamp:
        return jsonify({"message":"user id and timestamp is missing in the request body"}), 402

    if not files:
        return jsonify({"message":"There are no files in request body"}), 402
    base_path = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id), str(tstamp))
    for file in files:
        file_pages = 0
        file_path = os.path.join(base_path, file['file'])
        quantity = int(file['quantity'])
        uid, mimet, size, typ, side, dstamp, filename = file['file'].split('_', 6)
        key = decide_key(typ, size)
        print("SIZE TYPE", typ, size)
        print("KEY==============>",key)

        if mimet == 'pdf':
            with open(file_path, 'rb') as fpath:
                read_pdf = pypdf.PdfFileReader(fpath, strict=False)
                file_pages = read_pdf.getNumPages()
                # num_dict['numbers'].append({"filename": filename, 'pages': num_pages})
                print("NUM DICT +++", num_dict)
                total_pages += file_pages*quantity
                num_dict[key] += file_pages*quantity
        if mimet == 'image':
            if 'Total_Images' in num_dict.keys():
                num_dict['Total_Images'] += 1
            else:
                num_dict['Total_Images'] = 1
            file_pages = 1
            # num_dict['numbers'].append({"filename": filename, 'pages': 1})
            total_pages += 1 * quantity
            num_dict[key] += file_pages*quantity
        if mimet == 'doc':
            output = subprocess.run(
                ["libreoffice", '--headless', '--convert-to', 'pdf', file_path, '--outdir', base_path])
            print(output)
            
            new_var = file['file']
            new_dest = os.path.splitext(base_path + f'/{new_var}')[0] + ".pdf"
            with open(new_dest, 'rb') as fpath:
                read_pdf = pypdf.PdfFileReader(fpath)
                file_pages = read_pdf.getNumPages()
                # num_dict['numbers'].append({"filename": filename, 'pages': num_pages})
                print(file_pages)
                total_pages += file_pages * quantity
                num_dict[key] += file_pages*quantity
            print("On Going")

        cost = 0
        print("In price Calc")
        if size == "A4" and typ.lower() == 'color':
            cost += (round(A4_C(file_pages),2)) * quantity
            print(cost)
        if size == "A4" and typ.lower() == 'bw':
            cost += (round(A4_BC(file_pages),2)) * quantity
            print(cost)
        if size == "A3" and typ.lower() == 'color':
            cost += (round(A3_C(file_pages),2)) * quantity
            print(cost)
        if size == "A3" and typ.lower() == 'bw':
            cost += (round(A3_BC(file_pages),2)) * quantity
            print(cost)
        num_dict['numbers'].append({"filename": filename, 'pages': file_pages, "quantity":quantity,"cost":cost})
        # num_dict["Total_Cost"] += cost
    
    print(num_dict)
    # a3_bw = num_dict['A3_BW']
    # a4_bw = num_dict['A4_BW']
    # a3_c = num_dict['A3_C']
    # a4_bw = num_dict['A4_BW']

    # if num_dict['A3']
    if num_dict["A3_BW"] == 0 and num_dict['A4_BW'] == 0 and num_dict["A4_C"] == 0 and num_dict["A3_C"] > 0:
        num_dict['Total_Cost'] =  A3_C(num_dict['A3_C'])
    elif num_dict['A3_C'] == 0 and (num_dict["A3_BW"] + num_dict['A4_BW'] + num_dict["A4_C"])<4:
        num_dict['Total_Cost'] = 3
    else:
        num_dict['Total_Cost'] = round(A4_C(num_dict['A4_C']) + A4_BC(num_dict['A4_BW']) + A3_C(num_dict['A3_C']) + A3_BC(num_dict['A3_BW']),2)
    
    return num_dict

@app.route('/delete-files', methods=["POST"])
def delete_files():
    try:
        json_data = request.get_json()
        files = json_data.get('files[]', [])
        user_id = json_data.get('user_id')
        tstamp = json_data.get('timestamp')
        if not files:
            return jsonify({"message":"Send files to be deleted"}), 402
    except:
        return jsonify({"message":"User Id or Timestamp is missing"}), 402
    
    base_path = os.path.join(app.config["UPLOAD_FOLDER"], str(user_id), str(tstamp))
    for file in files:
        file_path = os.path.join(base_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
            continue
        continue
    
    return jsonify({"message":"Files successfully removed"}), 200


# def fetch_files_db(orderId):
#     sql = """Select files from orders where orde_id=%s"""
#     cur = mysql.connection.cursor()
#     cur.execute(sql, (orderId,))
#     result = cur.fetchone()
#     print(result)
#     cur.close()

# fetch_files_db(157)     

@app.route('/test-square', methods=["GET"])
def test_square():
    result = client.locations.list_locations()

    if result.is_success():
        for location in result.body['locations']:
            print(f"{location['id']}: ", end="")
            print(f"{location['name']}, ", end="")
            print(f"{location['address']['address_line_1']}, ", end="")
            print(f"{location['address']['locality']}")

    elif result.is_error():
        for error in result.errors:
            print(error['category'])
            print(error['code'])
            print(error['detail'])
    return {"result":result.body}


@app.post("/process-payment")
def create_payment(payment):
    payment = request.get_json()
    logging.info("Creating payment")
    # Charge the customer's card
    create_payment_response = client.payments.create_payment(
        body={
            "source_id": payment['token'],
            "idempotency_key": str(uuid.uuid4()),
            "amount_money": {
                "amount": payment['amount'],  # $1.00 charge
                "currency": ACCOUNT_CURRENCY,
            },
            "order_id": payment['order_id']
        }
    )

    logging.info("Payment created")
    if create_payment_response.is_success():
        return create_payment_response.body
    elif create_payment_response.is_error():
        return create_payment_response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, threaded=True)

