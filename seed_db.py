from app import app, db, User  # Adjust the import to match your app's structure

with app.app_context():
    db.create_all()  # Ensures database and tables are created

    # Add initial users
    initial_users = [
        User(username='erten', password='lozinka'),
        User(username='admin', password='adminpass'),
        User(username='user1', password='userpass1'),
        User(username='user2', password='userpass2')
    ]
    db.session.add_all(initial_users)
    db.session.commit()
    print("Initial users added to the database.")
