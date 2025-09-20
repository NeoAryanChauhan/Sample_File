from pymongo import MongoClient

def get_db():
    uri = "mongodb+srv://Lokesh:Lokesh%40123@clustersih.pt395cx.mongodb.net/?retryWrites=true&w=majority&appName=Clustersih"
    client = MongoClient(uri)
    db = client['traffic_simulation']
    return db