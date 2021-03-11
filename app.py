from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, RadioField
from passlib.hash import sha256_crypt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
import MySQLdb

app = Flask(__name__)
app.debug = True

# MYSQL configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234'
app.config['MYSQL_DB'] = 'db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

userid = 0

# Initialize db
mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/forgotPass.html")
def forgotPass():
    return render_template("forgotPass.html")

# Dev Functions
@app.route("/devSignUp.html", methods=['GET', 'POST'])
def devSignUp():
    if session.get("logged_in") == True:
        flash("Logged in currently, logout first please")
        return redirect(url_for("index"))
    else:
        class RegisterForm(Form):
            name = StringField('Name', [validators.Length(min=1, max=50)])
            username = StringField('Username', [validators.Length(min=4, max=25)])
            email = StringField('Email', [validators.Length(min=6, max=50)])
            password = PasswordField('Password', [validators.DataRequired(),
                        validators.EqualTo('confirm', message="Passwords do not match!")])
            confirm = PasswordField('Confirm Password')

        form = RegisterForm(request.form)
        if request.method == 'POST':
            name = form.name.data
            email = form.email.data
            password = form.password.data

            # Create cursor
            cur = mysql.connection.cursor()

            try:
                # Create new User
                cur.execute("INSERT INTO user(name, email, password) VALUES(%s, %s, %s)", (name, email, password))
                mysql.connection.commit()
                # Get User Id
                cur.execute("SELECT user_id FROM user WHERE email='{0}'".format(email));
                mysql.connection.commit();
                userid = cur.fetchall()[0]['user_id']
                # Create new Developer
                cur.execute("INSERT INTO developer (developer_id) VALUES(%s)", [userid])
                mysql.connection.commit()
                # Close connection
                cur.close()
                flash("You are now registered successfully", 'success')
                return redirect(url_for('index'))

            except MySQLdb.IntegrityError:
                app.logger.info('Email exists already')
                flash("Email exists already", "warning")
                return render_template("devSignUp.html", form = form)

    return render_template("devSignUp.html", form = form)


@app.route("/postQuestion.html" , methods=['Get', 'POST'])
def postQuestion():
    class makeQuestion(Form):
        question = TextAreaField("Question: ",[validators.Required("Please enter Question")])
        answer = TextAreaField("Answer: ",[validators.Required("Please Answer")])
        dept_name = TextAreaField("Department Name: ",[validators.Required("dept_name")])
        difficulty = RadioField("Difficulty", choices=[("e" , "easy") , ('m' , 'medium') , ('h', 'hard')])
    form = makeQuestion(request.form)
    if request.method == 'POST':
        # print("in post")
        # Create Cursor
        cur = mysql.connection.cursor()

        question = form.question.data

        answer = form.answer.data
        difficulty = form.difficulty.data
        dept_name = form.dept_name.data
        test_case = ""
        approval = 0

        cur.execute("INSERT INTO question(dept_name, description, test_case, difficulty, approval)" +
                    "VALUES ('{0}', '{1}', '{2}', '{3}', 0)".format(dept_name, question, test_case, difficulty))
        mysql.connection.commit()

        cur.execute("SELECT question_id FROM question")
        mysql.connection.commit()
        temp = cur.fetchall()

        cur.execute("INSERT INTO discussion(discussion_id, question_id) Values(%s, %s)",
                        [temp[len(temp)-1]['question_id'], temp[len(temp)-1]['question_id']])
        mysql.connection.commit()

        # Get response
        queryResponse = cur.fetchall();

        cur.close()
        return redirect(url_for("devHome"))

    return render_template("postQuestion.html", form = form)

