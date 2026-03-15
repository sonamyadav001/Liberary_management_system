import re
import datetime

def get_chatbot_response(message, db, user_id):
    msg = message.lower().strip()

    # Greetings
    if any(w in msg for w in ['hello','hi','hey','namaste','good morning','good evening']):
        return "🙏 Namaste! Welcome to Shabd Sangrah Library! I'm your library assistant. How can I help you today? You can ask me to find books, check availability, or view your issued books."

    # Help
    if any(w in msg for w in ['help','what can you do','features','commands']):
        return ("📚 I can help you with:\n\n"
                "• **Find books** – 'Find books on Python'\n"
                "• **Check availability** – 'Is Atomic Habits available?'\n"
                "• **My books** – 'What books do I have?'\n"
                "• **Category search** – 'Show me Technology books'\n"
                "• **Fine check** – 'Do I have any fines?'\n"
                "• **Popular books** – 'Most popular books'\n"
                "• **New arrivals** – 'Latest books'\n\n"
                "Just type your question naturally!")

    # My issued books
    if any(p in msg for p in ['my books','books issued to me','what books do i have','issued to me','my issued']):
        issued = db.execute('''SELECT b.title, b.author, t.due_date FROM transactions t
                               JOIN books b ON t.book_id=b.id
                               WHERE t.user_id=? AND t.return_date IS NULL''', (user_id,)).fetchall()
        if not issued:
            return "📖 You currently have no books issued. Browse our catalog to find interesting books!"
        today = datetime.date.today()
        resp = f"📚 You have **{len(issued)}** book(s) currently issued:\n\n"
        for i, t in enumerate(issued, 1):
            due = datetime.datetime.strptime(t['due_date'],'%Y-%m-%d').date()
            days_left = (due - today).days
            status = f"⚠️ {abs(days_left)} days overdue!" if days_left < 0 else f"✅ {days_left} days left"
            resp += f"{i}. **{t['title']}** by {t['author']}\n   Due: {t['due_date']} — {status}\n\n"
        return resp

    # Fine check
    if any(w in msg for w in ['fine','penalty','overdue amount','how much fine']):
        today = datetime.date.today()
        issued = db.execute('''SELECT t.*, b.title FROM transactions t JOIN books b ON t.book_id=b.id
                               WHERE t.user_id=? AND t.return_date IS NULL''', (user_id,)).fetchall()
        total_fine = 0
        for t in issued:
            due = datetime.datetime.strptime(t['due_date'],'%Y-%m-%d').date()
            days_late = max(0,(today-due).days)
            total_fine += days_late * 5
        if total_fine == 0:
            return "✅ Great news! You have no pending fines. All your books are within due date."
        return f"⚠️ You have a total pending fine of **₹{total_fine}**. Fine is ₹5 per late day. Please return overdue books soon!"

    # Popular books
    if any(w in msg for w in ['popular','most issued','trending','top books','best books']):
        books = db.execute('''SELECT b.title, b.author, COUNT(t.id) as cnt
                              FROM transactions t JOIN books b ON t.book_id=b.id
                              GROUP BY b.id ORDER BY cnt DESC LIMIT 5''').fetchall()
        if not books:
            return "📊 No borrowing data yet. Be the first to issue a book!"
        resp = "🌟 **Most Popular Books:**\n\n"
        for i, b in enumerate(books, 1):
            resp += f"{i}. **{b['title']}** by {b['author']} — Issued {b['cnt']} times\n"
        return resp

    # Latest/new books
    if any(w in msg for w in ['new','latest','recent','newly added','new arrivals']):
        books = db.execute('SELECT title, author, category FROM books ORDER BY id DESC LIMIT 5').fetchall()
        resp = "🆕 **Latest Books Added:**\n\n"
        for i, b in enumerate(books, 1):
            resp += f"{i}. **{b['title']}** by {b['author']} [{b['category']}]\n"
        return resp

    # Search books by category
    categories = ['technology', 'fiction', 'history', 'biography', 'self-help', 'business', 'literature', 'science', 'ai', 'python', 'data']
    cat_map = {'ai':'Technology', 'python':'Technology', 'data':'Technology',
               'tech':'Technology', 'technology':'Technology', 'fiction':'Fiction',
               'history':'History', 'biography':'Biography', 'self-help':'Self-Help',
               'self help':'Self-Help', 'business':'Business', 'literature':'Literature'}

    for cat_key in cat_map:
        if cat_key in msg and any(w in msg for w in ['show','find','search','get','list','available']):
            real_cat = cat_map[cat_key]
            keyword = cat_key if cat_key not in ['ai','python','data'] else None
            if keyword and cat_key in ['ai','python','data']:
                books = db.execute('''SELECT title, author, available FROM books
                                      WHERE title LIKE ? OR description LIKE ? ORDER BY title LIMIT 6''',
                                   (f'%{cat_key}%','%artificial%' if cat_key=='ai' else f'%{cat_key}%')).fetchall()
            else:
                books = db.execute('SELECT title, author, available FROM books WHERE category=? ORDER BY title LIMIT 6',
                                   (real_cat,)).fetchall()
            if not books:
                return f"😕 No books found for '{cat_key}'. Try browsing our full catalog."
            resp = f"📚 **Books on {cat_key.title()}:**\n\n"
            for b in books:
                avail = "✅ Available" if b['available'] > 0 else "❌ Not available"
                resp += f"• **{b['title']}** by {b['author']} — {avail}\n"
            return resp

    # Find/search books by keyword in title
    if any(w in msg for w in ['find','search','show','get','books on','about']):
        # Extract search term
        keywords_to_remove = ['find','search','show','get','books on','books about','me','on','about','a book on','book about','books']
        search_term = msg
        for k in keywords_to_remove:
            search_term = search_term.replace(k,'')
        search_term = search_term.strip()
        if len(search_term) >= 2:
            books = db.execute('''SELECT title, author, category, available FROM books
                                  WHERE title LIKE ? OR author LIKE ? OR description LIKE ?
                                  LIMIT 6''', (f'%{search_term}%',f'%{search_term}%',f'%{search_term}%')).fetchall()
            if books:
                resp = f"🔍 **Search results for '{search_term}':**\n\n"
                for b in books:
                    avail = "✅ Available" if b['available'] > 0 else "❌ Not available"
                    resp += f"• **{b['title']}** by {b['author']} [{b['category']}] — {avail}\n"
                return resp
            return f"😕 No books found matching '{search_term}'. Try a different search term or browse our catalog."

    # Availability check
    if any(w in msg for w in ['available','availability','can i get','is there']):
        # Try extracting book name from message
        words = msg.split()
        if len(words) > 2:
            search = ' '.join(words[2:]) if words[0] in ['is','are'] else msg
            books = db.execute('''SELECT title, author, available FROM books
                                  WHERE title LIKE ? LIMIT 3''', (f'%{search[:20]}%',)).fetchall()
            if books:
                resp = ""
                for b in books:
                    if b['available'] > 0:
                        resp += f"✅ **{b['title']}** by {b['author']} is available! ({b['available']} copies)\n"
                    else:
                        resp += f"❌ **{b['title']}** by {b['author']} is currently not available.\n"
                return resp

    # Library timing/info
    if any(w in msg for w in ['timing','hours','open','close','when','time']):
        return ("🕐 **Library Hours:**\n\n"
                "• Monday – Friday: 9:00 AM – 8:00 PM\n"
                "• Saturday: 10:00 AM – 6:00 PM\n"
                "• Sunday: 11:00 AM – 4:00 PM\n\n"
                "📦 Online delivery available 7 days a week!")

    # Delivery info
    if any(w in msg for w in ['delivery','deliver','home','online booking']):
        return ("🚚 **Home Delivery Service:**\n\n"
                "• Available within **5 km** radius\n"
                "• Charge: **₹5 per km**\n"
                "• Max delivery: 5 km (₹25 max charge)\n"
                "• Delivery time: 2–4 hours\n"
                "• Books returned via pickup or drop-off\n\n"
                "Visit the **Delivery** section to book!")

    # Fine policy
    if any(w in msg for w in ['rule','policy','how many days','loan period','borrow period']):
        return ("📋 **Library Policy:**\n\n"
                "• Loan period: **14 days**\n"
                "• Late fine: **₹5 per day**\n"
                "• Maximum books at once: **3 books**\n"
                "• Delivery available within **5 km**\n"
                "• Delivery charge: **₹5/km**")

    # Goodbye
    if any(w in msg for w in ['bye','goodbye','thanks','thank you','dhanyawad']):
        return "🙏 Thank you for using Shabd Sangrah! Happy Reading! 📚✨"

    # Default
    return ("🤔 I didn't quite understand that. Here are some things you can ask me:\n\n"
            "• 'Find books on Python'\n"
            "• 'Show Technology books'\n"
            "• 'What books do I have?'\n"
            "• 'Do I have any fines?'\n"
            "• 'Most popular books'\n"
            "• 'Delivery information'\n"
            "• 'Library hours'\n\n"
            "Type **help** for more options! 😊")
