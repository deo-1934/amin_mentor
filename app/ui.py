from retriever import retrieve
from generator import generate_response
import os

def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.readlines()

def chat_loop():
    data_dir = 'data/'
    data_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.txt')]
    data = []
    for file_path in data_files:
        data.extend(load_data(file_path))

    print("منتور شخصی شما آماده است! برای خروج، 'exit' را تایپ کنید.")

    while True:
        query = input("شما: ")
        if query.lower() == 'exit':
            break
        indices, distances = retrieve(query)
        retrieved_data = [data[i] for i in indices]
        response = generate_response(query, retrieved_data)
        print("منتور:", response)

if __name__ == "__main__":
    chat_loop()