@app.route("/devSignIn.html", methods=['GET', 'POST'])
def devSignIn():
    if session.get("logged_in") == True:
        if session.get("email") == "admin":
            flash("Admin is logged in currently!", "warning")
            return redirect(url_for("index"))
        else:
            flash("Redirecting to home")
            return redirect(url_for("devHome"))
    elif request.method == 'POST':
        email = request.form['email']
        password_candidate = request.form['password']

        # Create Cursor
        cur = mysql.connection.cursor()

        result = cur.execute("SELECT * FROM user WHERE email = %s", [email])
        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare the passwords
            if password == password_candidate:
                app.logger.info('PASSWORD MATCHED')
                session['logged_in'] = True
                session['email'] = email
                session['type'] = 'dev'
                flash("You are now logged in", "success")
                return redirect(url_for('devHome'))
            else:
                app.logger.info('PASSWORD NOT MATCHED')
                error = 'INVALID LOGIN'
                flash("INVALID LOGIN! Check Email/Password!", "warning")
                return render_template("devSignIn.html", error = error)

            # Close cursor
            cur.close()
        else:
            error = 'USER NOT FOUND'
            app.logger.info('USER NOT FOUND')
            flash("USER NOT FOUND", "warning")
            return render_template("devSignIn.html", error = error)
    return render_template("devSignIn.html")

@app.route("/logout.html")
def logout():
    session.clear()
    flash("You are logged out!", "success")
    return redirect(url_for("index"))

@app.route("/devHome.html")
def devHome():
    return render_template("devHome.html")

@app.route("/searchQuestion.html", methods=['Get', 'Post'])
def searchQuestion():

    class SearchForm(Form):
        input = StringField("Input" ,[validators.Required("Please enter Question")] )

    form = SearchForm(request.form)

    if (request.method == "POST"):

        input = form.input.data;

        # Create cursor
        cur = mysql.connection.cursor()

        # Get All Questions
        cur.execute("SELECT * from question where dept_name='{0}';".format(input));
        mysql.connection.commit()

        # Return the questions to the next page
        queryResponse = cur.fetchall();
        # print (queryResponse);
        import json

        return searchResult(queryResponse , input)
    return render_template("searchQuestion.html" , form=form)

def searchResult(obj , topic):

    return render_template("searchResult.html", questions=obj , topic=topic)


@app.route("/questionDetails/<string:id>/", methods = ["POST", "GET"])
def questionDetails(id):
    # Create cursor
    cur = mysql.connection.cursor()

    cur.execute("SELECT description FROM question WHERE question_id = %s", [id])
    # print("in questio details: ", id)
    mysql.connection.commit()
    question = cur.fetchone()

    cur.close()

    return render_template("questionDetails.html", id = id, question = question)

@app.route("/postComment.html", methods = ["POST", "GET"])
def postComment():
    class makeComment(Form):
        comment = TextAreaField("Comment: ",[validators.Required("Please enter Comment")])
    form = makeComment(request.form)
    discussion_id = request.args.get('discussion_id')
    if request.method == 'POST':
        # Create Cursor
        cur = mysql.connection.cursor()
        comment = form.comment.data
        print(discussion_id)
        print(comment)
        cur.execute("INSERT INTO comment(discussion_id, description) Values(%s, %s)", [discussion_id, comment])
        mysql.connection.commit()
        cur.close()
        print(discussion_id)
        return redirect(url_for("discussion", id = discussion_id))
        # return redirect(url_for("discussion", id = discussion_id))

    return render_template("postComment.html",  form = form)

@app.route("/discussion/<string:id>/", methods = ["POST", "GET"])
def discussion(id):
    # print(id)
    if request.method == "POST":
        print("in discussion:", id)
        return redirect(url_for("postComment", discussion_id = id))

    # Create cursor
    cur = mysql.connection.cursor()

    # try:
    print(id)
    cur.execute("INSERT INTO discussion(question_id) Values(%s)", [id])
    mysql.connection.commit()
    # except:
    # Create new User
    cur.execute("SELECT discussion_id FROM discussion WHERE question_id = %s AND discussion_id = %s", [id, id])
    mysql.connection.commit()

    discuss = cur.fetchall()[0]['discussion_id']
    # print("discuss ", discuss)
    cur.execute("SELECT * FROM comment WHERE discussion_id = %s", [discuss])
    mysql.connection.commit()

    comments = cur.fetchall()

    cur.close()

    return render_template("discussion.html", comments = comments, id = id)

