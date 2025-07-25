from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from models import db, User, Course, Enrollment, ParentStudent
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user is None or not user.check_password(request.form['password']):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        # Validar que el correo del superusuario sea el correcto
        if request.form['role'] == 'superadmin':
            if request.form['email'] not in ['santillan@cetis14.edu.mx', 'francisco.santillan@cetis14.edu.mx', 'santillan@kenova.xyz', 'francisco.santillan@kenova.xyz', 'administrador@kenova.xyz']:
                flash('Invalid superadmin email')
                return redirect(url_for('register'))

        # Validar que el dominio para los demas usuarios sea @kenova.xyz
        if request.form['role'] != 'superadmin' and not request.form['email'].endswith('@kenova.xyz'):
            flash('Only @kenova.xyz domains are allowed for this role')
            return redirect(url_for('register'))

        user = User(email=request.form['email'], role=request.form['role'])
        user.set_password(request.form['password'])
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'superadmin':
        return redirect(url_for('dashboard_superadmin'))
    elif current_user.role == 'teacher':
        return redirect(url_for('dashboard_teacher'))
    elif current_user.role == 'student':
        return redirect(url_for('dashboard_student'))
    elif current_user.role == 'parent':
        return redirect(url_for('dashboard_parent'))
    else:
        return redirect(url_for('index'))

@app.route('/dashboard/superadmin')
@login_required
def dashboard_superadmin():
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))

    pending_users = User.query.filter_by(validated=False).all()
    validated_users = User.query.filter_by(validated=True).all()

    return render_template('dashboard_superadmin.html', pending_users=pending_users, validated_users=validated_users)

@app.route('/validate_user/<int:user_id>')
@login_required
def validate_user(user_id):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    user.validated = True
    db.session.commit()
    msg = Message('Account Validated',
                  sender='noreply@kenova.xyz',
                  recipients=[user.email])
    msg.body = 'Your account has been validated by a superadmin.'
    mail.send(msg)
    flash(f'User {user.email} has been validated.')
    return redirect(url_for('dashboard_superadmin'))

@app.route('/assign_role/<int:user_id>/<string:role>')
@login_required
def assign_role(user_id, role):
    if current_user.role != 'superadmin':
        return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    user.role = role
    db.session.commit()
    flash(f'User {user.email} has been assigned the role of {role}.')
    return redirect(url_for('dashboard_superadmin'))

@app.route('/dashboard/teacher')
@login_required
def dashboard_teacher():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))

    courses = Course.query.filter_by(teacher_id=current_user.id).all()
    return render_template('dashboard_teacher.html', courses=courses)

@app.route('/create_course', methods=['POST'])
@login_required
def create_course():
    if current_user.role != 'teacher':
        return redirect(url_for('index'))

    course = Course(name=request.form['name'], teacher_id=current_user.id)
    db.session.add(course)
    db.session.commit()
    flash('Course created successfully')
    return redirect(url_for('dashboard_teacher'))

@app.route('/dashboard/student')
@login_required
def dashboard_student():
    if current_user.role != 'student':
        return redirect(url_for('index'))

    enrollments = Enrollment.query.filter_by(student_id=current_user.id).all()
    courses = [Course.query.get(enrollment.course_id) for enrollment in enrollments]
    return render_template('dashboard_student.html', courses=courses)

@app.route('/dashboard/parent')
@login_required
def dashboard_parent():
    if current_user.role != 'parent':
        return redirect(url_for('index'))

    student_relations = ParentStudent.query.filter_by(parent_id=current_user.id).all()
    students = [User.query.get(relation.student_id) for relation in student_relations]
    return render_template('dashboard_parent.html', students=students)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
