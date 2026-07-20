import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from ping3 import ping
from mail import send_email
import pandas as pd

app = Flask(__name__)
app.secret_key = 'noc_secure_development_token'

DB_FILE = os.path.join(os.path.dirname(__file__), 'database.json')

# --- DB Utility Handlers ---
def read_db():
    if not os.path.exists(DB_FILE):
        return {"users": [], "devices": [], "daily_checklists": {}, "incidents": []}
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def write_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- Authentication Guard ---
def login_required(roles=None):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'username' not in session:
                flash("Authentication required. Please access credentials first.", "warning")
                return redirect(url_for('login'))
            if roles and session.get('role') not in roles:
                flash("Access denied. Insufficient role permissions.", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# --- Application Routing Paths ---
@app.route('/')
def home():
    return redirect(url_for('dashboard')) if 'username' in session else redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        selected_role = request.form.get('role')
        
        db = read_db()
        user = next((u for u in db['users'] if u['username'] == username), None)
        
        if user and (user['password_hash'] == password or check_password_hash(user['password_hash'], password)):
            if user['role'] != selected_role:
                flash(f"Access Denied: User '{username}' does not hold '{selected_role}' clearance.", "danger")
                return render_template('login.html')
                
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f"Session initialized. Authenticated as: {username} ({user['role']})", "success")
            return redirect(url_for('dashboard'))
        
        flash("Invalid authentication credentials.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Session terminated successfully.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required()
def dashboard():
    db = read_db()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Extract monitoring metrics
    devices = db.get('devices', [])
    online_count = sum(1 for d in devices if d['status'] == 'Online')
    
    checklist = db.get('daily_checklists', {}).get(today, {}).get('tasks', {})
    total_tasks = len(checklist)
    completed_tasks = sum(1 for t in checklist.values() if t['status'] in ['Completed', 'Needs Attention', 'Failed'])
    
    completion_rate = int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    critical_alerts = sum(1 for d in devices if d['status'] == 'Offline')

    metrics = {
        "completion_rate": completion_rate,
        "devices_online": f"{online_count} / {len(devices)}",
        "open_incidents": len(db.get('incidents', [])),
        "critical_alerts": critical_alerts,
        "today_activities": total_tasks if total_tasks > 0 else 10
    }
    return render_template('dashboard.html', metrics=metrics, devices=devices)

@app.route('/checklist', methods=['GET', 'POST'])
@login_required(roles=['Administrator', 'Network Engineer', 'OJT User'])
def checklist():
    db = read_db()
    today = datetime.now().strftime('%Y-%m-%d')
    categories = ["Internet", "Firewall", "Switches", "Servers", "UPS", "Wi-Fi", "CCTV", "Backup", "Security", "Documentation"]
    
    if today not in db['daily_checklists']:
        db['daily_checklists'][today] = {
            "completed_by": None,
            "submitted_at": None,
            "tasks": {cat: {"status": "Pending", "remarks": ""} for cat in categories}
        }
        write_db(db)

    if request.method == 'POST':
        for cat in categories:
            db['daily_checklists'][today]['tasks'][cat]['status'] = request.form.get(f"status_{cat}", "Pending")
            db['daily_checklists'][today]['tasks'][cat]['remarks'] = request.form.get(f"remarks_{cat}", "")
            
            if request.form.get(f"status_{cat}") == "Failed":
                incident_id = f"INC-{datetime.now().strftime('%M%S')}"
                if not any(i['source'] == cat for i in db['incidents']):
                    db['incidents'].append({
                        "id": incident_id,
                        "source": cat,
                        "details": f"Checklist failure: {request.form.get(f'remarks_{cat}')}",
                        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M')
                    })
        
        db['daily_checklists'][today]['completed_by'] = session['username']
        db['daily_checklists'][today]['submitted_at'] = datetime.now().strftime('%I:%M %p')
        write_db(db)
        flash("Daily Checklist metrics successfully committed to registry.", "success")
        return redirect(url_for('checklist'))

    current_tasks = db['daily_checklists'][today]['tasks']
    return render_template('checklist.html', tasks=current_tasks, metadata=db['daily_checklists'][today])

@app.route('/devices/ping')
@login_required()
def run_ping_checks():
    db = read_db()
    for device in db['devices']:
        response = ping(device['ip'], timeout=1)
        if response is not None and response is not False:
            device['status'] = 'Online'
        else:
            device['status'] = 'Offline'
        device['last_checked'] = datetime.now().strftime('%I:%M %p')
    
    write_db(db)
    flash("ICMP Infrastructure sweep completed across managed IPs.", "info")
    return redirect(url_for('dashboard'))

@app.route('/devices/add', methods=['POST'])
@login_required(roles=['Administrator'])
def add_device():
    db = read_db()
    new_ip = request.form.get('new_ip')
    new_hostname = request.form.get('new_hostname')
    
    if any(device['ip'] == new_ip for device in db['devices']):
        flash(f"Error: IP address {new_ip} already exists in the system.", "danger")
        return redirect(url_for('dashboard'))

    db['devices'].append({
        "ip": new_ip,
        "hostname": new_hostname,
        "status": "Pending",
        "last_checked": "Never"
    })
    
    write_db(db)
    flash(f"New node '{new_hostname}' successfully added to monitoring.", "success")
    return redirect(url_for('dashboard'))

# UNLOCKED for all users
@app.route("/send-test-email")
@login_required()
def send_test_email():
    db = read_db()
    success = send_email(
        db["notification_settings"]["subject"],
        f"""
Hello!

This is an email generated from the NOC Portal System.

Sender Identity : {session['username']} ({session['role']})
Date : {datetime.now().strftime("%Y-%m-%d")}
Time : {datetime.now().strftime("%I:%M %p")}

If you received this message, the notification parameters are functioning correctly.
"""
    )
    if success:
        flash("Email successfully transmitted through the mail gateway.", "success")
    else:
        flash("Failed to send email. Check your SMTP settings.", "danger")
    return redirect(url_for("dashboard"))

@app.route('/devices/update', methods=['POST'])
@login_required(roles=['Administrator'])
def update_device():
    db = read_db()
    original_ip = request.form.get('original_ip')
    new_ip = request.form.get('new_ip')
    new_hostname = request.form.get('new_hostname')
    
    for device in db['devices']:
        if device['ip'] == original_ip:
            device['ip'] = new_ip
            device['hostname'] = new_hostname
            device['status'] = 'Pending'
            device['last_checked'] = 'Never'
            break
            
    write_db(db)
    flash("Device configurations updated successfully.", "success")
    return redirect(url_for('dashboard'))

@app.route('/report/export')
@login_required(roles=['Administrator', 'Network Engineer', 'Viewer/Manager'])
def export_report():
    db = read_db()
    today = datetime.now().strftime('%Y-%m-%d')
    tasks_data = db.get('daily_checklists', {}).get(today, {}).get('tasks', {})
    
    if not tasks_data:
        flash("No collection data available today to compile a structural report.", "warning")
        return redirect(url_for('dashboard'))
        
    records = [{"Category": k, "Status": v['status'], "Remarks": v['remarks']} for k, v in tasks_data.items()]
    df = pd.DataFrame(records)
    
    file_path = os.path.join(os.path.dirname(__file__), f"NOC-Report-{today}.xlsx")
    df.to_excel(file_path, index=False, sheet_name="Daily Checklist Status")
    
    return send_file(file_path, as_attachment=True)

@app.route('/profile', methods=['GET', 'POST'])
@login_required()
def profile():
    db = read_db()
    user_index = next((index for (index, d) in enumerate(db['users']) if d["username"] == session['username']), None)

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        user = db['users'][user_index]

        if user['password_hash'] == current_password or check_password_hash(user['password_hash'], current_password):
            if new_password == confirm_password:
                db['users'][user_index]['password_hash'] = generate_password_hash(new_password)
                write_db(db)
                flash("Security key updated successfully!", "success")
            else:
                flash("New passwords do not match. Try again.", "danger")
        else:
            flash("Incorrect current password.", "danger")
            
        return redirect(url_for('profile'))

    return render_template('profile.html', user=db['users'][user_index])

@app.route('/users', methods=['GET', 'POST'])
@login_required(roles=['Administrator'])
def manage_users():
    db = read_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            new_username = request.form.get('username')
            new_role = request.form.get('role')
            new_password = request.form.get('password')
            
            if any(u['username'] == new_username for u in db['users']):
                flash(f"Username '{new_username}' already exists.", "danger")
            else:
                db['users'].append({
                    "username": new_username,
                    "role": new_role,
                    "password_hash": generate_password_hash(new_password)
                })
                write_db(db)
                flash(f"Personnel '{new_username}' added to the system.", "success")
                
        elif action == 'update':
            target_username = request.form.get('username')
            new_role = request.form.get('role')
            
            for u in db['users']:
                if u['username'] == target_username:
                    u['role'] = new_role
                    break
            write_db(db)
            flash(f"Clearance level updated for '{target_username}'.", "success")

        elif action == 'reset_password':
            target_username = request.form.get('username')
            new_password = request.form.get('new_password')
            
            for u in db['users']:
                if u['username'] == target_username:
                    u['password_hash'] = generate_password_hash(new_password)
                    break
            write_db(db)
            flash(f"Security key successfully reset for '{target_username}'.", "success")

        elif action == 'delete':
            target_username = request.form.get('username')
            
            if target_username == session['username']:
                flash("Security Error: You cannot terminate your own active session account.", "danger")
            else:
                db['users'] = [u for u in db['users'] if u['username'] != target_username]
                write_db(db)
                flash(f"Personnel '{target_username}' access revoked successfully.", "success")
                
        return redirect(url_for('manage_users'))

    return render_template('users.html', all_users=db['users'])

@app.route('/maintenance')
@login_required()
def maintenance():
    db = read_db()
    if "maintenance" not in db:
        db["maintenance"] = []
        write_db(db)
    return render_template("maintenance.html", schedules=db["maintenance"])

@app.route('/maintenance/add', methods=['POST'])
@login_required()
def add_maintenance():
    db = read_db()
    if "maintenance" not in db:
        db["maintenance"] = []
    next_id = 1
    if db["maintenance"]:
        next_id = max(item["id"] for item in db["maintenance"]) + 1
    db["maintenance"].append({
        "id": next_id,
        "device": request.form.get("device"),
        "activity": request.form.get("activity"),
        "date": request.form.get("date"),
        "assigned": request.form.get("assigned"),
        "status": request.form.get("status")
    })
    write_db(db)
    flash("Maintenance schedule added successfully.", "success")
    return redirect(url_for("maintenance"))

@app.route('/maintenance/edit', methods=['POST'])
@login_required()
def edit_maintenance():
    db = read_db()
    maintenance_id = int(request.form.get("id"))
    for item in db["maintenance"]:
        if item["id"] == maintenance_id:
            item["device"] = request.form.get("device")
            item["activity"] = request.form.get("activity")
            item["date"] = request.form.get("date")
            item["assigned"] = request.form.get("assigned")
            item["status"] = request.form.get("status")
            break
    write_db(db)
    flash("Maintenance updated successfully.", "success")
    return redirect(url_for("maintenance"))

@app.route('/maintenance/delete', methods=['POST'])
@login_required()
def delete_maintenance():
    db = read_db()
    maintenance_id = int(request.form.get("id"))
    db["maintenance"] = [item for item in db["maintenance"] if item["id"] != maintenance_id]
    write_db(db)
    flash("Maintenance schedule deleted successfully.", "success")
    return redirect(url_for("maintenance"))

# UNLOCKED for all users
@app.route("/notification-settings", methods=["GET", "POST"])
@login_required()
def notification_settings():
    db = read_db()
    if "notification_settings" not in db:
        db["notification_settings"] = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "from_address": "",
            "to_addresses": "",
            "subject": "CHECKLIST NOTIFICATION SYSTEM",
            "smtp_username": "",
            "smtp_password": "",
            "use_tls": True
        }
        write_db(db)

    settings = db["notification_settings"]
    settings.setdefault("smtp_username", "")
    settings.setdefault("smtp_password", "")
    settings.setdefault("use_tls", False)

    if request.method == "POST":
        
        # EVERYONE can update Sender and Recipient
        settings["from_address"] = request.form.get("from_address")
        settings["to_addresses"] = request.form.get("to_addresses")

        # ONLY Administrators can update core server details
        if session.get("role") == "Administrator":
            settings["smtp_server"] = request.form.get("smtp_server")
            settings["smtp_port"] = int(request.form.get("smtp_port"))
            settings["subject"] = request.form.get("subject")
            settings["smtp_username"] = request.form.get("smtp_username")
            settings["smtp_password"] = request.form.get("smtp_password")
            settings["use_tls"] = ("use_tls" in request.form)
            
        write_db(db)
        flash("Notification routing targets updated successfully.", "success")
        return redirect(url_for("notification_settings"))

    return render_template("notification_settings.html", settings=settings)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)