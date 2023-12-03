# Imports the necessary modules and classes from Flask
from flask import Flask, flash, render_template, redirect, request, url_for, get_flashed_messages
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import User, AddStudent, Course, CourseEnrollment, db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func

# Creates a Flask application
app = Flask(__name__)
app.config.from_object('config')

# Sets a secret key for the application
app.secret_key = "your_secret_key"

# Creates a LoginManager instance and configures login-related settings
login_manager = LoginManager(app)
login_manager.login_view = "login_page"

# Initialises the database within the application context
with app.app_context():
    db.init_app(app)
    db.create_all()

# Defines the user loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(int(user_id))

# Function to check if the phone number is already in the database
def is_phone_number_taken(new_phone, student_id):
    return (
        AddStudent.query.filter(AddStudent.phone == new_phone, AddStudent.id != student_id)
        .first() is not None
    )

# Function to check if the email is already in the database
def is_email_taken(new_email, student_id):
    return (
        AddStudent.query.filter(AddStudent.email == new_email, AddStudent.id != student_id)
        .first() is not None
    )

# Function to retrieve statistics from the database
def get_enrollment_statistics():
    most_enrolled_student = (
        db.session.query(
            AddStudent.first_name,
            AddStudent.last_name,
            func.count(CourseEnrollment.id).label('enrollment_count')
        )
        .join(CourseEnrollment)
        .group_by(AddStudent.id)
        .order_by(func.count(CourseEnrollment.id).desc())
        .first()
    )

    least_enrolled_student = (
        db.session.query(
            AddStudent.first_name,
            AddStudent.last_name,
            func.count(CourseEnrollment.id).label('enrollment_count')
        )
        .join(CourseEnrollment)
        .group_by(AddStudent.id)
        .order_by(func.count(CourseEnrollment.id))
        .first()
    )

    most_enrolled_course = (
        db.session.query(
            Course.course_name,
            func.count(CourseEnrollment.id).label('enrollment_count')
        )
        .join(CourseEnrollment)
        .group_by(Course.id)
        .order_by(func.count(CourseEnrollment.id).desc())
        .first()
    )

    least_enrolled_course = (
        db.session.query(
            Course.course_name,
            func.count(CourseEnrollment.id).label('enrollment_count')
        )
        .join(CourseEnrollment)
        .group_by(Course.id)
        .order_by(func.count(CourseEnrollment.id))
        .first()
    )

    total_students = db.session.query(AddStudent).count()
    total_courses = db.session.query(Course).count()

    return most_enrolled_student, least_enrolled_student, most_enrolled_course, least_enrolled_course, total_students, total_courses

# Defines the route for the homepage
@app.route('/')
def index():
    flashed_messages = get_flashed_messages(with_categories=True)

    # Clears the flashed messages for the current request context
    get_flashed_messages()

    return render_template("index.html", flashed_messages=flashed_messages)

# Defines the route for the registration page (GET request)
@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")

