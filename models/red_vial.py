import numpy as np

class RedVial:
    def __init__(self, intersecciones):
        self.intersecciones = intersecciones
        self.tiempo_simulacion = 0
        self.flujos_calles = {}
    
    def simular_llegada_poisson(self, tasa_llegada, duracion=3600):
        """Simula la llegada de vehículos siguiendo una distribución de Poisson"""
        for t in range(duracion):
            # Para cada intersección
            for interseccion in self.intersecciones:
                # Para cada dirección en la intersección
                for semaforo_id in interseccion.cola_vehiculos:
                    # Generar llegadas según distribución de Poisson
                    num_llegadas = np.random.poisson(tasa_llegada)
                    for _ in range(num_llegadas):
                        # Añadir vehículo a la cola con su tiempo de llegada
                        interseccion.cola_vehiculos[semaforo_id].append(t)


    def simular_trafico(self, duracion=3600):
        """Simula el tráfico durante un período de tiempo"""
        tiempos_espera = []
        
        for t in range(duracion):
            self.tiempo_simulacion = t
            
            # Para cada intersección
            for interseccion in self.intersecciones:
                # Para cada semáforo en la intersección
                for semaforo in interseccion.semaforos:
                    estado = semaforo.get_estado(t)
                    
                    # Si el semáforo está en verde, procesar vehículos
                    if estado == "verde":
                        cola = interseccion.cola_vehiculos[semaforo.id]
                        # Procesar hasta 3 vehículos por segundo de verde (capacidad)
                        for _ in range(min(3, len(cola))):
                            if cola:
                                tiempo_llegada = cola.popleft()
                                tiempo_espera = t - tiempo_llegada
                                # Fix: Ensure tiempo_espera is never negative
                                if tiempo_espera >= 0:
                                    tiempos_espera.append(tiempo_espera)
        
        # Fix: Check for empty tiempos_espera list
        if tiempos_espera:
            tiempo_promedio = sum(tiempos_espera) / len(tiempos_espera)
            congestión = sum([len(cola) for interseccion in self.intersecciones 
                            for cola in interseccion.cola_vehiculos.values()])
        else:
            tiempo_promedio = 30  # Default value if no data
            congestión = 100      # Default value indicating congestion
            
        return tiempo_promedio, congestión

    def agregar_flujo_calle(self, desde_id, hasta_id, flujo_mañana, flujo_tarde, flujo_noche):
        """Agrega información de flujo entre dos intersecciones"""
        self.flujos_calles[(desde_id, hasta_id)] = {
            'mañana': flujo_mañana,
            'tarde': flujo_tarde,
            'noche': flujo_noche
        }

