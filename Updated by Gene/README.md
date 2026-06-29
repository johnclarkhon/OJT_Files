# Web-Based Network Operations Checklist and Notification System

## Project Overview

This project is a web-based application developed as part of our On-the-Job Training (OJT). It is designed to help IT Infrastructure teams perform and monitor daily network operation tasks through a centralized system instead of using spreadsheets and email updates.

The system simulates the workflow of a Network Operations Center (NOC) by allowing users to complete daily network checklists, monitor device status, receive notifications, and generate operational reports.

---

## Features

- User Authentication
  - Administrator
  - Network Engineer
  - OJT User
  - Viewer

- Daily Network Checklist
  - Internet Connectivity Check
  - Firewall Health Check
  - Switch Uptime Verification
  - Server Availability
  - UPS Monitoring
  - Wi-Fi Validation
  - CCTV Monitoring
  - Backup Verification
  - Security Log Review
  - Documentation Updates

- Device Monitoring
  - Ping network devices
  - Online/Offline status
  - Device health monitoring

- Notifications
  - Daily checklist reminders
  - Missed activity alerts
  - Device failure notifications

- Dashboard
  - Checklist completion rate
  - Device status overview
  - Open incidents
  - Critical alerts

- Reports
  - Daily Operations Report
  - Monthly Compliance Report
  - Export to PDF
  - Export to Excel

---

## Technologies Used

### Backend
- Python
- Flask

### Frontend
- HTML
- Bootstrap 5
- JavaScript

### Database
- JSON

### Python Libraries
- ping3
- pandas
- openpyxl
- schedule
- Flask

---

## Installation

1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/web-based-network-operations-checklist.git
```

2. Open the project folder

```bash
cd web-based-network-operations-checklist
```

3. Install the required packages

```bash
pip install -r requirements.txt
```

4. Run the application

```bash
python app.py
```

---

## Project Structure

```
app.py
database/
modules/
static/
templates/
uploads/
requirements.txt
README.md
```

---

## Future Improvements

- Microsoft Teams notifications
- Telegram Bot integration
- QR Code Attendance
- AI-based troubleshooting recommendations
- Maintenance Calendar

---

## Developers

OJT Team

Panasonic Manufacturing Philippines Corporation
