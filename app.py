
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from datetime import date
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.secret_key = "hospital-demo-secret-key"


# ---------- DATABASE ----------

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="PASSWARD",
        database="hospital_db"
    )


def go(section):
    return redirect(url_for("dashboard") + "#" + section)


# ---------- DASHBOARD ----------

@app.route("/")
def dashboard():
    db = get_db()
    cur = db.cursor(dictionary=True)

    try:
        cur.execute("SELECT COUNT(*) AS n FROM patients")
        total_patients = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM doctors")
        total_doctors = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) AS n FROM appointments")
        total_appointments = cur.fetchone()["n"]

        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM bills WHERE payment_status = 'Pending'
        """)
        pending_bills = cur.fetchone()["total"]

        cur.execute("SELECT * FROM patients ORDER BY patient_id DESC")
        patients = cur.fetchall()

        cur.execute("""
            SELECT d.doctor_id, d.doctor_name, d.specialization,
                   d.phone, d.department_id, dep.department_name
            FROM doctors d
            LEFT JOIN departments dep
            ON d.department_id = dep.department_id
            ORDER BY d.doctor_id DESC
        """)
        doctors = cur.fetchall()

        cur.execute("SELECT * FROM departments ORDER BY department_id DESC")
        departments = cur.fetchall()

        cur.execute("""
            SELECT a.appointment_id, a.patient_id, a.doctor_id,
                   a.appointment_date, a.appointment_time,
                   a.diagnosis, a.status,
                   p.name AS patient_name, d.doctor_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN doctors d ON a.doctor_id = d.doctor_id
            ORDER BY a.appointment_date DESC, a.appointment_time DESC
        """)
        appointments = cur.fetchall()

        cur.execute("""
            SELECT b.bill_id, b.patient_id, b.appointment_id,
                   b.amount, b.payment_status, b.bill_date,
                   p.name AS patient_name
            FROM bills b
            JOIN patients p ON b.patient_id = p.patient_id
            ORDER BY b.bill_id DESC
        """)
        bills = cur.fetchall()

        return render_template(
            "index.html",
            total_patients=total_patients,
            total_doctors=total_doctors,
            total_appointments=total_appointments,
            pending_bills=pending_bills,
            patients=patients,
            doctors=doctors,
            departments=departments,
            appointments=appointments,
            bills=bills,
            today=date.today().isoformat()
        )
    finally:
        cur.close()
        db.close()


# ---------- PATIENTS ----------

@app.route("/patient/add", methods=["POST"])
def add_patient():
    name = request.form.get("name", "").strip()
    age = request.form.get("age", type=int)

    if not name or age is None or not 1 <= age <= 120:
        flash("Enter a valid name and age.", "error")
        return go("patients")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO patients (name, age, gender, phone, disease)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            name, age, request.form.get("gender", ""),
            request.form.get("phone", "").strip(),
            request.form.get("disease", "").strip()
        ))
        db.commit()
        flash("Patient added.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not add patient: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("patients")


@app.route("/patient/update/<int:pid>", methods=["POST"])
def update_patient(pid):
    name = request.form.get("name", "").strip()
    age = request.form.get("age", type=int)

    if not name or age is None or not 1 <= age <= 120:
        flash("Enter a valid name and age.", "error")
        return go("patients")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE patients
            SET name=%s, age=%s, gender=%s, phone=%s, disease=%s
            WHERE patient_id=%s
        """, (
            name, age, request.form.get("gender", ""),
            request.form.get("phone", "").strip(),
            request.form.get("disease", "").strip(), pid
        ))
        db.commit()
        flash("Patient updated successfully.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not update patient: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("patients")


@app.route("/patient/delete/<int:pid>", methods=["POST"])
def delete_patient(pid):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM patients WHERE patient_id=%s", (pid,))
        db.commit()
        flash("Patient deleted.", "success")
    except mysql.connector.Error:
        db.rollback()
        flash("Cannot delete a patient linked to appointments or bills.", "error")
    finally:
        cur.close()
        db.close()
    return go("patients")


# ---------- DOCTORS ----------

@app.route("/doctor/add", methods=["POST"])
def add_doctor():
    name = request.form.get("doctor_name", "").strip()
    if not name:
        flash("Doctor name is required.", "error")
        return go("doctors")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO doctors
            (doctor_name, specialization, phone, department_id)
            VALUES (%s, %s, %s, %s)
        """, (
            name, request.form.get("specialization", "").strip(),
            request.form.get("phone", "").strip(),
            request.form.get("department_id") or None
        ))
        db.commit()
        flash("Doctor added.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not add doctor: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("doctors")


@app.route("/doctor/update/<int:did>", methods=["POST"])
def update_doctor(did):
    name = request.form.get("doctor_name", "").strip()
    if not name:
        flash("Doctor name is required.", "error")
        return go("doctors")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE doctors
            SET doctor_name=%s, specialization=%s, phone=%s,
                department_id=%s
            WHERE doctor_id=%s
        """, (
            name, request.form.get("specialization", "").strip(),
            request.form.get("phone", "").strip(),
            request.form.get("department_id") or None, did
        ))
        db.commit()
        flash("Doctor updated successfully.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not update doctor: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("doctors")


@app.route("/doctor/delete/<int:did>", methods=["POST"])
def delete_doctor(did):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("DELETE FROM doctors WHERE doctor_id=%s", (did,))
        db.commit()
        flash("Doctor deleted.", "success")
    except mysql.connector.Error:
        db.rollback()
        flash("Remove or reassign this doctor's appointments first.", "error")
    finally:
        cur.close()
        db.close()
    return go("doctors")


# ---------- DEPARTMENTS ----------

@app.route("/department/add", methods=["POST"])
def add_department():
    name = request.form.get("department_name", "").strip()
    location = request.form.get("location", "").strip()

    if not name:
        flash("Department name is required.", "error")
        return go("departments")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO departments (department_name, location)
            VALUES (%s, %s)
        """, (name, location))
        db.commit()
        flash("Department added.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not add department: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("departments")


@app.route("/department/update/<int:dep_id>", methods=["POST"])
def update_department(dep_id):
    name = request.form.get("department_name", "").strip()
    location = request.form.get("location", "").strip()

    if not name:
        flash("Department name is required.", "error")
        return go("departments")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE departments
            SET department_name=%s, location=%s
            WHERE department_id=%s
        """, (name, location, dep_id))
        db.commit()
        flash("Department updated successfully.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not update department: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("departments")


@app.route("/department/delete/<int:dep_id>", methods=["POST"])
def delete_department(dep_id):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "DELETE FROM departments WHERE department_id=%s", (dep_id,)
        )
        db.commit()
        flash("Department deleted.", "success")
    except mysql.connector.Error:
        db.rollback()
        flash("Reassign this department's doctors before deleting it.", "error")
    finally:
        cur.close()
        db.close()
    return go("departments")


