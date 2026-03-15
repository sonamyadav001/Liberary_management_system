from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
import sqlite3, os, hashlib, datetime, qrcode, io, base64, json, math
from email_utils import send_email_notification
from chatbot import get_chatbot_response

app = Flask(__name__)
app.secret_key = 'shabdsangrah_secret_key_2024'
DATABASE = 'library.db'
FINE_PER_DAY = 5
LOAN_DAYS = 14
DELIVERY_CHARGE_PER_KM = 5
MAX_DELIVERY_KM = 5

# ─── DB HELPER ───────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# ─── AUTH DECORATORS ─────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ─── QR CODE GENERATOR ───────────────────────────────────────────────────────
def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#6D3B07", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')

# ─── ROUTES: AUTH ─────────────────────────────────────────────────────────────
@app.route('/')
def index():
    db = get_db()
    books = db.execute('SELECT * FROM books ORDER BY RANDOM() LIMIT 8').fetchall()
    stats = {
        'total_books': db.execute('SELECT COUNT(*) FROM books').fetchone()[0],
        'total_users': db.execute('SELECT COUNT(*) FROM users WHERE role="user"').fetchone()[0],
        'issued_books': db.execute('SELECT COUNT(*) FROM transactions WHERE return_date IS NULL').fetchone()[0],
    }
    db.close()
    return render_template('index.html', books=books, stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email=? AND password=?', (email, password)).fetchone()
        db.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['name']
            session['role'] = user['role']
            session['email'] = user['email']
            flash(f'Welcome back, {user["name"]}!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('user_dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        phone = request.form.get('phone','')
        address = request.form.get('address','')
        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        if existing:
            flash('Email already registered.', 'danger')
            db.close()
            return render_template('register.html')
        db.execute('INSERT INTO users (name,email,password,phone,address,role) VALUES (?,?,?,?,?,?)',
                   (name, email, password, phone, address, 'user'))
        db.commit()
        db.close()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

# ─── USER DASHBOARD ──────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def user_dashboard():
    db = get_db()
    user_id = session['user_id']
    issued = db.execute('''SELECT t.*, b.title, b.author, b.category, b.cover_color
                           FROM transactions t JOIN books b ON t.book_id=b.id
                           WHERE t.user_id=? AND t.return_date IS NULL
                           ORDER BY t.issue_date DESC''', (user_id,)).fetchall()
    history = db.execute('''SELECT t.*, b.title, b.author
                            FROM transactions t JOIN books b ON t.book_id=b.id
                            WHERE t.user_id=? AND t.return_date IS NOT NULL
                            ORDER BY t.return_date DESC LIMIT 5''', (user_id,)).fetchall()
    deliveries = db.execute('''SELECT d.*, b.title FROM deliveries d JOIN books b ON d.book_id=b.id
                               WHERE d.user_id=? ORDER BY d.created_at DESC LIMIT 5''', (user_id,)).fetchall()
    today = datetime.date.today()
    # Calculate fines
    issued_with_fine = []
    for t in issued:
        t = dict(t)
        due = datetime.datetime.strptime(t['due_date'], '%Y-%m-%d').date()
        days_late = max(0, (today - due).days)
        t['fine'] = days_late * FINE_PER_DAY
        t['days_late'] = days_late
        issued_with_fine.append(t)
    db.close()
    return render_template('dashboard_user.html', issued=issued_with_fine, history=history, deliveries=deliveries)

# ─── ADMIN DASHBOARD ─────────────────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    total_books = db.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    available_books = db.execute('SELECT COUNT(*) FROM books WHERE available>0').fetchone()[0]
    issued_books = db.execute('SELECT COUNT(*) FROM transactions WHERE return_date IS NULL').fetchone()[0]
    total_users = db.execute('SELECT COUNT(*) FROM users WHERE role="user"').fetchone()[0]
    total_fines = db.execute('SELECT SUM(fine) FROM transactions WHERE fine>0').fetchone()[0] or 0
    pending_deliveries = db.execute('SELECT COUNT(*) FROM deliveries WHERE status="pending"').fetchone()[0]
    recent_transactions = db.execute('''SELECT t.*, b.title, u.name as uname
                                       FROM transactions t JOIN books b ON t.book_id=b.id
                                       JOIN users u ON t.user_id=u.id
                                       ORDER BY t.issue_date DESC LIMIT 10''').fetchall()
    today = datetime.date.today()
    overdue = []
    for t in recent_transactions:
        t = dict(t)
        if not t['return_date']:
            due = datetime.datetime.strptime(t['due_date'],'%Y-%m-%d').date()
            t['days_late'] = max(0,(today-due).days)
        else:
            t['days_late'] = 0
        overdue.append(t)
    # Category stats
    cat_stats = db.execute('SELECT category, COUNT(*) as cnt FROM books GROUP BY category').fetchall()
    # Monthly issues
    monthly = db.execute('''SELECT strftime('%Y-%m', issue_date) as month, COUNT(*) as cnt
                            FROM transactions GROUP BY month ORDER BY month DESC LIMIT 6''').fetchall()
    popular = db.execute('''SELECT b.title, b.author, COUNT(t.id) as issue_count
                           FROM transactions t JOIN books b ON t.book_id=b.id
                           GROUP BY b.id ORDER BY issue_count DESC LIMIT 5''').fetchall()
    db.close()
    return render_template('dashboard_admin.html',
        total_books=total_books, available_books=available_books,
        issued_books=issued_books, total_users=total_users,
        total_fines=total_fines, pending_deliveries=pending_deliveries,
        recent_transactions=overdue, cat_stats=cat_stats,
        monthly=monthly, popular=popular)

# ─── BOOKS ───────────────────────────────────────────────────────────────────
@app.route('/books')
def books():
    search = request.args.get('q','')
    category = request.args.get('category','')
    year = request.args.get('year','')
    sort = request.args.get('sort','title')
    db = get_db()
    query = 'SELECT * FROM books WHERE 1=1'
    params = []
    if search:
        query += ' AND (title LIKE ? OR author LIKE ? OR isbn LIKE ?)'
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if category:
        query += ' AND category=?'
        params.append(category)
    if year:
        query += ' AND pub_year=?'
        params.append(year)
    sort_map = {'title':'title','author':'author','year':'pub_year DESC','rating':'avg_rating DESC'}
    query += f' ORDER BY {sort_map.get(sort,"title")}'
    books_list = db.execute(query, params).fetchall()
    categories = db.execute('SELECT DISTINCT category FROM books ORDER BY category').fetchall()
    years = db.execute('SELECT DISTINCT pub_year FROM books WHERE pub_year IS NOT NULL ORDER BY pub_year DESC').fetchall()
    db.close()
    return render_template('books.html', books=books_list, categories=categories,
                           years=years, search=search, selected_cat=category,
                           selected_year=year, sort=sort)

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
    if not book:
        flash('Book not found.', 'danger')
        return redirect(url_for('books'))
    reviews = db.execute('''SELECT r.*, u.name FROM reviews r JOIN users u ON r.user_id=u.id
                            WHERE r.book_id=? ORDER BY r.created_at DESC''', (book_id,)).fetchall()
    user_review = None
    user_transaction = None
    if 'user_id' in session:
        user_review = db.execute('SELECT * FROM reviews WHERE book_id=? AND user_id=?',
                                 (book_id, session['user_id'])).fetchone()
        user_transaction = db.execute('''SELECT * FROM transactions WHERE book_id=? AND user_id=? AND return_date IS NULL''',
                                       (book_id, session['user_id'])).fetchone()
    qr_data = generate_qr(f"https://lib-cm7k.onrender.com/book/{book_id}")
    db.close()
    return render_template('book_detail.html', book=book, reviews=reviews,
                           user_review=user_review, user_transaction=user_transaction, qr_data=qr_data)

# ─── ISSUE & RETURN ──────────────────────────────────────────────────────────
@app.route('/issue/<int:book_id>', methods=['POST'])
@login_required
def issue_book(book_id):
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
    if not book or book['available'] <= 0:
        flash('Book not available for issue.', 'danger')
        db.close()
        return redirect(url_for('book_detail', book_id=book_id))
    existing = db.execute('SELECT * FROM transactions WHERE book_id=? AND user_id=? AND return_date IS NULL',
                          (book_id, session['user_id'])).fetchone()
    if existing:
        flash('You already have this book issued.', 'warning')
        db.close()
        return redirect(url_for('book_detail', book_id=book_id))
    issue_date = datetime.date.today()
    due_date = issue_date + datetime.timedelta(days=LOAN_DAYS)
    db.execute('INSERT INTO transactions (book_id,user_id,issue_date,due_date) VALUES (?,?,?,?)',
               (book_id, session['user_id'], str(issue_date), str(due_date)))
    db.execute('UPDATE books SET available=available-1 WHERE id=?', (book_id,))
    db.commit()
    # Send notification
    send_email_notification(session['email'], 'Book Issued - Shabd Sangrah',
        f'Your book "{book["title"]}" has been issued. Due date: {due_date}')
    db.close()
    flash(f'Book "{book["title"]}" issued successfully! Due date: {due_date}', 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/return/<int:transaction_id>', methods=['POST'])
@login_required
def return_book(transaction_id):
    db = get_db()
    trans = db.execute('SELECT t.*, b.title FROM transactions t JOIN books b ON t.book_id=b.id WHERE t.id=? AND t.user_id=?',
                       (transaction_id, session['user_id'])).fetchone()
    if not trans:
        flash('Transaction not found.', 'danger')
        db.close()
        return redirect(url_for('user_dashboard'))
    today = datetime.date.today()
    due = datetime.datetime.strptime(trans['due_date'],'%Y-%m-%d').date()
    days_late = max(0, (today - due).days)
    fine = days_late * FINE_PER_DAY
    db.execute('UPDATE transactions SET return_date=?, fine=? WHERE id=?',
               (str(today), fine, transaction_id))
    db.execute('UPDATE books SET available=available+1 WHERE id=?', (trans['book_id'],))
    db.commit()
    db.close()
    msg = f'Book returned successfully!'
    if fine > 0:
        msg += f' Fine of ₹{fine} charged for {days_late} late day(s).'
    flash(msg, 'success' if fine == 0 else 'warning')
    return redirect(url_for('user_dashboard'))

# ─── ADMIN: BOOK MANAGEMENT ──────────────────────────────────────────────────
@app.route('/admin/books')
@admin_required
def admin_books():
    db = get_db()
    books_list = db.execute('SELECT * FROM books ORDER BY title').fetchall()
    db.close()
    return render_template('admin_books.html', books=books_list)

@app.route('/admin/books/add', methods=['GET','POST'])
@admin_required
def add_book():
    if request.method == 'POST':
        data = {k: request.form.get(k,'') for k in ['title','author','isbn','category','pub_year','total_copies','description','cover_color']}
        total = int(data['total_copies'] or 1)
        db = get_db()
        db.execute('''INSERT INTO books (title,author,isbn,category,pub_year,total_copies,available,description,cover_color)
                      VALUES (?,?,?,?,?,?,?,?,?)''',
                   (data['title'],data['author'],data['isbn'],data['category'],
                    data['pub_year'],total,total,data['description'],data['cover_color'] or '#D47E30'))
        db.commit()
        db.close()
        flash('Book added successfully!', 'success')
        return redirect(url_for('admin_books'))
    return render_template('add_book.html')

@app.route('/admin/books/edit/<int:book_id>', methods=['GET','POST'])
@admin_required
def edit_book(book_id):
    db = get_db()
    book = db.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
    if request.method == 'POST':
        data = {k: request.form.get(k,'') for k in ['title','author','isbn','category','pub_year','total_copies','description','cover_color']}
        total = int(data['total_copies'] or 1)
        issued = db.execute('SELECT COUNT(*) FROM transactions WHERE book_id=? AND return_date IS NULL',(book_id,)).fetchone()[0]
        available = max(0, total - issued)
        db.execute('''UPDATE books SET title=?,author=?,isbn=?,category=?,pub_year=?,
                      total_copies=?,available=?,description=?,cover_color=? WHERE id=?''',
                   (data['title'],data['author'],data['isbn'],data['category'],
                    data['pub_year'],total,available,data['description'],data['cover_color'],book_id))
        db.commit()
        db.close()
        flash('Book updated!', 'success')
        return redirect(url_for('admin_books'))
    db.close()
    return render_template('edit_book.html', book=book)

@app.route('/admin/books/delete/<int:book_id>', methods=['POST'])
@admin_required
def delete_book(book_id):
    db = get_db()
    db.execute('DELETE FROM books WHERE id=?', (book_id,))
    db.execute('DELETE FROM transactions WHERE book_id=?', (book_id,))
    db.commit()
    db.close()
    flash('Book deleted.', 'info')
    return redirect(url_for('admin_books'))

# ─── ADMIN: USER MANAGEMENT ──────────────────────────────────────────────────
@app.route('/admin/users')
@admin_required
def admin_users():
    db = get_db()
    users = db.execute('''SELECT u.*, COUNT(t.id) as issued_count
                          FROM users u LEFT JOIN transactions t ON u.id=t.user_id AND t.return_date IS NULL
                          WHERE u.role="user" GROUP BY u.id ORDER BY u.name''').fetchall()
    db.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    db = get_db()
    db.execute('DELETE FROM users WHERE id=?', (user_id,))
    db.commit()
    db.close()
    flash('User removed.', 'info')
    return redirect(url_for('admin_users'))

# ─── ADMIN: REPORTS ──────────────────────────────────────────────────────────
@app.route('/admin/reports')
@admin_required
def admin_reports():
    db = get_db()
    today = datetime.date.today()
    overdue_trans = db.execute('''SELECT t.*, b.title, u.name as uname, u.email
                                  FROM transactions t JOIN books b ON t.book_id=b.id
                                  JOIN users u ON t.user_id=u.id
                                  WHERE t.return_date IS NULL AND t.due_date < ?
                                  ORDER BY t.due_date''', (str(today),)).fetchall()
    overdue_list = []
    for t in overdue_trans:
        t = dict(t)
        due = datetime.datetime.strptime(t['due_date'],'%Y-%m-%d').date()
        t['days_late'] = (today - due).days
        t['fine'] = t['days_late'] * FINE_PER_DAY
        overdue_list.append(t)
    total_fines = sum(t['fine'] for t in overdue_list)
    db.close()
    return render_template('admin_reports.html', overdue=overdue_list, total_fines=total_fines)

# ─── REVIEWS ─────────────────────────────────────────────────────────────────
@app.route('/review/<int:book_id>', methods=['POST'])
@login_required
def add_review(book_id):
    rating = int(request.form.get('rating', 5))
    comment = request.form.get('comment','').strip()
    db = get_db()
    existing = db.execute('SELECT id FROM reviews WHERE book_id=? AND user_id=?',
                          (book_id, session['user_id'])).fetchone()
    if existing:
        db.execute('UPDATE reviews SET rating=?, comment=?, created_at=? WHERE id=?',
                   (rating, comment, str(datetime.datetime.now()), existing['id']))
    else:
        db.execute('INSERT INTO reviews (book_id,user_id,rating,comment,created_at) VALUES (?,?,?,?,?)',
                   (book_id, session['user_id'], rating, comment, str(datetime.datetime.now())))
    avg = db.execute('SELECT AVG(rating) FROM reviews WHERE book_id=?', (book_id,)).fetchone()[0]
    db.execute('UPDATE books SET avg_rating=? WHERE id=?', (round(avg,1), book_id))
    db.commit()
    db.close()
    flash('Review submitted!', 'success')
    return redirect(url_for('book_detail', book_id=book_id))

# ─── DELIVERY ────────────────────────────────────────────────────────────────
@app.route('/delivery', methods=['GET','POST'])
@login_required
def delivery():
    db = get_db()
    if request.method == 'POST':
        book_id = int(request.form['book_id'])
        address = request.form['address'].strip()
        distance = float(request.form.get('distance', 1))
        if distance > MAX_DELIVERY_KM:
            flash(f'Delivery only available within {MAX_DELIVERY_KM} km radius.', 'danger')
            return redirect(url_for('delivery'))
        charge = round(distance * DELIVERY_CHARGE_PER_KM, 2)
        book = db.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
        if not book or book['available'] <= 0:
            flash('Book not available for delivery.', 'danger')
            return redirect(url_for('delivery'))
        issue_date = datetime.date.today()
        due_date = issue_date + datetime.timedelta(days=LOAN_DAYS)
        db.execute('INSERT INTO transactions (book_id,user_id,issue_date,due_date) VALUES (?,?,?,?)',
                   (book_id, session['user_id'], str(issue_date), str(due_date)))
        db.execute('UPDATE books SET available=available-1 WHERE id=?', (book_id,))
        db.execute('''INSERT INTO deliveries (book_id,user_id,address,distance,charge,status,created_at)
                      VALUES (?,?,?,?,?,"pending",?)''',
                   (book_id, session['user_id'], address, distance, charge, str(datetime.datetime.now())))
        db.commit()
        send_email_notification(session['email'], 'Delivery Booked - Shabd Sangrah',
            f'Book "{book["title"]}" delivery booked! Charge: ₹{charge}. ETA: 2-4 hours.')
        flash(f'Delivery booked! Charge: ₹{charge} for {distance} km. Book will arrive within 4 hours.', 'success')
        db.close()
        return redirect(url_for('user_dashboard'))
    available_books = db.execute('SELECT * FROM books WHERE available>0 ORDER BY title').fetchall()
    my_deliveries = db.execute('''SELECT d.*, b.title FROM deliveries d JOIN books b ON d.book_id=b.id
                                  WHERE d.user_id=? ORDER BY d.created_at DESC''', (session['user_id'],)).fetchall()
    db.close()
    return render_template('delivery.html', books=available_books, deliveries=my_deliveries,
                           max_km=MAX_DELIVERY_KM, charge_per_km=DELIVERY_CHARGE_PER_KM)

@app.route('/admin/deliveries')
@admin_required
def admin_deliveries():
    db = get_db()
    deliveries = db.execute('''SELECT d.*, b.title, u.name as uname, u.email
                               FROM deliveries d JOIN books b ON d.book_id=b.id
                               JOIN users u ON d.user_id=u.id ORDER BY d.created_at DESC''').fetchall()
    db.close()
    return render_template('admin_deliveries.html', deliveries=deliveries)

@app.route('/admin/deliveries/update/<int:did>', methods=['POST'])
@admin_required
def update_delivery(did):
    status = request.form['status']
    db = get_db()
    db.execute('UPDATE deliveries SET status=? WHERE id=?', (status, did))
    db.commit()
    db.close()
    flash('Delivery status updated.', 'success')
    return redirect(url_for('admin_deliveries'))

# ─── CHATBOT ─────────────────────────────────────────────────────────────────
@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    message = request.json.get('message','')
    db = get_db()
    response = get_chatbot_response(message, db, session['user_id'])
    db.close()
    return jsonify({'response': response})

# ─── API: Search (AJAX) ──────────────────────────────────────────────────────
@app.route('/api/books/search')
def api_search():
    q = request.args.get('q','')
    db = get_db()
    results = db.execute('''SELECT id,title,author,category,available,avg_rating FROM books
                            WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ?
                            LIMIT 8''', (f'%{q}%',f'%{q}%',f'%{q}%')).fetchall()
    db.close()
    return jsonify([dict(r) for r in results])

# ─── PROFILE ──────────────────────────────────────────────────────────────────
@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    db = get_db()
    if request.method == 'POST':
        name = request.form['name'].strip()
        phone = request.form.get('phone','')
        address = request.form.get('address','')
        db.execute('UPDATE users SET name=?,phone=?,address=? WHERE id=?',
                   (name, phone, address, session['user_id']))
        db.commit()
        session['username'] = name
        flash('Profile updated!', 'success')
    user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    history = db.execute('''SELECT t.*, b.title FROM transactions t JOIN books b ON t.book_id=b.id
                            WHERE t.user_id=? ORDER BY t.issue_date DESC''', (session['user_id'],)).fetchall()
    db.close()
    return render_template('profile.html', user=user, history=history)

if __name__ == '__main__':
    from models import init_db
    init_db()
    app.run(debug=True, port=5000)