@app.route("/answerToQuestion/<string:id>/")
def answerToQuestion(id):
    # Create cursor
    cur = mysql.connection.cursor()

    cur.execute("SELECT description FROM question WHERE question_id = %s", [id])
    mysql.connection.commit()
    question = cur.fetchone()
    cur.close()

    return render_template("answerToQuestion.html", id = id, question = question)

@app.route("/track/<string:id>.html/", methods = ['GET', 'POST'])
def track(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Create new User
    result = cur.execute("SELECT question_id FROM trackquestions WHERE track_id = %s", [id])
    mysql.connection.commit()

    cur.execute("SELECT question_id FROM trackquestions WHERE track_id = %s", [id])
    mysql.connection.commit()

    track = cur.fetchall()
    questions = list()
    for i in track:
        cur.execute("SELECT * FROM question WHERE question_id = %s", [i["question_id"]])
        mysql.connection.commit()
        temp = cur.fetchone()
        questions.append(temp)

    cur.close()

    if request.method == "POST":
        print("hello")
        return redirect(url_for('leaderboard', idi=[id]))


    # print("in track: ", id)
    return render_template("Track.html", questions = questions, id = id)

@app.route("/joinTrack.html", methods = ['GET', 'POST'])
def joinTrack():

    class SelectTrackForm(Form):
        id = StringField('id', [validators.Length(min=1, max=50)])
    form = SelectTrackForm(request.form)

    # Create cursor
    cur = mysql.connection.cursor()

    # Get all the tracks
    result = cur.execute("SELECT * FROM track")
    mysql.connection.commit()
    tracks = cur.fetchall();

    if result > 0:
        if request.method == "POST":
            trackId = form.id.data
            cur.execute("SELECT user_id FROM user WHERE email = %s", [session["email"]])
            mysql.connection.commit()
            userId = cur.fetchone()
            try:
                cur.execute("INSERT INTO trackdeveloper(developer_id, track_id) VALUES(%s, %s)", (userId['user_id'], trackId))
                mysql.connection.commit()
            except:
                flash("Track already added! Redirecting to it", "success")

            return redirect(url_for("track", id = trackId))

        return render_template("joinTrack.html", tracks = tracks);
    else:
        error = 'No Tracks available'
        flash('No Tracks available')
        app.logger.info('No Tracks available')
        return render_template("joinTrack.html", error = error)

@app.route("/leaderboard.html", methods = ['GET', 'POST'])
def leaderboard():
    trackId = request.args.get('idi')
    print(trackId)
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM leaderboard,score,developer,user WHERE track_id = %s ORDER BY score ASC", [trackId])
    mysql.connection.commit()
    leader = cur.fetchall()
    return render_template("leaderboard.html", leader=leader)


@app.route("/acceptInter.html", methods=['GET', 'POST'] )
def acceptInter():
    # Create cursor
    cur = mysql.connection.cursor()

    class makeQuestion(Form):
        compRepId = StringField('comprepId', [validators.Length(min=1, max=50)])
        devId = StringField('devId', [validators.Length(min=1, max=50)])
    form = makeQuestion(request.form);

    cur = mysql.connection.cursor()
    cur.execute("Select user_id from user where email='{0}'".format(session['email']));
    mysql.connection.commit();
    userid = cur.fetchall()[0]['user_id']
    cur.execute("SELECT * FROM job,comprep WHERE job.compRep_id = comprep.compRep_id AND job.developer_id='{0}'".format(userid));
    mysql.connection.commit();
    aInter = cur.fetchall()

    if (request.method == "POST"):
        compRepId = form.compRepId.data
        devId = form.devId.data
        return redirect(url_for('jobDetails', comprepid=compRepId, devid = devId))

    return render_template("acceptInter.html",aInter = aInter);

@app.route("/jobDetails.html/", methods=['GET', 'POST'])
def jobDetails():
    cur = mysql.connection.cursor()
    comprep = request.args.get('comprepid')
    devid = request.args.get('devid')
    cur.execute("SELECT * FROM job WHERE developer_id = '{0}' AND comprep_id = '{1}'".format(devid , comprep))
    mysql.connection.commit()
    description = cur.fetchone()

    if (request.method == "POST"):
        cur.execute("DELETE FROM job WHERE developer_id = '{0}' AND comprep_id = '{1}'".format(devid , comprep))
        mysql.connection.commit()
        return redirect(url_for('acceptInter'))

    return render_template("jobDetails.html", description = description)

# Company Functions
compCreatedTrackId = 0;
questionNoOfNewTrack = 0;

@app.route("/compCreateTrack.html", methods=['GET', 'POST'])
def compCreateTrack():

    global questionNoOfNewTrack
    # Create cursor
    cur = mysql.connection.cursor()

    # Create new User
    cur.execute("SELECT * FROM question")
    mysql.connection.commit()

    queryResponse = cur.fetchall();

    if len(queryResponse) == 0:
        flash ("There is not any question", "warning")
        return render_template("compCreateTrack.html", question = queryResponse)

    class CreateTrackForm(Form):
        id = StringField('id', [validators.Length(min=1, max=50)])
    form = CreateTrackForm(request.form)

    global compCreatedTrackId

    if request.method == "POST":
        id = form.id.data

        if id !='0':
            try:
                cur.execute("INSERT INTO trackquestions (question_id, track_id) VALUES(%s,%s)", [id,compCreatedTrackId]);
                mysql.connection.commit()
                questionNoOfNewTrack = questionNoOfNewTrack + 1;
            except:
                flash("Already Added to Track")
        else:
            cur.execute("UPDATE track SET no_questions = '{0}' WHERE track_id = '{1}'".format(questionNoOfNewTrack,compCreatedTrackId));
            mysql.connection.commit()
            questionNoOfNewTrack = 0;
            return redirect(url_for('compReviewTrack'))
    else:
        trackName = "Track";
        cur.execute("INSERT INTO track (track_name) VALUES(%s)", [trackName]);
        mysql.connection.commit()

        cur.execute("SELECT track_id FROM track");
        mysql.connection.commit()
        trackResult = cur.fetchall();

        compCreatedTrackId = (trackResult[len(trackResult)-1]["track_id"]);

    return render_template("compCreateTrack.html", question = queryResponse)

@app.route("/compInviteDeveloper.html",methods=['GET', 'POST'])
def compInviteDeveloper():

    track_id = request.args.get('track_id')

    # Create cursor
    cur = mysql.connection.cursor()

    # Create new User
    cur.execute("SELECT name, developer_id FROM user, developer WHERE user_id = developer_id")
    mysql.connection.commit()
    queryResponse = cur.fetchall()

    if len(queryResponse) == 0:
        flash ("There is not any developer", "warning")
        return render_template("compInviteDeveloper.html",developer = queryResponse)
    else :
        print(track_id)

    class InviteForm(Form):
        id = StringField('id', [validators.Length(min=1, max=50)])
        jobDetails = StringField('jobDetails', [validators.Length(min=1, max=50)])
        endDate = StringField('endDate', [validators.Length(min=1, max=50)])
    form = InviteForm(request.form)

    global compCreatedTrackId

    if request.method == "POST":
        id = form.id.data
        jobDetails = form.jobDetails.data
        endDate = form.endDate.data

        print(id)
        print(jobDetails)
        print(endDate)


        cur.execute("SELECT comprep_id FROM comprep, user WHERE (user.email='{0}' AND user.user_id = comprep.compRep_id)".format(session.get("email")))
        mysql.connection.commit()
        activeUID = cur.fetchall();
        print(activeUID)
        try:
            cur.execute("INSERT INTO job (developer_id, comprep_id, jobDescription, endDate) VALUES ({0}, {1}, '{2}', '{3}')".format(id,activeUID[0]["comprep_id"],jobDetails,endDate));
            mysql.connection.commit()
        except:
            flash("Already sent an invitation")



    return render_template("compInviteDeveloper.html",developer = queryResponse)

@app.route("/compHome.html")
def compHome():
    return render_template("compHome.html")

@app.route("/compSelectTrack.html",methods=['GET', 'POST'])
def compSelectTrack():

    # Create cursor
    cur = mysql.connection.cursor()

    # Create new User
    cur.execute("SELECT * FROM track")
    mysql.connection.commit()

    queryRespone = cur.fetchall();

    if len(queryRespone) == 0:
        flash ("There is not any track", "warning")
        return render_template("compSelectTrack.html", track = queryRespone)
    else :
        pass

    class SelectTrackForm(Form):
        id = StringField('id', [validators.Length(min=1, max=50)])
    form = SelectTrackForm(request.form)

    if request.method == "POST":
        id = form.id.data
        return redirect(url_for("compInviteDeveloper", track_id = id))


    return render_template("compSelectTrack.html", track = queryRespone)


compCreatedTrackId2 = 0;

@app.route("/compReviewTrack.html", methods=['GET', 'POST'])
def compReviewTrack():

    global compCreatedTrackId2

    # Create cursor
    cur = mysql.connection.cursor()
    cur.execute("SELECT track_id FROM track");
    mysql.connection.commit()
    trackResult = cur.fetchall();

    compCreatedTrackId2 = (trackResult[len(trackResult)-1]["track_id"]);
    print (compCreatedTrackId2);

    cur.execute("SELECT * FROM question,trackquestions WHERE (trackquestions.track_id='{0}'AND trackquestions.question_id = question.question_id)".format(compCreatedTrackId2));
    mysql.connection.commit()
    outputQuestions = cur.fetchall();

    #print (outputQuestions)


    if len(outputQuestions) == 0:
        flash ("There is not any question in the track", "warning")
        return render_template("compReviewTrack.html",question=outputQuestions)

    class ReviewForm(Form):
        trackName = StringField('trackName', [validators.Length(min=1, max=50)])
    form = ReviewForm(request.form)

    if request.method == "POST":

        trackName = form.trackName.data
        # print(trackName, file=sys.stderr)

        cur.execute("UPDATE track SET track_name = '{0}' WHERE track_id = '{1}'".format(trackName,compCreatedTrackId2));
        mysql.connection.commit()

        return redirect(url_for('compHome'))

    return render_template("compReviewTrack.html",question=outputQuestions)

@app.route("/comSignIn.html", methods=['GET', 'POST'])
def comSignIn():
    if session.get("logged_in") == True:
        if session.get("email") == "admin":
            flash("Admin is logged in currently!", "warning")
            return redirect(url_for("index"))
        elif session.get("type") == "dev":
            flash("Developer is logged in currently!", "warning")
            return redirect(url_for("index"))
        else:
            flash("Redirecting to home")
            return redirect(url_for("compHome"))
    elif request.method == 'POST':
        email = request.form['email']
        password_candidate = request.form['password']

        # Create Cursor
        cur = mysql.connection.cursor()

        result = cur.execute("SELECT * FROM user WHERE email = %s", [email])
        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']

            # Compare the passwords
            if password == password_candidate:
                app.logger.info('PASSWORD MATCHED')
                session['logged_in'] = True
                session['email'] = email
                session['type'] = 'company'
                flash("You are now logged in", "success")
                return redirect(url_for('compHome'))
            else:
                app.logger.info('PASSWORD NOT MATCHED')
                error = 'INVALID LOGIN'
                flash("INVALID LOGIN! Check Email/Password!", "warning")
                return render_template("comSignIn.html", error = error)

            # Close cursor
            cur.close()
        else:
            error = 'USER NOT FOUND'
            app.logger.info('USER NOT FOUND')
            flash("USER NOT FOUND", "warning")
            return render_template("comSignIn.html", error = error)


    return render_template("comSignIn.html")

@app.route("/comSignUp.html" , methods=['GET', 'POST'] )
def comSignUp():

    if session.get("logged_in") == True:
        logout()
    else:
        class RegisterForm(Form):
            companyName = StringField('Company Name', [validators.Length(min=1, max=50)])
            agentName = StringField('Agent Name', [validators.Length(min=4, max=25)])
            email = StringField('Email', [validators.Length(min=6, max=50)])
            password = PasswordField('Password', [validators.DataRequired(),
                        validators.EqualTo('confirm', message="Passwords do not match!")])
            confirm = PasswordField('Confirm Password')

        form = RegisterForm(request.form)

        if request.method == 'POST':
            agentName = form.agentName.data
            companyName = form.companyName.data
            email = form.email.data
            name = form.agentName.data
            password = form.password.data

            # Create cursor
            cur = mysql.connection.cursor()

            try:
                cur.execute("INSERT INTO user(name, email, password) VALUES(%s, %s, %s)", (name, email, password))
                mysql.connection.commit()
                # Get User Id
                cur.execute("SELECT user_id FROM user WHERE email='{0}'".format(email));
                mysql.connection.commit();
                userid = cur.fetchall()[0]['user_id']

                # Create new Company Rep
                cur.execute("INSERT INTO comprep(comprep_id , comp_name) VALUES(%s , %s)", (userid , companyName))
                mysql.connection.commit()

                # Close connection
                cur.close()

                flash("You are now registered successfully", 'success')
                return redirect(url_for('index'))

            except MySQLdb.IntegrityError:
                app.logger.info('Email exists already')
                flash("Email exists already", "warning")
                return render_template("comSignUp.html" , form = form)

    return render_template("comSignUp.html" , form = form)

# Admin Functions
@app.route("/adminSignIn.html", methods=['GET', 'POST'])
def adminSignIn():
    if session.get("logged_in") == True:
        if session.get("email") == "admin":
            return redirect(url_for("adminHome"))
        else:
            logout()
            return redirect(url_for("adminSignIn"))
    else:
        class SignIn(Form):
            email = StringField('Username', [validators.Length(min=6, max=50)])
            password = PasswordField('Password', [validators.DataRequired(),
                        validators.EqualTo('confirm', message="Passwords do not match!")])

        form = SignIn(request.form)

        if (request.method == "POST"):

            email = form.email.data
            password = form.password.data

            # Create Cursor
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM user, admin " +
             "WHERE user.user_id = admin.admin_id AND user.email = '{0}' AND user.password = '{1}'".format(email , password))
            mysql.connection.commit()

            # Get response
            queryResponse = cur.fetchall();

            if (len(queryResponse) == 0):
                flash("INVALID LOGIN! Check Email/Password!", "warning")
                return redirect(url_for("adminSignIn"))
            else:
                app.logger.info('PASSWORD MATCHED')
                session['logged_in'] = True
                session['email'] = email
                flash("ADMIN logged in", "success")
                return redirect(url_for("adminHome"))

        return render_template("adminSignIn.html" , form=form)