# Defines the route for the registration action (POST request)
@app.route("/register", methods=["POST"])
def register_action():
    username = request.form["username"]
    password = request.form["password"]
    if User.query.filter_by(username=username).first():
        flash(f"The username '{username}' is already taken")
        return redirect(url_for("register_page"))

    user = User(username=username, password=password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    flash(f"Welcome {username}!")

    return redirect(url_for("index"))

# Defines the route for the login page (GET request)
@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html")

# Defines the route for the login action (POST request)
@app.route("/login", methods=["POST"])
def login_action():
    username = request.form["username"]
    password = request.form["password"]
    user = User.query.filter_by(username=username).first()
    if not user:
        flash(f"No such user as '{username}'")
        return redirect(url_for("login_page"))
    if password != user.password:
        flash(f"Invalid password for the user '{username}'")
        return redirect(url_for("login_page"))

    login_user(user)
    flash(f"Welcome back, {username}!")
    return redirect(url_for("index"))

# Defines the route for the logout page (GET request)
@app.route("/logout", methods=["GET"])
@login_required
def logout_page():
    return render_template("logout.html")

# Defines the route for the logout action (POST request)
@app.route("/logout", methods=["POST"])
@login_required
def logout_action():
    logout_user()
    flash("You have been logged out")

    return redirect(url_for("index"))

# Defines the route for adding a student (GET and POST requests)
@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    added_students = None
    student = None  

    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date()
        phone = request.form['phone']
        email = request.form['email']
        student_id = request.form.get('student_id')  

        current_time = datetime.utcnow()

        # Check if the same email or phone already exists in the database
        existing_student_email = AddStudent.query.filter(
            AddStudent.email == email,
            AddStudent.user_id == current_user.id,
            AddStudent.id != student_id if student_id else True
        ).first()

        existing_student_phone = AddStudent.query.filter(
            AddStudent.phone == phone,
            AddStudent.user_id == current_user.id,
            AddStudent.id != student_id if student_id else True
        ).first()

        if existing_student_email:
            flash('This email address is already in use', 'error')
            return redirect(url_for('add_student'))

        if existing_student_phone:
            flash('This phone number is already in use', 'error')
            return redirect(url_for('add_student'))

        if student_id:  # If student_id is present, fetch the existing student for editing
            student = AddStudent.query.get(student_id)

            if student:
                student.first_name = first_name
                student.last_name = last_name
                student.date_of_birth = date_of_birth
                student.phone = phone
                student.email = email

                flash('Student details updated successfully!')
        else:  # If no student_id, create a new student
            student = AddStudent(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                phone=phone,
                email=email,
                user_id=current_user.id,
                created_at=current_time
            )

            db.session.add(student)
            flash('Student added successfully!')

        db.session.commit()

    # Fetch the added students for display
    added_students = AddStudent.query.all()

    # Clear the flashed messages for the current request context
    get_flashed_messages()

    return render_template('add_student.html', added_students=added_students)

# Defines the route for editing a student (GET and POST requests)
@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    student = AddStudent.query.get(student_id)


    if request.method == 'POST':
        if 'delete' in request.form:
            db.session.delete(student)
            db.session.commit()
            flash('Student deleted successfully!')
            return redirect(url_for('add_student'))

        else:
            student.first_name = request.form['first_name']
            student.last_name = request.form['last_name']
            student.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date()
            phone = request.form['phone']
            email = request.form['email']

            # Checks if the phone number is already taken
            if is_phone_number_taken(phone, student_id):
                flash('This phone number is already in use', 'error_phone')
                return redirect(url_for('edit_student', student_id=student_id))

            # Checks if the email is already taken
            if is_email_taken(email, student_id):
                flash('This email address is already in use', 'error_email')
                return redirect(url_for('edit_student', student_id=student_id))

            student.phone = phone
            student.email = email

            db.session.commit()
            flash('Student details updated successfully!')

            # Redirects to 'add_student' and display the flash message
            return redirect(url_for('add_student'))

    return render_template('edit_student.html', student=student)

# Defines the route for deleting a student
@app.route('/delete_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def delete_student(student_id):
    student = AddStudent.query.get(student_id)

    # Deletes corresponding rows in course_enrollment
    CourseEnrollment.query.filter_by(student_id=student_id).delete()

    db.session.delete(student)
    db.session.commit()

    flash('Student deleted successfully!')

    return redirect(url_for('add_student'))

# Defines the route for adding a course (GET and POST requests)
@app.route('/add_course', methods=['GET', 'POST'])
@login_required
def add_course():
    added_courses = None
    course = None

    if request.method == 'POST':
        course_name = request.form['course_name']
        day = request.form['day']
        time = request.form['time']

        current_time = datetime.utcnow()

        try:
            # Sets the user_id to the current user's ID
            course = Course(
                course_name=course_name,
                day=day,
                time=time,
                user_id=current_user.id,
                created_at=current_time
            )

            db.session.add(course)
            db.session.commit()
            flash('Course added successfully!')
        except IntegrityError as e:
            db.session.rollback()
            flash('This course already exists', 'error')

        # Redirects to the same page to avoid form resubmission on refresh
        return redirect(url_for('add_course'))

    # Clears flash messages on GET request
    flash_messages = list(get_flashed_messages(with_categories=True))
    added_courses = Course.query.all()

    return render_template('add_course.html', added_courses=added_courses, flash_messages=flash_messages)

# Defines the route for editing a course (GET and POST requests)
@app.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get(course_id)


    if request.method == 'POST':
        if 'delete' in request.form:
            db.session.delete(course)
            db.session.commit()
            flash('Course deleted successfully!')
        else:
            course.course_name = request.form['course_name']
            course.day = request.form['day']
            course.time = request.form['time']

            db.session.commit()
            flash('Course details updated successfully!')

        return redirect(url_for('add_course'))

    return render_template('edit_course.html', course=course)

# Defines the route for deleting a course
@app.route('/delete_course/<int:course_id>')
@login_required
def delete_course(course_id):
    course = Course.query.get(course_id)

    if not course:
        flash('Course not found.')
        return redirect(url_for('add_course'))


    db.session.delete(course)
    db.session.commit()
    flash('Course deleted successfully!')

    return redirect(url_for('add_course'))

# Defines the route for displaying trending statistics
@app.route('/trending')
def trending():
    most_enrolled_student, least_enrolled_student, most_enrolled_course, least_enrolled_course, total_students, total_courses = get_enrollment_statistics()

    return render_template('trending.html',
                           most_enrolled_student=most_enrolled_student,
                           least_enrolled_student=least_enrolled_student,
                           most_enrolled_course=most_enrolled_course,
                           least_enrolled_course=least_enrolled_course,
                           total_students=total_students,
                           total_courses=total_courses)

# Defines the route for adding course enrollment (GET and POST requests)
@app.route('/add_course_enrollment', methods=['GET', 'POST'])
@login_required
def add_course_enrollment():
    enrollments = None

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        course_id = request.form.get('course_id')

        # Checks if the student and course IDs are provided
        if not student_id or not course_id:
            flash('Please provide both student ID and course ID.', 'error')
            return redirect(url_for('add_course_enrollment'))

        # Converts IDs to integers
        try:
            student_id = int(student_id)
            course_id = int(course_id)
        except ValueError:
            flash('Invalid student ID or course ID.', 'error')
            return redirect(url_for('add_course_enrollment'))

        # Checks if the student and course exist
        student = AddStudent.query.get(student_id)
        course = Course.query.get(course_id)

        if not student:
            flash('Invalid student ID. This student does not exist.', 'error')
            return redirect(url_for('add_course_enrollment'))
        elif not course:
            flash('Invalid course ID. This course does not exist.', 'error')
            return redirect(url_for('add_course_enrollment'))

        # Checks if the logged-in user is the owner of the student
        if student.user != current_user:
            flash('You are not authorized to enroll this student in a course.', 'error')
            return redirect(url_for('add_course_enrollment'))

        # Checks if the student is already enrolled in the course
        existing_enrollment = CourseEnrollment.query.filter_by(
            student_id=student_id,
            course_id=course_id
        ).first()

        if existing_enrollment:
            flash('This student is already enrolled in this course!', 'error')
        else:
            # Stores the student ID before deleting the enrollment
            enrollment = CourseEnrollment(
                student_id=student_id,
                course_id=course_id,
                created_by=current_user.id,
                created_at=datetime.utcnow()
            )

            db.session.add(enrollment)
            flash('Enrollment added successfully!')
            db.session.commit()

    # Fetches the flashed messages for the current request context
    flashed_messages = get_flashed_messages(with_categories=True)

    enrollments = CourseEnrollment.query.all()

    return render_template('course_enrollment.html', enrollments=enrollments, flashed_messages=flashed_messages)

# Defines the route for editing course enrollment (GET and POST requests)
@app.route('/edit_course_enrollment/<int:enrollment_id>', methods=['GET', 'POST'])
@login_required
def edit_course_enrollment(enrollment_id):
    enrollment = CourseEnrollment.query.get(enrollment_id)

    if not enrollment:
        flash('Enrollment not found.')
        return redirect(url_for('add_course_enrollment'))

    if enrollment.creator != current_user:
        flash("You are not authorized to edit this enrollment.")
        return redirect(url_for('add_course_enrollment'))

    if request.method == 'POST':
        if 'delete' in request.form:
            db.session.delete(enrollment)
            db.session.commit()
            flash('Enrollment withdrawn successfully!')
        else:
            enrollment.student_id = request.form['student_id']
            enrollment.course_id = request.form['course_id']

            db.session.commit()
            flash('Enrollment details updated successfully!')

        return redirect(url_for('add_course_enrollment'))

    return render_template('edit_course_enrollment.html', enrollment=enrollment)

# Defines the route for deleting course enrollment
@app.route('/delete_course_enrollment/<int:enrollment_id>')
@login_required
def delete_course_enrollment(enrollment_id):
    enrollment = CourseEnrollment.query.get(enrollment_id)

    if not enrollment:
        flash('Enrollment not found.')
    elif enrollment.creator != current_user:
        flash("You are not authorized to delete this enrollment.")
    else:
        # Deletes the enrollment
        db.session.delete(enrollment)
        db.session.commit()
        flash('Enrollment withdrawn successfully!')

    return redirect(url_for('add_course_enrollment'))  

# Runs the application if the script is executed directly
if __name__ == "__main__":
    app.run(debug=True)  