# ---------- APPOINTMENTS ----------

@app.route("/appointment/add", methods=["POST"])
def add_appointment():
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    appt_date = request.form.get("appointment_date")
    appt_time = request.form.get("appointment_time")

    if not all([patient_id, doctor_id, appt_date, appt_time]):
        flash("Complete all required appointment fields.", "error")
        return go("appointments")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO appointments
            (patient_id, doctor_id, appointment_date,
             appointment_time, diagnosis, status)
            VALUES (%s, %s, %s, %s, %s, 'Scheduled')
        """, (
            patient_id, doctor_id, appt_date, appt_time,
            request.form.get("diagnosis", "").strip()
        ))
        db.commit()
        flash("Appointment booked.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not book appointment: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("appointments")


@app.route("/appointment/update/<int:aid>", methods=["POST"])
def update_appointment(aid):
    patient_id = request.form.get("patient_id")
    doctor_id = request.form.get("doctor_id")
    appt_date = request.form.get("appointment_date")
    appt_time = request.form.get("appointment_time")

    if not all([patient_id, doctor_id, appt_date, appt_time]):
        flash("Complete all required appointment fields.", "error")
        return go("appointments")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE appointments
            SET patient_id=%s, doctor_id=%s,
                appointment_date=%s, appointment_time=%s,
                diagnosis=%s
            WHERE appointment_id=%s
        """, (
            patient_id, doctor_id, appt_date, appt_time,
            request.form.get("diagnosis", "").strip(), aid
        ))
        db.commit()
        flash("Appointment updated successfully.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not update appointment: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("appointments")


@app.route("/appointment/status/<int:aid>", methods=["POST"])
def update_appointment_status(aid):
    status = request.form.get("status")
    if status not in ("Scheduled", "Completed", "Cancelled"):
        flash("Invalid appointment status.", "error")
        return go("appointments")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE appointments SET status=%s
            WHERE appointment_id=%s
        """, (status, aid))
        db.commit()
        flash("Appointment status updated.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not update status: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("appointments")


@app.route("/appointment/delete/<int:aid>", methods=["POST"])
def delete_appointment(aid):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            "DELETE FROM appointments WHERE appointment_id=%s", (aid,)
        )
        db.commit()
        flash("Appointment deleted.", "success")
    except mysql.connector.Error:
        db.rollback()
        flash("This appointment is linked to a bill. Handle the bill first.", "error")
    finally:
        cur.close()
        db.close()
    return go("appointments")


# ---------- BILLING ----------

@app.route("/bill/add", methods=["POST"])
def add_bill():
    try:
        amount = Decimal(request.form.get("amount", ""))
        if not amount.is_finite() or amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        flash("Enter a valid positive amount.", "error")
        return go("billing")

    bill_date = request.form.get("bill_date")
    patient_id = request.form.get("patient_id")
    appointment_id = request.form.get("appointment_id") or None

    if not bill_date or not patient_id:
        flash("Choose a patient and bill date.", "error")
        return go("billing")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            INSERT INTO bills
            (patient_id, appointment_id, amount, payment_status, bill_date)
            VALUES (%s, %s, %s, 'Pending', %s)
        """, (patient_id, appointment_id, amount, bill_date))
        db.commit()
        flash("Bill created.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not create bill: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("billing")


@app.route("/bill/pay/<int:bid>", methods=["POST"])
def pay_bill(bid):
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""
            UPDATE bills SET payment_status='Paid' WHERE bill_id=%s
        """, (bid,))
        db.commit()
        flash("Bill marked as paid.", "success")
    except mysql.connector.Error as e:
        db.rollback()
        flash(f"Could not update bill: {e}", "error")
    finally:
        cur.close()
        db.close()
    return go("billing")


if __name__ == "__main__":
    app.run(debug=True)
