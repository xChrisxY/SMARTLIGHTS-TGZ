import numpy as np
import random
import matplotlib.pyplot as plt
from collections import deque

class Semaforo:
    def __init__(self, id, tiempo_verde=30, tiempo_amarillo=3, tiempo_rojo=30, desfase=0):
        self.id = id
        self.tiempo_verde = tiempo_verde
        self.tiempo_amarillo = tiempo_amarillo
        self.tiempo_rojo = tiempo_rojo
        self.desfase = desfase
        self.ciclo_total = tiempo_verde + tiempo_amarillo + tiempo_rojo
    
    def get_estado(self, tiempo_simulacion):
        # Calcula el estado del semáforo (verde, amarillo, rojo) en un tiempo dado
        tiempo_efectivo = (tiempo_simulacion + self.desfase) % self.ciclo_total
        
        if tiempo_efectivo < self.tiempo_verde:
            return "verde"
        elif tiempo_efectivo < (self.tiempo_verde + self.tiempo_amarillo):
            return "amarillo"
        else:
            return "rojo"
    
    def __str__(self):
        return f"Semáforo {self.id}: Verde={self.tiempo_verde}s, Amarillo={self.tiempo_amarillo}s, Rojo={self.tiempo_rojo}s, Desfase={self.desfase}s"

class Interseccion:
    def __init__(self, id, semaforos, conexiones=None):
        self.id = id
        self.semaforos = semaforos  # Lista de semáforos en esta intersección
        self.conexiones = conexiones if conexiones else []  # Conexiones a otras intersecciones
        self.cola_vehiculos = {s.id: deque() for s in semaforos}  # Colas de vehículos por dirección
    
    def __str__(self):
        return f"Intersección {self.id}: {len(self.semaforos)} semáforos, {len(self.conexiones)} conexiones"

class RedVial:
    def __init__(self, intersecciones):
        self.intersecciones = intersecciones
        self.tiempo_simulacion = 0
    
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
                                tiempos_espera.append(tiempo_espera)
        
        # Calcular estadísticas
        if tiempos_espera:
            tiempo_promedio = sum(tiempos_espera) / len(tiempos_espera)
            congestión = sum([len(cola) for interseccion in self.intersecciones 
                             for cola in interseccion.cola_vehiculos.values()])
        else:
            tiempo_promedio = float('inf')
            congestión = float('inf')
            
        return tiempo_promedio, congestión

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
        # Actualizar la configuración de semáforos en la red vial
        semaforo_idx = 0
        for interseccion in red_vial.intersecciones:
            for i, _ in enumerate(interseccion.semaforos):
                if semaforo_idx < len(self.cromosoma):
                    interseccion.semaforos[i] = self.cromosoma[semaforo_idx]
                    semaforo_idx += 1
        
        # Reiniciar las colas de vehículos
        for interseccion in red_vial.intersecciones:
            for semaforo_id in interseccion.cola_vehiculos:
                interseccion.cola_vehiculos[semaforo_id] = deque()
        
        # Simular llegadas de vehículos con distribución Poisson
        red_vial.simular_llegada_poisson(tasa_llegada, duracion_sim)
        
        # Simular el tráfico y obtener métricas
        tiempo_promedio, congestion = red_vial.simular_trafico(duracion_sim)
        
        # Calcular desincronización
        desincronizacion = self.calcular_desincronizacion()
        
        # Calcular fitness (menor tiempo de espera y congestión es mejor)
        alpha = 0.3  # Peso para la congestión
        beta = 0.1   # Peso para la desincronización
        
        if tiempo_promedio == 0:
            tiempo_promedio = 0.1  # Evitar división por cero
        
        self.fitness = 1 / (tiempo_promedio + alpha * congestion + beta * desincronizacion)
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

