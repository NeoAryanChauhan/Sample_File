from pymongo import MongoClient

def get_db():
    # Replace <db_password> with your actual password
    uri = "mongodb+srv://Lokesh:<db_password>@clustersih.pt395cx.mongodb.net/?retryWrites=true&w=majority&appName=Clustersih"
    client = MongoClient(uri)
    db = client['traffic_simulation']  # You can change the database name
    return db