@app.route("/adminHome.html")
def adminHome():
    return render_template("adminHome.html")


@app.route("/adminSearchEditQuestion.html" , methods=["GET" , "POST"])
def adminSearchEditQuestion():

    class searchQuestion(Form):
        search = StringField('Search' , [validators.DataRequired()])

    form = searchQuestion(request.form)

    if (request.method == "POST"):

        search = form.search.data

        return redirect(url_for("adminSearchQuestionResult", topic=search))

    return render_template("adminSearchEditQuestion.html" , form=form)

@app.route("/adminSearchQuestionResult/<topic>" , methods=["GET" , "POST"])
def adminSearchQuestionResult(topic):

    # Create cursor
    cur = mysql.connection.cursor()

    # Find the Question
    cur.execute("SELECT * from question where dept_name = '{0}';".format(topic))
    mysql.connection.commit()

    questions = cur.fetchall();

    class searchQuestion(Form):
        id = StringField('id' , [validators.DataRequired()])

    form = searchQuestion(request.form)

    if (request.method == "POST"):

        id = form.id.data

        return redirect(url_for("adminEditQuestion" , id=id))


    return render_template("adminSearchQuestionResult.html" , form = form , questions=questions , topic=topic)



@app.route("/adminCreateQuestion.html" , methods=['Get', 'POST'])
def adminCreateQuestion():
    class makeQuestion(Form):
        question = TextAreaField("Question: ",[validators.Required("Please enter Question")])
        answer = TextAreaField("Answer: ",[validators.Required("Please Answer")])
        dept_name = TextAreaField("Department Name: ",[validators.Required("dept_name")])
        difficulty = RadioField("Difficulty", choices=[("e" , "easy") , ('m' , 'medium') , ('h', 'hard')])
    form = makeQuestion(request.form)
    if request.method == 'POST':
        # Create Cursor
        cur = mysql.connection.cursor()

        question = form.question.data
        answer = form.answer.data
        difficulty = form.difficulty.data
        dept_name = form.dept_name.data
        test_case = ""
        approval = 1

        cur.execute("INSERT INTO question(dept_name, description, test_case, difficulty, approval)" +
            "VALUES ('{0}', '{1}', '{2}', '{3}', 1)".format(dept_name, question, test_case, difficulty))
        mysql.connection.commit()

        # Get response
        queryResponse = cur.fetchall()

        cur.execute("SELECT question_id FROM question")
        mysql.connection.commit()

        temp = cur.fetchall()

        cur.execute("INSERT INTO discussion(discussion_id, question_id) Values(%s, %s)",
                        [temp[len(temp)-1]['question_id'], temp[len(temp)-1]['question_id']])
        mysql.connection.commit()

        cur.close()
        return redirect(url_for("adminHome"))
    return render_template("adminCreateQuestion.html", form = form)