class AlgoritmoGenetico:
    def __init__(self, tamaño_poblacion, num_semaforos, red_vial, 
                prob_cruce=0.8, prob_mutacion=0.1, elitismo=0.05, 
                max_generaciones=100):
        self.tamaño_poblacion = tamaño_poblacion
        self.num_semaforos = num_semaforos
        self.red_vial = red_vial
        self.prob_cruce = prob_cruce
        self.prob_mutacion = prob_mutacion
        self.elitismo = elitismo
        self.max_generaciones = max_generaciones
        self.poblacion = []
        self.mejor_fitness_historico = []
        self.mejor_individuo = None
    
    def inicializar_poblacion(self):
        """Crea la población inicial de individuos"""
        self.poblacion = [IndividuoAG(self.num_semaforos) for _ in range(self.tamaño_poblacion)]
    
    def evaluar_poblacion(self):
        """Evalúa el fitness de todos los individuos"""
        for individuo in self.poblacion:
            individuo.calcular_fitness(self.red_vial)
    
    def seleccion_torneo(self, k=3):
        """Selecciona un individuo mediante torneo"""
        seleccionados = random.sample(self.poblacion, k)
        return max(seleccionados, key=lambda ind: ind.fitness)
    
    def cruce(self, padre1, padre2):
        """Realiza el cruce de dos puntos entre dos padres"""
        if random.random() > self.prob_cruce:
            return padre1, padre2
        
        hijo1 = IndividuoAG(0)  # Crear hijos vacíos
        hijo2 = IndividuoAG(0)
        hijo1.cromosoma = []
        hijo2.cromosoma = []
        
        # Seleccionar puntos de cruce
        punto1 = random.randint(0, len(padre1.cromosoma) - 1)
        punto2 = random.randint(punto1, len(padre1.cromosoma) - 1)
        
        # Realizar cruce de dos puntos
        hijo1.cromosoma = (padre1.cromosoma[:punto1] + 
                          padre2.cromosoma[punto1:punto2] + 
                          padre1.cromosoma[punto2:])
        
        hijo2.cromosoma = (padre2.cromosoma[:punto1] + 
                          padre1.cromosoma[punto1:punto2] + 
                          padre2.cromosoma[punto2:])
        
        return hijo1, hijo2
    
    def mutacion(self, individuo):
        """Aplica mutación a un individuo"""
        for i in range(len(individuo.cromosoma)):
            if random.random() < self.prob_mutacion:
                semaforo = individuo.cromosoma[i]
                
                # Seleccionar qué parámetro mutar
                param = random.choice(['verde', 'rojo', 'desfase'])
                
                if param == 'verde':
                    # Mutar tiempo de verde (±15%)
                    cambio = semaforo.tiempo_verde * random.uniform(-0.15, 0.15)
                    semaforo.tiempo_verde = max(15, int(semaforo.tiempo_verde + cambio))
                
                elif param == 'rojo':
                    # Mutar tiempo de rojo (±15%)
                    cambio = semaforo.tiempo_rojo * random.uniform(-0.15, 0.15)
                    semaforo.tiempo_rojo = max(10, int(semaforo.tiempo_rojo + cambio))
                
                else:  # desfase
                    # Mutar desfase (±30%)
                    cambio = semaforo.desfase * random.uniform(-0.3, 0.3)
                    semaforo.desfase = max(0, int(semaforo.desfase + cambio))
                
                # Actualizar ciclo total
                semaforo.ciclo_total = semaforo.tiempo_verde + semaforo.tiempo_amarillo + semaforo.tiempo_rojo
    
    def seleccion_siguiente_generacion(self, hijos):
        """Selecciona individuos para la siguiente generación"""
        # Combinar padres e hijos
        combinados = self.poblacion + hijos
        
        # Ordenar por fitness (de mayor a menor)
        combinados.sort(key=lambda ind: ind.fitness, reverse=True)
        
        # Elitismo: mantener los mejores individuos
        num_elite = int(self.tamaño_poblacion * self.elitismo)
        elite = combinados[:num_elite]
        
        # Selección por ruleta para el resto
        no_elite = combinados[num_elite:]
        sum_fitness = sum(ind.fitness for ind in no_elite)
        
        seleccionados = []
        while len(seleccionados) < self.tamaño_poblacion - num_elite:
            # Selección por ruleta
            r = random.uniform(0, sum_fitness)
            acumulado = 0
            for ind in no_elite:
                acumulado += ind.fitness
                if acumulado >= r:
                    seleccionados.append(ind)
                    break
        
        # Nueva población
        self.poblacion = elite + seleccionados
    
    def ejecutar(self):
        """Ejecuta el algoritmo genético"""
        # Inicializar población
        self.inicializar_poblacion()
        
        # Evaluar población inicial
        self.evaluar_poblacion()
        
        # Ordenar población por fitness
        self.poblacion.sort(key=lambda ind: ind.fitness, reverse=True)
        
        # Guardar mejor individuo
        self.mejor_individuo = self.poblacion[0]
        self.mejor_fitness_historico.append(self.mejor_individuo.fitness)
        
        print(f"Generación 0: Mejor fitness = {self.mejor_individuo.fitness:.6f}")
        
        # Bucle principal de evolución
        for gen in range(1, self.max_generaciones + 1):
            # Crear nueva generación
            hijos = []
            
            while len(hijos) < self.tamaño_poblacion:
                # Selección de padres
                padre1 = self.seleccion_torneo()
                padre2 = self.seleccion_torneo()
                
                # Cruce
                hijo1, hijo2 = self.cruce(padre1, padre2)
                
                # Mutación
                self.mutacion(hijo1)
                self.mutacion(hijo2)
                
                # Agregar hijos
                hijos.extend([hijo1, hijo2])
            
            # Evaluar hijos
            for hijo in hijos:
                hijo.calcular_fitness(self.red_vial)
            
            # Seleccionar siguiente generación
            self.seleccion_siguiente_generacion(hijos)
            
            # Actualizar mejor individuo
            if self.poblacion[0].fitness > self.mejor_individuo.fitness:
                self.mejor_individuo = self.poblacion[0]
            
            self.mejor_fitness_historico.append(self.mejor_individuo.fitness)
            
            if gen % 10 == 0:  # Mostrar progreso cada 10 generaciones
                print(f"Generación {gen}: Mejor fitness = {self.mejor_individuo.fitness:.6f}")
        
        print(f"\nMejor solución encontrada (Fitness: {self.mejor_individuo.fitness:.6f}):")
        for i, semaforo in enumerate(self.mejor_individuo.cromosoma):
            print(semaforo)
    
    def graficar_evolucion(self):
        """Gráfica la evolución del fitness a lo largo de las generaciones"""
        plt.figure(figsize=(10, 6))
        plt.plot(self.mejor_fitness_historico)
        plt.title('Evolución del Fitness')
        plt.xlabel('Generación')
        plt.ylabel('Fitness (mejor individuo)')
        plt.grid(True)
        plt.savefig('evolucion_fitness.png')
        plt.show()
    
    def obtener_mejores_soluciones(self, n=3):
        """Retorna las n mejores soluciones encontradas"""
        self.poblacion.sort(key=lambda ind: ind.fitness, reverse=True)
        return self.poblacion[:n]

