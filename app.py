from flask import Flask, render_template, request, redirect, session, Response
import pyodbc
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'secret123'

def get_connection():
    conn = pyodbc.connect(
        'DRIVER={SQL Server};'
        'SERVER=TANISHQ;'
        'DATABASE=healthcare;'
        'Trusted_Connection=yes;'
    )
    return conn

# ---------- AI LOGIC ----------
def analyze_health(bp, oxygen, sugar, pulse):
    result = []

    if bp > 140:
        result.append("High BP")
    else:
        result.append("BP Normal")

    if oxygen < 95:
        result.append("Low Oxygen")
    else:
        result.append("Oxygen Normal")

    if sugar > 140:
        result.append("High Sugar")
    else:
        result.append("Sugar Normal")

    if pulse < 60 or pulse > 100:
        result.append("Abnormal Pulse")
    else:
        result.append("Pulse Normal")

    return result


# ---------- ROUTES ----------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/find-doctor')
def find_doctor():
    return render_template('find_doctor.html')

# ---------- LOGIN ----------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (user,pwd))
        data = c.fetchone()
        conn.close()

        if data:
            session['user'] = user
            return redirect('/services')

    return render_template('login.html')


# ---------- REGISTER ----------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO users(username,password) VALUES(?,?)", (user,pwd))
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


# ---------- SERVICES ----------
@app.route('/services', methods=['GET','POST'])
def services():
    if 'user' not in session:
        return redirect('/login')

    result = None

    if request.method == 'POST':
        bp = int(request.form['bp'])
        oxygen = int(request.form['oxygen'])
        sugar = int(request.form['sugar'])
        pulse = int(request.form['pulse'])

        result = analyze_health(bp, oxygen, sugar, pulse)

        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO reports(username,bp,oxygen,sugar,pulse) VALUES(?,?,?,?,?)",
                  (session['user'],bp,oxygen,sugar,pulse))
        conn.commit()
        conn.close()

    return render_template('services.html', result=result)


# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT bp,oxygen,sugar,pulse FROM reports WHERE username=?", (session['user'],))
    rows = c.fetchall()
    data = [list(row) for row in rows]
    conn.close()

    return render_template('dashboard.html', data=data)


# ---------- DOWNLOAD CSV (NEW FEATURE) ----------
@app.route('/download')
def download():
    if 'user' not in session:
        return redirect('/login')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT bp, oxygen, sugar, pulse FROM reports WHERE username=?", (session['user'],))
    rows = cursor.fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Username", "BP", "Oxygen", "Sugar", "Pulse"])

    # Data
    for row in rows:
        writer.writerow([session['user'], row.bp, row.oxygen, row.sugar, row.pulse])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=health_data.csv"}
    )


# ---------- BMI ----------
@app.route('/bmi', methods=['GET', 'POST'])
def bmi():
    bmi = None
    status = ""

    if request.method == 'POST':
        height = float(request.form['height'])
        weight = float(request.form['weight'])

        if height > 0 and weight > 0:
            bmi = round(weight / ((height / 100) ** 2), 2)

            if bmi < 18.5:
                status = "Underweight"
            elif bmi < 24.9:
                status = "Normal weight"
            elif bmi < 29.9:
                status = "Overweight"
            else:
                status = "Obese"
        else:
            status = "Invalid input"

    return render_template('bmi.html', bmi=bmi, status=status)


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)