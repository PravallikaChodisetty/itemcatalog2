from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime
from database_setup import *

engine = create_engine('sqlite:///catalog.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Delete Categories if exisitng.
session.query(Genre).delete()
# Delete Items if exisitng.
session.query(Books).delete()
# Delete Users if exisitng.
session.query(User).delete()

# Create sample users
User1 = User(name="Rohini Pravallika",
             email="rohini.chodisetty@gmail.com",
             picture="static/images/dp.jpg")
session.add(User1)
session.commit()


# Create sample categories
Genre1 = Genre(name="Mythology", user_id=1)
session.add(Genre1)
session.commit()

Genre2 = Genre(name="Thriller", user_id=1)
session.add(Genre2)
session.commit

Genre3 = Genre(name="Romance", user_id=1)
session.add(Genre3)
session.commit()

Genre4 = Genre(name="Science-fiction", user_id=1)
session.add(Genre4)
session.commit()

Genre5 = Genre(name="Fantasy", user_id=1)
session.add(Genre5)
session.commit()

# Populate the genres with books
Book1 = Books(name="Scion Of Ikshvaku",
              date=datetime.datetime.now(),
              description="A mythological and historical jewel"
              "\nauthor: Amish Tripathi",
              picture="""https://encrypted-tbn0.gstatic.com/
              images?q=tbn:ANd9GcTnW1C17TfzLzrZDyBToVlPVkv
              7Or47_Be9Up2Dk_VH2_VSSPX3-g""",
              genre_id=1,
              user_id=1)
session.add(Book1)
session.commit()

Book2 = Books(name="Sorceres Ring ",
              date=datetime.datetime.now(),
              description="A royal fantasy novel"
              "\nauthor: Morgan Rice",
              picture="""https://encrypted-tbn0.gstatic.com/
              images?q=tbn:ANd9GcTgGPNBr1iSaxidQdA_APK4YB9o
              KPoyRqzBjdqcY3Pp9iaCd4fg""",
              genre_id=5,
              user_id=1)
session.add(Book2)
session.commit()

Book3 = Books(name="Harappa Curse Of blood river ",
              date=datetime.datetime.now(),
              description="A historical thriller novel"
              "\nauthor:Vineeth Bajpai",
              picture="""https://encrypted-tbn0.gstatic.com/
              images?q=tbn:ANd9GcSPzDK1-u0GaUAOM4-5tRji1eB9
              nPy0Z2E7XvRil5d-uwdf4WEKoQ""",
              genre_id=2,
              user_id=1)
session.add(Book3)
session.commit()

Book4 = Books(name="Digital Fortress ",
              date=datetime.datetime.now(),
              description="A scientific thriller"
              "\nauthor:DanBrown",
              picture="""https://encrypted-tbn0.gstatic.com/
              images?q=tbn:ANd9GcSS5E9ah5obVB02m89jfFkSU0eH
              jBDmi3U4PiQhdYdFTaLfQQoRcg""",
              genre_id=4,
              user_id=1)
session.add(Book4)
session.commit()

Book5 = Books(name="2 states ",
              date=datetime.datetime.now(),
              description="A indian love story"
              "\nauthor:Chetan Bhagath",
              picture="""https://encrypted-tbn0.gstatic.com/
              images?q=tbn:ANd9GcTC-ApeEZ4Nx1LQRLiZ2gtvamj
              jKNIQ67QEpiGvj9NFXJNhWL0e""",
              genre_id=3,
              user_id=1)
session.add(Book5)
session.commit()

print("Your database has been populated with sample data!")
