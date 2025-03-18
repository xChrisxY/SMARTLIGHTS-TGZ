import random
from models.semaforo import Semaforo
from collections import deque

class IndividuoAG:
    def __init__(self, num_semaforos):
        self.cromosoma = []
        self.fitness = 0
        
        # Generar cromosoma aleatorio
        for i in range(num_semaforos):
            tiempo_verde = random.randint(15, 60)
            tiempo_amarillo = random.randint(3, 5)
            tiempo_rojo = random.randint(20, 60)
            desfase = random.randint(0, 30)
            
            self.cromosoma.append(Semaforo(i, tiempo_verde, tiempo_amarillo, tiempo_rojo, desfase))

    def calcular_fitness(self, red_vial, tasa_llegada=0.2, duracion_sim=3600):
        """Calcula el fitness del individuo basado en la simulación de tráfico"""
        # Reset simulation time
        red_vial.tiempo_simulacion = 0
        
        # Actualizar la configuración de semáforos en la red vial
        semaforo_idx = 0
        for interseccion in red_vial.intersecciones:
            # Guardar los IDs originales
            ids_originales = [sem.id for sem in interseccion.semaforos]
            
            for i, _ in enumerate(interseccion.semaforos):
                if semaforo_idx < len(self.cromosoma):
                    # Crear una copia del semáforo del cromosoma pero mantener el ID original
                    nuevo_semaforo = Semaforo(
                        id=ids_originales[i],
                        tiempo_verde=self.cromosoma[semaforo_idx].tiempo_verde,
                        tiempo_amarillo=self.cromosoma[semaforo_idx].tiempo_amarillo,
                        tiempo_rojo=self.cromosoma[semaforo_idx].tiempo_rojo,
                        desfase=self.cromosoma[semaforo_idx].desfase
                    )
                    interseccion.semaforos[i] = nuevo_semaforo
                    semaforo_idx += 1
        
        # Reiniciar las colas de vehículos
        for interseccion in red_vial.intersecciones:
            for semaforo_id in interseccion.cola_vehiculos:
                interseccion.cola_vehiculos[semaforo_id] = deque() 
        
        # Simular llegadas de vehículos con distribución Poisson
        red_vial.simular_llegada_poisson(tasa_llegada, duracion_sim)
        
        # Simular el tráfico y obtener métricas
        tiempo_promedio, congestion = red_vial.simular_trafico(duracion_sim)
        
        # Fix: Ensure metrics are positive
        tiempo_promedio = max(0.01, abs(tiempo_promedio))
        congestion = max(0.01, abs(congestion))
        
        # Calcular desincronización
        desincronizacion = self.calcular_desincronizacion()
        
        # Calcular fitness (menor tiempo de espera y congestión es mejor)
        alpha = 0.3  # Peso para la congestión
        beta = 0.1   # Peso para la desincronización
        
        # Fix: Ensure the denominator is positive
        denominator = tiempo_promedio + alpha * congestion + beta * desincronizacion
        if denominator <= 0:
            denominator = 0.0001  # Avoid zero or negative values
        
        self.fitness = 1 / denominator
        return self.fitness

    def calcular_desincronizacion(self):
        """Calcula una medida de desincronización entre semáforos adyacentes"""
        desincronizacion = 0
        
        # Ejemplo simple: comparar ciclos y desfases de semáforos consecutivos
        for i in range(len(self.cromosoma) - 1):
            s1 = self.cromosoma[i]
            s2 = self.cromosoma[i + 1]
            
            # Diferencia de ciclos (idealmente deberían ser similares)
            diff_ciclo = abs(s1.ciclo_total - s2.ciclo_total)
            
            # Diferencia de desfases (dependiendo del diseño vial)
            diff_desfase = min(abs(s1.desfase - s2.desfase), 
                              abs(s1.desfase - s2.desfase + s1.ciclo_total))
            
            desincronizacion += diff_ciclo + diff_desfase
            
        return desincronizacion