@app.route("/adminCreateTrack.html", methods=['GET', 'POST'])
def adminCreateTrack():

    global questionNoOfNewTrack
    # Create cursor
    cur = mysql.connection.cursor()

    # Create new User
    cur.execute("SELECT * FROM question")
    mysql.connection.commit()

    queryResponse = cur.fetchall();

    if len(queryResponse) == 0:
        flash ("There is not any question", "warning")
        return render_template("adminCreateTrack.html", question = queryResponse)

    class CreateTrackForm(Form):
        id = StringField('id', [validators.Length(min=1, max=50)])
    form = CreateTrackForm(request.form)

    global compCreatedTrackId

    if request.method == "POST":
        id = form.id.data
        if id !='0':
            try:
                cur.execute("INSERT INTO trackquestions (question_id, track_id) VALUES(%s,%s)", [id,compCreatedTrackId]);
                mysql.connection.commit()
                questionNoOfNewTrack = questionNoOfNewTrack + 1;
            except:
                flash("Already Added to Track")
        else:
            cur.execute("UPDATE track SET no_questions = '{0}' WHERE track_id = '{1}'".format(questionNoOfNewTrack,compCreatedTrackId));
            mysql.connection.commit()
            questionNoOfNewTrack = 0;
            return redirect(url_for('adminReviewTrack'))
    else:
        trackName = "Track";
        cur.execute("INSERT INTO track (track_name) VALUES(%s)", [trackName]);
        mysql.connection.commit()

        cur.execute("SELECT track_id FROM track");
        mysql.connection.commit()
        trackResult = cur.fetchall();

        compCreatedTrackId = (trackResult[len(trackResult)-1]["track_id"]);

    return render_template("adminCreateTrack.html", question = queryResponse)