# Ejemplo de uso del algoritmo genético
def crear_red_ejemplo():
    # Crear semáforos para la primera intersección
    s1 = Semaforo(0, tiempo_verde=30, tiempo_amarillo=3, tiempo_rojo=30, desfase=0)
    s2 = Semaforo(1, tiempo_verde=30, tiempo_amarillo=3, tiempo_rojo=30, desfase=30)
    
    # Crear primera intersección
    interseccion1 = Interseccion(0, [s1, s2])
    
    # Crear semáforos para la segunda intersección
    s3 = Semaforo(2, tiempo_verde=30, tiempo_amarillo=3, tiempo_rojo=30, desfase=0)
    s4 = Semaforo(3, tiempo_verde=30, tiempo_amarillo=3, tiempo_rojo=30, desfase=30)
    
    # Crear segunda intersección
    interseccion2 = Interseccion(1, [s3, s4])
    
    # Conectar intersecciones
    interseccion1.conexiones = [interseccion2]
    interseccion2.conexiones = [interseccion1]
    
    # Crear red vial
    red = RedVial([interseccion1, interseccion2])
    
    return red

def main():
    # Crear red vial de ejemplo
    red_ejemplo = crear_red_ejemplo()
    
    # Configurar y ejecutar algoritmo genético
    ag = AlgoritmoGenetico(
        tamaño_poblacion=50,
        num_semaforos=4,  # 4 semáforos en el ejemplo
        red_vial=red_ejemplo,
        prob_cruce=0.8,
        prob_mutacion=0.1,
        elitismo=0.05,
        max_generaciones=100
    )
    
    # Ejecutar algoritmo
    ag.ejecutar()
    
    # Graficar evolución
    ag.graficar_evolucion()
    
    # Obtener mejores soluciones
    mejores = ag.obtener_mejores_soluciones(3)
    
    print("\nLas tres mejores soluciones:")
    for i, sol in enumerate(mejores):
        print(f"\nSolución #{i+1} (Fitness: {sol.fitness:.6f}):")
        for semaforo in sol.cromosoma:
            print(semaforo)

if __name__ == "__main__":
    main()
