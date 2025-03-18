from collections import deque

class Interseccion:

    def __init__(self, id, semaforos, conexiones=None, nombre='', coordenadas=None):
        self.id = id
        self.semaforos = semaforos  # Lista de semáforos en esta intersección
        self.conexiones = conexiones if conexiones else []  # Conexiones a otras intersecciones
        self.cola_vehiculos = {s.id: deque() for s in semaforos}  # Colas de vehículos por dirección
        self.nombre = nombre
        self.coordenadas = coordenadas
    
    def __str__(self):
        return f"Intersección {self.id}: {len(self.semaforos)} semáforos, {len(self.conexiones)} conexiones"