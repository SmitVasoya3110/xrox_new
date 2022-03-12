import time
import os
import subprocess
import json
import socket
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, decode_token
import datetime
# from flask_jwt import current_identity
from flask_cors import CORS
import magic
from flask_mysqldb import MySQL
import PyPDF2 as pypdf
from flask_mail import Mail, Message
import threading
import stripe

from flask import Flask, request, redirect, jsonify, copy_current_request_context
from werkzeug.utils import secure_filename

welcome_message = "Welcome to Online Printing. You have successfully registered with us.\nThank you..."
hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)
print(ip_address)

stripe.api_key = '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'
endpoint_secret = ''
app = Flask(__name__)
CORS(app)


app.config['SECRET_KEY'] = 'smit-->p-->this__is~secret886651234'
jwt = JWTManager(app)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'ssssmmmmiiiitttt@gmail.com'
app.config['MAIL_PASSWORD'] = 'mqlgthtejpwtrocw'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['ORDER_MAIL'] = "websdaily@gmail.com"
mail = Mail(app)

app.config['MYSQL_HOST'] = 'localhost'  # db
app.config['MYSQL_USER'] = 'root'  # root
# app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_PASSWORD'] = 'root1234'  # print1234
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


def A3_BC(num: int):
    if 1 <= num <= 3:
        cost = 3
        return cost
    if 3 < num < 30:
        cost = 4 + (num - 3) * 0.6
        return cost
    if 30 <= num < 100:
        cost = (29 * 0.6) + (num - 29) * 0.4
        return cost
    if num >= 100:
        cost = (99 * 0.4) + (num - 99) * 0.2
        return cost


def A4_C(num: int):
    if 1 <= num <= 3:
        cost = 2
        return cost
    if 3 <= num < 30:
        cost = 2 + (num - 3) * 0.8
        return cost
    if 30 <= num < 100:
        cost = (29 * 0.6) + (num - 29) * 0.6
        return cost
    if num >= 100:
        cost = (99 * 0.4) + (num - 99) * 0.4
        return cost