@app.route("/adminReviewTrack.html", methods=['GET', 'POST'])
def adminReviewTrack():

    global compCreatedTrackId2

    # Create cursor
    cur = mysql.connection.cursor()
    cur.execute("SELECT track_id FROM track");
    mysql.connection.commit()
    trackResult = cur.fetchall();

    compCreatedTrackId2 = (trackResult[len(trackResult)-1]["track_id"]);
    print (compCreatedTrackId2);

    cur.execute("SELECT * FROM question,trackquestions WHERE (trackquestions.track_id='{0}'AND trackquestions.question_id = question.question_id)".format(compCreatedTrackId2));
    mysql.connection.commit()
    outputQuestions = cur.fetchall();

    if len(outputQuestions) == 0:
        flash ("There is not any question in the track")
        return render_template("adminReviewTrack.html",question=outputQuestions)

    class ReviewForm(Form):
        trackName = StringField('trackName', [validators.Length(min=1, max=50)])
    form = ReviewForm(request.form)

    if request.method == "POST":
        trackName = form.trackName.data

        cur.execute("UPDATE track SET track_name = '{0}' WHERE track_id = '{1}'".format(trackName,compCreatedTrackId2));
        mysql.connection.commit()

        return redirect(url_for('adminHome'))

    return render_template("adminReviewTrack.html",question=outputQuestions)


