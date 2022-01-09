from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps


# Login Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Please log in first!", "danger")
            return redirect(url_for('login'))
    return decorated_function

# Form of Registration
class RegistrationForm(Form):
    name = StringField("First Name:", validators=[validators.Length(min=4, max=25), validators.DataRequired(message="Must be filled!")])
    lastname = StringField("Last Name:", validators=[validators.Length(min=4, max=25), validators.DataRequired(message="Must be filled!")])
    username = StringField("Username:", validators=[validators.Length(min=5, max=25), validators.DataRequired(message="Must be filled!")])
    email =  StringField("Email:", validators=[validators.Email(message="Invalid email!"),validators.DataRequired(message="Must be filled!")])
    password = PasswordField("Password:", validators=[validators.DataRequired(message="Must be filled!"), validators.EqualTo(fieldname="repassword", message="Mismatched passwords!")])
    repassword = PasswordField("Repeat Password:", validators=[validators.Length(min=8,max=16)])

# Form of Login
class LoginForm(Form):
    username = StringField("Username:", validators=[validators.InputRequired()])
    password = PasswordField("Password:", validators=[validators.InputRequired()])

# Form of Stories
class StoryForm(Form):
    story_name = StringField("Story Name:", validators=[validators.DataRequired(), validators.Length(min=5, max=100)])
    famous_name = StringField("Famous Name:", validators=[validators.DataRequired(), validators.Length(min=3)])
    programme_name = StringField("Show Name:", validators=[validators.DataRequired()])
    url = StringField("URL:", validators=[validators.DataRequired(), validators.URL(message="Invalid URL!")])


app = Flask(__name__)
app.secret_key = "fob"
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "FOB"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/profile")
@login_required
def profile():
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM stories WHERE username = %s", (session["username"],))
    if result > 0:
        stories = cursor.fetchall()
        return render_template("profile.html", stories = stories)
    else:
        return render_template("profile.html")

@app.route("/stories")
def stories():
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM stories")
    if result > 0:
        stories = cursor.fetchall()
        return render_template("stories.html", stories=stories)
    else:
        return render_template("stories.html")

# Registration
@app.route("/register", methods=["GET","POST"])
def register():
    form = RegistrationForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        lastname = form.lastname.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        query = "INSERT INTO users (first_name,last_name,username,email,password) VALUES (%s,%s,%s,%s,%s)"
        cursor.execute(query, (name, lastname, username, email, password))
        mysql.connection.commit()
        cursor.close()
        flash("You have successfully registered!","success")
        return redirect(url_for("login"))
    else:
        return render_template("register.html", form=form)
# Login Page
@app.route("/login", methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        cursor = mysql.connection.cursor()
        login_query = "SELECT username, password FROM users WHERE username = %s"
        result = cursor.execute(login_query, (username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered, real_password):
                flash(f"You have successfully logged in! WELCOME {username} :)", "success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Invalid password or username!", "danger")
                return redirect(url_for("login"))
        else:
            flash("Invalid password or username!", "danger")
            return redirect(url_for("login"))
    return render_template("login.html", form=form)       

# Logout Page
@app.route("/logout")
def logout():
    session.clear()
    flash("You have successfully logged out!", "info")
    return redirect(url_for("index"))

# Insert Story Page
@app.route("/addstory", methods=["GET","POST"])
def addstory():
    form = StoryForm(request.form)
    if request.method == "POST" and form.validate:
        story_name = form.story_name.data
        famous_name = form.famous_name.data
        programme_name = form.programme_name.data
        url = form.url.data
        
        cursor = mysql.connection.cursor()
        query = "INSERT INTO stories (story_name,famous_name,programme_name,url, username) VALUES (%s,%s,%s,%s,%s)"
        cursor.execute(query, (story_name, famous_name, programme_name, url, session["username"]))
        mysql.connection.commit()
        cursor.close()
        flash("Story has been successfully inserted!", "success")
        return redirect(url_for("profile"))
    return render_template("add_story.html", form=form)

# Story Details 
@app.route("/story/<string:ID>")
def storydetails(ID):
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM stories WHERE ID = %s", (ID,))
    if result > 0:
        story = cursor.fetchone()
        return render_template("single_story.html", story=story)
    else:
        return render_template("single_story.html")

# Delete Story
@app.route("/delete/<string:ID>")
@login_required
def deletestory(ID):
    cursor = mysql.connection.cursor()
    result = cursor.execute("SELECT * FROM stories WHERE username = %s AND ID = %s", (session["username"], ID))
    if result > 0:
        cursor.execute("DELETE FROM stories WHERE ID = %s", (ID,))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for("profile"))
    else:
        flash("There is no such story, or this story is not accessible to delete!", "warning")
        return redirect(url_for("index"))

# Update Story
@app.route("/update/<string:ID>", methods=["GET", "POST"])
@login_required
def updatestory(ID):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        result = cursor.execute("SELECT * FROM stories WHERE ID = %s AND username = %s", (ID, session["username"]))
        if result > 0:
            story = cursor.fetchone()
            form = StoryForm()
            form.story_name.data = story["story_name"]
            form.famous_name.data = story["famous_name"]
            form.programme_name.data = story["programme_name"]
            form.url.data = story["url"]
            return render_template("update.html", form = form)
        else:
            flash("There is no such story, or this article is not updatable!", "warning")
            return redirect(url_for("index"))
    else:
        form = StoryForm(request.form)
        newTitle = form.story_name.data
        newFamousName = form.famous_name.data
        newShowName = form.programme_name.data
        newURL = form.url.data
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE stories SET story_name = %s, famous_name = %s, programme_name = %s, url = %s WHERE ID = %s", (newTitle, newFamousName, newShowName, newURL, ID))
        mysql.connection.commit()
        cursor.close()
        flash("Story has been successfully updated!", "success")
        return redirect(url_for("profile"))

# Search Page
@app.route("/search", methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        cursor = mysql.connection.cursor()
        keyword = request.form.get("keyword")
        query = "SELECT * FROM stories WHERE story_name LIKE '%" + keyword + "%' or famous_name LIKE '%" + keyword + "%' or programme_name LIKE '%" + keyword + "%'"
        result = cursor.execute(query)
        if result > 0:
            stories = cursor.fetchall()
            return render_template("stories.html", stories = stories)
        else:
            flash("There is no story suitable for such a keyword!", "warning")
            return redirect(url_for("stories"))

if __name__ == "__main__":
    app.run(debug=True)