def A3_C(num: int):
    if num == 1:
        cost = 3
        return cost
    if 2 <= num < 30:
        cost = 3 + (num - 1) * 0.3
        return cost
    if 30 <= num < 100:
        cost = (29 * 1.6) + (num - 29) * 1.2
        return cost
    if num >= 100:
        cost = (99 * 1.2) + (num - 99) * 0.8
        return cost


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
            size, typ = json_data.get('type', ' _ ').split('_')
            files = json_data.get('files', [])
            amount = json_data.get('amount')
            sides = json_data.get('pageFormat')
        except Exception as e:
            print(e)
            return {"message": "Invalid data sent"}, 402

        print(type(json.dumps(files)))
        print("++" * 20, type(user_id), size, typ, type(files), amount)
        try:
            qry = "insert into orders (user_id, size, type, sides, files, amount) values (%s,%s,%s,%s,%s,%s)"
            values = (user_id, size, typ, sides, json.dumps(files), amount)
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
    def send_attachment(order_id: int, files: list, psize: str, side: str, amount: int, receiver: str):
        msg = Message('Order', sender=app.config['MAIL_USERNAME'], recipients=[app.config['ORDER_MAIL']])
        msg.body = f"Order has been received with <order_id:{order_id}> from <{receiver}>"
        fpath = []
        print(files)
        for file in files:
            file = secure_filename(file)
            print(file)
            nme = os.path.join(app.config['UPLOAD_FOLDER'], file)
            fpath.append(nme)
            print("Full Path.....=>", (os.path.join(app.config['UPLOAD_FOLDER'], file)))
            buf = open(nme, 'rb').read()
            print(magic.from_buffer(buf, mime=True))
            msg.attach(file, magic.from_buffer(buf, mime=True), buf)
        print(msg)
        mail.send(msg)
        msg = Message("Customer Receipt", sender=app.config['MAIL_USERNAME'], recipients=[receiver])
        main_ = "Details of the Order Placed:\n\n"
        msg.body = main_ + f"Order Id: {order_id} \n Files: {','.join(files)} \n Price: ${amount} \n Sides: {side} \n ABN: {ABN} \n Company: {COMPANY}"
        mail.send(msg)

        for pth in fpath:
            if os.path.isfile(pth) and os.path.exists(pth):
                os.remove(pth)
                continue
            continue

    json_data = request.json
    order_id = json_data.get('order_id', 0)
    user_id = json_data.get('user_id', 0)
    files = json_data.get('fileNames', [])
    amount = json_data.get('Total_Cost', 0)
    email = json_data.get('email', '')
    psize, typ = json_data.get('docFormat', ' _ ').split('_')
    sides = json_data.get('pageaFormat')
    typ = "color" if typ.lower() == "c" else "black & white"
    if order_id and files and amount and email:
        qry = "insert into payments (order_id, user_id,amount, is_successful) values (%s, %s, %s, %s)"
        cur = mysql.connection.cursor()
        cur.execute(qry, (order_id, user_id, amount, 1))
        mysql.connection.commit()
        threading.Thread(target=send_attachment, args=(order_id, files, psize, sides, amount, email)).start()
        return {"message": "OK"}, 200


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
    jsdata = request.get_json()
    print("THIS IS JSON DATA", jsdata)
    email = jsdata.get('email')
    amount = jsdata.get('amount')
    user_id = jsdata.get('user_id')
    files = jsdata.get('files')
    order_id = jsdata.get('order_id')

    if not email:
        return 'You need to send an Email!', 400

    intent = stripe.PaymentIntent.create(
        amount=int(amount*100),
        currency='aud',
        receipt_email=email,
        metadata={
            'order_id': order_id,
            'files': json.dumps(files),
            'user_id': user_id,
            'email': email,
            'amount': amount
        }
    )

    return {"client_secret": intent['client_secret']}, 200


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        @copy_current_request_context
        def send_attachment(order_id: int, files: list, psize: str, side: str, amount: float, receiver: str):
            msg = Message('Order', sender=app.config['MAIL_USERNAME'], recipients=[app.config['ORDER_MAIL']])
            msg.body = f"Order has been received with <order_id:{order_id}> from <{receiver}>"
            fpath = []
            print(files)
            for file in files:
                file = secure_filename(file)
                print(file)
                nme = os.path.join(app.config['UPLOAD_FOLDER'], file)
                fpath.append(nme)
                print("Full Path.....=>", (os.path.join(app.config['UPLOAD_FOLDER'], file)))
                buf = open(nme, 'rb').read()
                print(magic.from_buffer(buf, mime=True))
                msg.attach(file, magic.from_buffer(buf, mime=True), buf)
            print("Sending Mail")
            mail.send(msg)
            print("successful sending")
            msg = Message("Customer Receipt", sender=app.config['MAIL_USERNAME'], recipients=[receiver])
            main_ = "Details of the Order Placed:\n\n"
            msg.body = main_ + f"Order Id: {order_id} \n Files: {','.join(files)} \n Price: ${amount} \n type: {psize} \n Sides: {side} \n ABN: {ABN} \n Company: {COMPANY}"
            mail.send(msg)
            print("to the client")

            for pth in fpath:
                if os.path.isfile(pth) and os.path.exists(pth):
                    os.remove(pth)
                    continue
                continue


        payload = request.get_json()

        print(payload)
        metadata = payload['data']['object']['charges']['data'][0]['metadata']
        order_id = int(metadata['order_id'])
        charge_id = payload['data']['object']['charges']['data'][0]['id']
        sig_header = request.headers.get('Stripe_Signature', None)
        files = json.loads(metadata['files'])
        user_id = int(metadata['user_id'])
        amount = float(metadata['amount'])

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

            ftch = "SELECT sides, size, type from orders WHERE order_id = %s"
            cur.execute(ftch, (order_id,))
            res = cur.fetchone()
            cur.close()
            sides = res[0]
            psize = res[1]+"_"+res[2]
            threading.Thread(target=send_attachment, args=(order_id, files, psize, sides, amount, email)).start()

            return {"message":"OK"},200
        else:
            print("In Else Part")
            return 'Unexpected event type', 400
    except Exception as e:
        print(e)
        return '', 200


