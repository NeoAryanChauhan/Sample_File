from pymongo import MongoClient

def get_db():
    # Replace <db_password> with your actual password
    uri = "mongodb+srv://Lokesh:YOUR_PASSWORD_HERE@clustersih.pt395cx.mongodb.net/?retryWrites=true&w=majority&appName=Clustersih"
    client = MongoClient(uri)
    db = client['traffic_simulation']
    return db