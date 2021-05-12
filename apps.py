import os,hashlib
from flask import Flask,render_template,request,session,json,redirect,url_for
from flask_mysqldb import MySQL
import MySQLdb.cursors
import urllib.request
from werkzeug.utils import secure_filename
import re
from sendemail import sendmail
import smtplib
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = 'a'
app.config['MYSQL_HOST'] = 'remotemysql.com'
app.config['MYSQL_USER'] = '...'
app.config['MYSQL_PASSWORD'] = '...'
app.config['MYSQL_DB'] = '...'
mysql = MySQL(app)
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = set(['jpeg', 'jpg', 'png', 'gif'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


@app.route('/register',methods =['GET', 'POST'])
def Registration():
    msg = ''
    if request.method =="POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM tableone WHERE name = % s', (name, ))
        account = cursor.fetchone()
        print(account)
        if account:
            msg = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', name):
            msg = 'name must contain only characters and numbers !'
        else:
            cursor.execute('INSERT INTO tableone VALUES(NULL,% s,% s,% s)',(name,email,hashlib.md5(password.encode()).hexdigest(),))
            mysql.connection.commit()
            msg = "you have sucessfully got registered"
            TEXT = "Hello "+name + ",\n\n"+ """Thanks for applying registring at smartinterns """
            message  = 'Subject: {}\n\n{}'.format("smartinterns Carrers", TEXT)
            sendmail(TEXT,email)
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template("Registration.html",msg = msg)


@app.route('/login',methods=['GET', 'POST'])
def Login():
    global UserId
    msg = ''
    if request.method == 'POST' and 'name' in request.form and 'password' in request.form:
        name = request.form['name']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM tableone WHERE name = %s AND password = %s', (name, hashlib.md5(password.encode()).hexdigest(),))
        account = cursor.fetchone()
        print (account)
        if account:
            session['loggedin'] = True
            session['UserId'] = account["UserId"]
            id = account["UserId"]
            session['name'] = account["name"]
            msg = 'Logged in successfully!'
        else:
            msg = 'Incorrect username/password!'
    return render_template('Login.html', msg=msg)

def getLoginDetails():
    cursor = mysql.connection.cursor()
    if 'name' not in session:
        loggedin = False
        email = ''
    else:
        loggedin = True
    return (loggedin)


#to contact the admin
@app.route('/contact',methods=['GET','POST'])
def contact():
    msg=' '
    if request.method =="POST":
        name = request.form['name']
        email = request.form['email']
        subject= request.form['subject']
        message = request.form['message']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM contact WHERE id = % s', (session['UserId'],))
        account = cursor.fetchone()
        print(account)
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO contact VALUES (% s, % s, % s, % s,% s)', (session['UserId'],name, email,subject,message))
        mysql.connection.commit()
        msg = 'You have successfully sent the message to admin !'
        session['loggedin'] = True
        TEXT = "from"+email+"Message:"+message+"Subject:"+subject+" "
        sendmail(TEXT,"kavyapadala259@gmail.com")
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('contact.html', msg = msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('UserId', None)
    session.pop('name', None)
    return render_template('home.html')

def allowed_file(filename):
    return '.' in filename and \
              filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

#this is to add the product into the product list
@app.route('/AddProduct',methods=["GET", "POST"])
def add_product():
    if request.method =="POST":
        name=request.form['name']
        price=request.form['price']
        description = request.form['description']
        categoryId = int(request.form['category'])
        image = request.files['image']
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            imagename = filename
        print(filename)#img2.png
        cursor = mysql.connection.cursor()
        cursor.execute('INSERT INTO products VALUES(NULL,% s,% s,% s,% s,% s)',(categoryId,name,price,description,imagename))
        mysql.connection.commit()
    return render_template('Shopping.html')


#Homepage
@app.route('/')
def home():
    loggedin = getLoginDetails()
    return render_template('home.html',loggedin=loggedin)

#Page to show the category Books
@app.route('/category/<int:categoryId>',methods=['GET','POST'])
def category(categoryId):
    loggedin = getLoginDetails()
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT products.*, categories.* FROM  products, categories WHERE products.categoryId = categories.categoryId AND categories.categoryId = % s', (categoryId, ))
    data=cursor.fetchall()
    print(data)
    return render_template('category.html', data=data,loggedin=loggedin)


#this is the all productspage
@app.route('/allproducts')
def allproducts():
    loggedin = getLoginDetails()
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT * FROM products ORDER BY price')
    data = cursor.fetchall()
    return render_template('allproducts.html',data=data,loggedin=loggedin)


#to show product details: each product
@app.route('/product_detail/<int:ProductId>',methods=["GET", "POST"])
def product_detail(ProductId):
    loggedin = getLoginDetails()
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT *FROM products WHERE ProductId = % s',(ProductId,))#get the product Id
    data=cursor.fetchone()
    return render_template('product_detail.html',data=data,loggedin=loggedin)

#to add the items in cart
@app.route('/AddCart',methods=["GET", "POST"])
def AddCart():
    loggedin = getLoginDetails()
    msg=' '
    if 'name' not in session:
        return redirect(url_for('Login'))
    else:
        ProductId = request.form.get('ProductId')
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT UserId FROM tableone WHERE name = %s",(session['name'],))
        UserId = cursor.fetchone()[0]
        cursor.execute("INSERT INTO cart (UserId, ProductId) VALUES (%s, %s)", (UserId, ProductId))
        mysql.connection.commit()
        msg = "Added successfully"
        return render_template("cart.html",loggedin=loggedin)

#to display cart
@app.route("/cart", methods=["GET", "POST"])
def cart():
    loggedin = getLoginDetails()
    if 'name' not in session:
        return redirect(url_for('Login'))
    name = session['name']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT UserId FROM tableone WHERE  name= %s", (name, ))
    UserId = cursor.fetchone()[0]
    cursor.execute("SELECT products.ProductId, products.name, products.price, products.image FROM products, cart WHERE products.ProductId = cart.ProductId AND cart.UserId = %s", (UserId, ))
    products = cursor.fetchall()
    print(products)
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template("cart.html", products = products, totalPrice=totalPrice,loggedin=loggedin)

#to remove item from cart
@app.route('/removeItem/<int:ProductId>',methods=["GET", "POST"])
def removeItem(ProductId):
    loggedin = getLoginDetails()
    if 'name' not in session:
        return redirect(url_for('Login'))
    name = session['name']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT UserId FROM tableone WHERE name = %s", (name, ))
    UserId = cursor.fetchone()[0]
    cursor.execute("DELETE FROM cart WHERE UserId = % s AND ProductId = % s", (UserId, ProductId))
    mysql.connection.commit()
    msg = "removed successfully"
    return render_template("cart.html",msg=msg,loggedin=loggedin)


#ADD to  buy table and delete in cart
@app.route("/buy",methods=["GET", "POST"])
def buy():
    loggedin = getLoginDetails()
    if 'name' not in session:
       return redirect(url_for('Login'))
    name = session['name']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT UserId FROM tableone WHERE  name= %s", (name, ))
    UserId = cursor.fetchone()[0]
    ProductId = request.form.get('ProductId')
    cursor.execute("INSERT into buy(userId,ProductId) values (% s, % s)",(UserId,ProductId))
    mysql.connection.commit()
    cursor.execute("SELECT products.ProductId, products.name, products.price, products.image FROM products, buy WHERE products.ProductId = buy.ProductId AND buy.userId = %s", (UserId,))
    products = cursor.fetchall()
    cursor.execute("DELETE FROM cart WHERE UserId='%s' ",(UserId,))
    mysql.connection.commit()
    cursor.execute("SELECT email FROM tableone WHERE  name= %s", (name, ))
    email = cursor.fetchone()[0]
    print(email)
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    TEXT = "thank you for buying "+name + ",\n\n"+ " "
    sendmail(TEXT,email)
    return render_template("history.html",loggedin=loggedin)


#peviously purschased products
@app.route('/history')
def history():
    loggedin = getLoginDetails()
    if 'name' not in session:
       return redirect(url_for('Login'))
    name = session['name']
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT UserId FROM tableone WHERE  name= %s", (name, ))
    UserId = cursor.fetchone()[0]
    cursor.execute("SELECT products.ProductId, products.name, products.price, products.image FROM products, buy WHERE products.ProductId = buy.ProductId AND buy.userId = %s", (UserId,))
    products = cursor.fetchall()
    totalPrice = 0
    for row in products:
        totalPrice += row[2]
    return render_template('history.html',products=products,totalPrice=totalPrice,loggedin=loggedin)



if __name__ == '__main__':
    app.run(host='0.0.0.0',debug = True,port = 8080)