@app.post('/api/v1/files/file-cart-upload')
def cart_upload():
    @copy_current_request_context
    def travers_file(final_result: list, files: list, size: str, typ: str, side: str, dtime: str, user_id: int = None):
        num_dict = {"numbers": []}
        total_pages = 0
        print("Thread Started")
        for file in files:
            print(">}>}" * 20, file)
            print(file.mimetype)
            filename = typ + "_" + size + "_" + side + "_" + str(dtime) + "_" + secure_filename(file.filename)
            print(filename)
            if file.mimetype == "app/pdf":
                npath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(npath)
                with open(npath, 'rb') as fpath:
                    read_pdf = pypdf.PdfFileReader(fpath)
                    num_pages = read_pdf.getNumPages()
                    num_dict['numbers'].append({"filename": filename, 'pages': num_pages})
                    print("NUM DICT +++", num_dict)
                    total_pages += num_pages

            if file.mimetype == "image/jpeg" or file.mimetype == "image/png" or file.mimetype == "image/jpg":
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                if 'Total_Images' in num_dict.keys():
                    num_dict['Total_Images'] += 1
                else:
                    num_dict['Total_Images'] = 1
                num_dict['numbers'].append({"filename": filename, 'pages': 1})
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
            num_dict['Total_cost'] = A4_C(total_pages)
        if size == "A4" and typ.lower() == 'bw':
            num_dict['Total_cost'] = total_pages
        if size == "A3" and typ.lower() == 'color':
            num_dict['Total_cost'] = A3_C(total_pages)
        if size == "A3" and typ.lower() == 'bw':
            num_dict['Total_cost'] = A3_BC(total_pages)
        num_dict['page_format'] = side
        print(num_dict)
        final_result.append(num_dict)

    metadata = json.loads(request.form.get('metadata'))
    meta_data = metadata['metadata']
    # user_id = meta_data['user_id']
    current_tp = str(time.time())
    traverse_files = time.perf_counter()

    thread_list = []
    final_result = []
    for data in meta_data:
        num_dict = {"numbers": []}
        size, typ = request.form[data['docFormat']].split('_')
        # TODO: check for every attributes and vaule is not null
        # TODO: fetch files and check for extension
        # TODO: Travers files and calculate page numbers and do ohter perfomantion -- done
        # TODO: calculate price and numbers and file details for current iteration and append it to global response
        files = request.files.getlist(data["files"])
        side = request.form.get(data['sides'], "")
        check_extension_start = time.perf_counter()

        if False in [allowed_file(file.filename) for file in files]:
            return jsonify({"message": "check your file type", "allowed": list(ALLOWED_EXTENSIONS)}), 422
        print("Checking file extension as Taken time:", time.perf_counter() - check_extension_start)

        th = threading.Thread(target=travers_file, args=(final_result, files, size, typ, side, current_tp))
        th.start()
        thread_list.append(th)
    print("Thread started")
    for thread in thread_list:
        thread.join()
    end_traversal = time.perf_counter()
    print(final_result)
    print("Estimated Time Taken By File Traversal and Page Calculation is: ", end_traversal - traverse_files)
    return {"traversl_time": (end_traversal - traverse_files), "final_result": final_result}



@app.route('/user', methods=['GET'])
def user():
    return "OK", 200


@app.route('/upload-to-cart', methods=['POST'])
def upload_to_cart():
    # json_data = request.get_json()
    user_id = request.form.get('user_id')
    files = request.files.getlist('files[]')
    typ, size = request.form.get('pageFormat').split('_')
    side = request.form.get('docFormat')
    tstamp = request.form.get('timestamp')
    server_stamp = str(time.time())
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id), str(tstamp))

    if not os.path.isdir(file_path):
        os.mkdir(file_path)

    if False in [allowed_file(file.filename) for file in files]:
        return jsonify({"message": "check your file type", "allowed": list(ALLOWED_EXTENSIONS)}), 422

    for file in files:
        print(">}>}" * 20, file)
        print(file.mimetype)
        filename = str(user_id)+"_"+typ + "_" + size + "_" + side + "_" + server_stamp + "_" + secure_filename(file.filename)
        print(filename)
        npath = os.path.join(file_path, filename)
        file.save(npath)

    return jsonify({"Message": "Your files have been successfully uploaded"}), 200


@app.route('/fetch-user-files', methods=["GET"])
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
        uid,size,typ,page_format,dstamp,filename = file.rsplit('_',5)
        dict_file = {
            "size": size,
            "type": typ,
            "page_format": page_format,
            "filename": filename,
            "server_file_name": file
        }
        file_res.append(dict_file)
    return jsonify({"files": file_res}), 200
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True, threaded=True)