@app.route("/adminReviewQuestion.html" , methods=["GET" , "POST"])
def adminReviewQuestion():

    class buttonForm(Form):

        id = StringField('id' , [validators.DataRequired()])
        btn = StringField('btn', [validators.DataRequired()])

    form = buttonForm(request.form)

    if (request.method == "POST") :

        id = form.id.data
        btn = form.btn.data

        print (btn)

        if (btn == "review"):

            # Send to specific question review
            return redirect(url_for('adminSpecificReviewQuestion' , id=id))

        elif (btn == "accept"):
            # Create cursor
            cur = mysql.connection.cursor()

            # Create new User
            cur.execute("UPDATE question set approval=1 where question_id={0};".format(id))
            mysql.connection.commit()

        else:
            # Create cursor
            cur = mysql.connection.cursor()

            # Create new User
            cur.execute("DELETE from question where question_id={0};".format(id))
            mysql.connection.commit()
            redirect(url_for("adminReviewQuestion"))

    # Create cursor
    cur = mysql.connection.cursor()

    # Create new User
    cur.execute("SELECT * FROM question WHERE approval = 0")
    mysql.connection.commit()

    # Get the response
    questions = cur.fetchall();

    return render_template("adminReviewQuestion.html", form=form, questions=questions)

@app.route("/adminReviewSpecificQuestion/<id>" , methods=["GET", "POST"])
def adminSpecificReviewQuestion(id=-1):

    class updateQuestion(Form):
        id = StringField('id' , [validators.DataRequired()])
        btn = StringField('btn', [validators.DataRequired()])

    form = updateQuestion(request.form)

    if (request.method == "POST"):

        id = form.id.data
        btn = form.btn.data

        if (btn == "accept"):

            # Create cursor
            cur = mysql.connection.cursor()

            # Create new User
            cur.execute("update question set approval=1 where question_id={0};".format(id))
            mysql.connection.commit()

        elif (btn == "decline"):

            # Create cursor
            cur = mysql.connection.cursor()

            # Create new User
            cur.execute("DELETE from question where question_id={0};".format(id))
            mysql.connection.commit()


        return redirect(url_for("adminReviewQuestion"))

    question = []
    if (int(id) > 0):
        # Create cursor
        cur = mysql.connection.cursor()

        # Create new User
        cur.execute("SELECT * FROM question WHERE question_id ={0}".format(str(id)))
        mysql.connection.commit()
        adminSpecificReviewQuestion
        # Get the response
        question = cur.fetchall()[0];

    return render_template("adminReviewSpecificQuestion.html" , question=question , form=form)

@app.route("/adminEditQuestion/<id>" , methods=["GET" , "POST"])
def adminEditQuestion(id):
    # Create cursor
    cur = mysql.connection.cursor()

    # Find the Question
    cur.execute("SELECT * from question where question_id = '{0}';".format(id))
    mysql.connection.commit()

    q = cur.fetchall()[0];

    class editQuestion(Form):

        question = TextAreaField('Question' , default=q['description'] )
        answer = TextAreaField('Answer' , default=q['test_case'])
        difficulty = RadioField("Difficulty", choices=[("Easy" , "Easy") , ('Medium' , 'Medium') , ('Hard', 'Hard')] , default=q['difficulty'])


    form = editQuestion(request.form)

    if (request.method == "POST"):

        question = form.question.data
        answer = form.answer.data
        diff = form.difficulty.data

        # Create cursor
        cur = mysql.connection.cursor()

        # Create new User
        cur.execute("UPDATE question set description='{0}' , test_case='{1}' , difficulty='{2}' where question_id={3};"
                    .format(question , answer , diff , id))
        mysql.connection.commit()

        return redirect(url_for("adminHome"))



    return render_template('adminEditQuestion.html' , form=form)

if __name__== '__main__':
    app.secret_key = "difficult"
    app.run()
