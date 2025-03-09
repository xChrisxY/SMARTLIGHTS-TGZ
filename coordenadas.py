import osmnx as ox
import json
import random

# Configurar el nombre de la ciudad y las coordenadas del punto central
city_name = "Tuxtla Gutiérrez, Chiapas, México"
center_point = (16.7602, -93.1193)  # Coordenadas del centro del área de interés
buffer_distance = 200  # Reducir el radio en metros alrededor del punto central (de 500 a 200)

# Descargar el grafo de calles delimitado por un punto central y un radio
print("Descargando grafo de calles en el área delimitada...")
G = ox.graph_from_point(center_point, dist=buffer_distance, network_type="drive")

# Extraer nodos e intersecciones de la subregión
print("Extrayendo intersecciones en el área delimitada...")
intersections = ox.graph_to_gdfs(G, nodes=True, edges=False)

# Reducir el número de intersecciones (por ejemplo, tomar solo las primeras 20)
intersections = intersections.head(20)

# Generar intersecciones ficticias
print("Generando intersecciones ficticias...")
intersecciones = []
id_counter = 1
for index, row in intersections.iterrows():
    coords = {"lat": row["y"], "lng": row["x"]}
    intersecciones.append({
        "id": id_counter,
        "nombre": f"Intersección {id_counter}",
        "coordenadas": coords,
        "semaforos": [],
        "conexiones": list(G.neighbors(index))  # Conexiones a otras intersecciones
    })
    id_counter += 1

# Generar semáforos ficticios (limitar el número de semáforos por intersección)
print("Generando semáforos ficticios...")
semaforos = []
semaforo_id = 1
for interseccion in intersecciones:
    # Crear semáforos ficticios para cada intersección (máximo 2 semáforos por intersección)
    num_semaforos = random.randint(1, 2)
    for _ in range(num_semaforos):
        semaforos.append({
            "id": semaforo_id,
            "direccion": random.choice(["Norte-Sur", "Este-Oeste", "Sur-Norte", "Oeste-Este"]),
            "tiempo_verde_inicial": random.randint(20, 60),  # Tiempo verde entre 20 y 60 segundos
            "tiempo_amarillo_inicial": random.randint(3, 5),  # Tiempo amarillo entre 3 y 5 segundos
            "tiempo_rojo_inicial": random.randint(20, 60)  # Tiempo rojo entre 20 y 60 segundos
        })
        semaforo_id += 1

# Asignar semáforos a las intersecciones
print("Asignando semáforos a las intersecciones...")
for interseccion in intersecciones:
    num_semaforos = random.randint(1, 2)  # Cada intersección tendrá entre 1 y 2 semáforos
    for _ in range(num_semaforos):
        semaforo = random.choice(semaforos)
        interseccion["semaforos"].append(semaforo)

# Generar calles ficticias (limitar el número de calles)
print("Generando calles ficticias...")
calles = []
calles_id = 1
for i in range(len(intersecciones) - 1):
    # Limitar el número de calles entre intersecciones
    if calles_id > 10:  # Limitar a 10 calles
        break
    calle = {
        "id": calles_id,
        "nombre": f"Calle {calles_id}",
        "desde_interseccion": intersecciones[i]["id"],
        "hasta_interseccion": intersecciones[i + 1]["id"],
        "longitud": random.randint(300, 800),  # Longitud de la calle entre 300 y 800 metros
        "velocidad_max": random.choice([40, 50, 60]),  # Velocidad máxima aleatoria
        "carriles": random.randint(2, 3),  # Número de carriles entre 2 y 3
        "bidireccional": random.choice([True, False]),  # Calle bidireccional aleatoria
        "flujo_promedio": {
            "mañana": random.randint(200, 400),
            "tarde": random.randint(150, 300),
            "noche": random.randint(50, 150)
        }
    }
    calles.append(calle)
    calles_id += 1

# Crear el JSON final
ciudad_data = {
    "intersecciones": intersecciones,
    "calles": calles
}

# Guardar el JSON
output_file = "zona_delimitada.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(ciudad_data, f, indent=4, ensure_ascii=False)

print(f"Archivo generado: {output_file}")
