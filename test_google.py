from googlesearch import search
try:
    results = search("Restaurante El Celler de Can Roca Girona", num_results=5, sleep_interval=2)
    for res in results:
        print(res)
except Exception as e:
    print("Error:", e)
