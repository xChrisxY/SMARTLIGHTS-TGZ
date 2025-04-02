from models.individuo_ag import IndividuoAG
import random
import matplotlib.pyplot as plt

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