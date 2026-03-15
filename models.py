import sqlite3, hashlib, datetime

DATABASE = 'library.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE,
            category TEXT DEFAULT 'General',
            pub_year TEXT,
            total_copies INTEGER DEFAULT 1,
            available INTEGER DEFAULT 1,
            description TEXT DEFAULT '',
            cover_color TEXT DEFAULT '#D47E30',
            avg_rating REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            fine REAL DEFAULT 0,
            FOREIGN KEY(book_id) REFERENCES books(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(book_id) REFERENCES books(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            address TEXT NOT NULL,
            distance REAL DEFAULT 1.0,
            charge REAL DEFAULT 5.0,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(book_id) REFERENCES books(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
    ''')
    conn.commit()

    # Seed admin
    admin_pass = hashlib.sha256('admin123'.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                  ('Admin', 'admin@shabdsangrah.com', admin_pass, 'admin'))
    except:
        pass

    # Seed demo user
    user_pass = hashlib.sha256('user123'.encode()).hexdigest()
    try:
        c.execute("INSERT INTO users (name,email,password,role,phone) VALUES (?,?,?,?,?)",
                  ('Arjun Sharma', 'arjun@example.com', user_pass, 'user', '9876543210'))
    except:
        pass

    # Seed books
    books_data = [
        ('Python Programming', 'Guido van Rossum', '978-0-13-110362-7', 'Technology', '2023', 5, '#D47E30',
         'The definitive guide to Python programming language. Covers basics to advanced topics.'),
        ('The Alchemist', 'Paulo Coelho', '978-0-06-112241-5', 'Fiction', '1988', 3, '#6F4E37',
         'A magical fable about following your dream. One of the best-selling books in history.'),
        ('Sapiens', 'Yuval Noah Harari', '978-0-06-231609-7', 'History', '2011', 4, '#845763',
         'A brief history of humankind exploring how Homo sapiens came to dominate Earth.'),
        ('Atomic Habits', 'James Clear', '978-0-7352-1115-1', 'Self-Help', '2018', 6, '#90C67F',
         'An easy and proven way to build good habits and break bad ones.'),
        ('Artificial Intelligence', 'Stuart Russell', '978-0-13-604259-4', 'Technology', '2020', 3, '#92E4BA',
         'A comprehensive introduction to AI. The bible of artificial intelligence.'),
        ('Wings of Fire', 'A.P.J. Abdul Kalam', '978-81-7371-146-6', 'Biography', '1999', 4, '#E491A6',
         'Autobiography of Dr. A.P.J. Abdul Kalam, the Missile Man of India.'),
        ('The God of Small Things', 'Arundhati Roy', '978-0-06-097749-0', 'Fiction', '1997', 2, '#6D3B07',
         'A story about the childhood experiences of fraternal twins in India.'),
        ('Data Science Handbook', 'Jake VanderPlas', '978-1-491-91205-8', 'Technology', '2022', 3, '#D47E30',
         'Essential tools for working with data in Python.'),
        ('Ikigai', 'Hector Garcia', '978-0-14-313780-3', 'Self-Help', '2017', 5, '#92E4BA',
         'The Japanese secret to a long and happy life.'),
        ('History of India', 'Romila Thapar', '978-0-14-014660-0', 'History', '2002', 2, '#6F4E37',
         'A comprehensive account of Indian history from ancient times.'),
        ('Deep Learning', 'Ian Goodfellow', '978-0-26-203561-3', 'Technology', '2016', 3, '#845763',
         'Comprehensive textbook on deep learning techniques and applications.'),
        ('One Hundred Years of Solitude', 'Gabriel García Márquez', '978-0-06-088328-7', 'Fiction', '1967', 2, '#E491A6',
         'A landmark of magical realism and world literature.'),
        ('The Lean Startup', 'Eric Ries', '978-0-307-88789-4', 'Business', '2011', 3, '#90C67F',
         'How today\'s entrepreneurs use continuous innovation to create successful businesses.'),
        ('Maths for Machine Learning', 'Marc Deisenroth', '978-1-108-47004-9', 'Technology', '2020', 2, '#D47E30',
         'The foundation of all machine learning algorithms explained mathematically.'),
        ('Ramayana', 'Valmiki', '978-0-14-044892-3', 'Literature', '500BCE', 3, '#6D3B07',
         'The ancient Indian epic depicting the journey of Lord Rama.'),
        ('Clean Code', 'Robert C. Martin', '978-0-13-235088-4', 'Technology', '2008', 4, '#845763',
         'A handbook of agile software craftsmanship for writing clean, maintainable code.'),
        ('Zero to One', 'Peter Thiel', '978-0-8041-3929-8', 'Business', '2014', 3, '#92E4BA',
         'Notes on startups, or how to build the future.'),
        ('The Secret', 'Rhonda Byrne', '978-1-58270-170-7', 'Self-Help', '2006', 4, '#E491A6',
         'The greatest secret of all — the law of attraction.'),
        ('Introduction to Algorithms', 'Thomas H. Cormen', '978-0-26-204630-5', 'Technology', '2009', 2, '#6F4E37',
         'The essential reference for algorithm design and analysis.'),
        ('Mahabharata', 'Vyasa', '978-0-14-044886-2', 'Literature', '400BCE', 3, '#90C67F',
         'The longest epic poem ever written, a treatise on dharma.'),
    ]

    for b in books_data:
        try:
            c.execute('''INSERT INTO books (title,author,isbn,category,pub_year,total_copies,available,cover_color,description)
                         VALUES (?,?,?,?,?,?,?,?,?)''',
                      (b[0],b[1],b[2],b[3],b[4],b[5],b[5],b[6],b[7]))
        except:
            pass

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()
