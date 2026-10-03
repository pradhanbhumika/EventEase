# EventEase – Event Ticket Booking System

EventEase is a web application for discovering events and booking tickets online. Users can browse events, choose seats on an interactive seat map, pay through a simulated checkout and receive a digital ticket with a QR code. Administrators can manage events and view bookings and revenue.

This project is an ASDD mini-project and is also used to demonstrate basic Git operations.

---

## Features

**Users**
- Responsive home page with search and categories
- Event listing with search, category filter and sorting
- Event details page with live countdown
- Registration and login (passwords are hashed)
- Interactive seat selection with live price calculation
- Checkout with simulated payment (Card, UPI, Net Banking)
- Booking confirmation with a unique booking ID
- Digital ticket with QR code (print or download)
- My Bookings page (upcoming and past)

**Administrators**
- Separate admin login
- Dashboard with revenue statistics
- Add, edit and delete events
- View and search all bookings

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3, Flask |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript (Jinja2 templates) |
| Security | Werkzeug password hashing, Flask sessions |
| QR codes | qrcode + Pillow |
| Version control | Git and GitHub |

---

## Project Structure

```
EventEase/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── templates/
│   ├── base.html, index.html, events.html, event_detail.html
│   ├── seats.html, checkout.html, confirmation.html
│   ├── ticket.html, verify.html, my_bookings.html
│   ├── login.html, register.html, error.html
│   └── admin_login.html, admin_dashboard.html,
│       admin_events.html, admin_event_form.html, admin_bookings.html
└── static/
    ├── css/   (style.css, enhancements.css)
    ├── js/    (script.js)
    └── images/
```

The database file `eventease.db` is not stored in Git. It is created automatically the first time the app runs.

---

## Installation (Windows PowerShell)

Requirements: Python 3.9 or newer, and Git.

```powershell
git clone https://github.com/<username>/EventEase.git
cd EventEase

python -m venv venv
venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

If PowerShell blocks the activation script, run this once in the same window and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## Running Locally

```powershell
python app.py
```

Open http://127.0.0.1:5000 in your browser.

On the first run the app creates the database, adds sample events and creates the admin account.

**Admin login:** http://127.0.0.1:5000/admin/login

| Email | Password |
|-------|----------|
| admin@eventease.com | admin123 |

**Test payment (no real money is charged)**

| Purpose | Value |
|---------|-------|
| Successful card | 4111 1111 1111 1111 |
| Declined card | 4000 0000 0000 0002 |
| Expiry / CVV | Any future date (e.g. 12/34) / any 3 digits |
| UPI | Any ID like name@bank |

To reset the data, stop the app, delete `eventease.db` and run `python app.py` again.

---

## Git Practical – Commands

**Check the version and configure Git**
```powershell
git --version
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global --list
```

**Create a repository, stage and commit**
```powershell
git init
git status
git add README.md
git commit -m "docs: add README for EventEase"
git log
git log --oneline
```

**Modify a file and save the change**
```powershell
git status
git diff
git add README.md
git commit -m "docs: update README"
```

**Branches**
```powershell
git branch                      # list branches
git branch feature-readme       # create a branch
git switch feature-readme       # switch to it
git switch main                 # switch back
git merge feature-readme        # merge into the current branch
git branch -d feature-readme    # delete the merged branch
git log --oneline --graph --all # view history of all branches
```

**GitHub: push and clone**
```powershell
git remote add origin https://github.com/<username>/EventEase.git
git branch -M main
git push -u origin main

git clone https://github.com/<username>/EventEase.git EventEase-clone
```

**Other useful commands**
```powershell
git restore <file>                 # discard changes in a file
git restore --staged <file>        # unstage a file
git show <commit-id>               # view one commit
git check-ignore -v eventease.db   # confirm a file is ignored
```

**Commit message style:** `feat:` new feature, `fix:` bug fix, `docs:` documentation, `style:` styling, `chore:` setup.

---

## Security Notes

- Passwords are hashed and never stored as plain text.
- All database queries use parameters to prevent SQL injection.
- Double booking of a seat is blocked by a database UNIQUE rule.
- Payments are simulated only. Never enter real card details.
- The admin credentials above are demo values for a college project.
## Author
Student: Bhumika Pradhan
