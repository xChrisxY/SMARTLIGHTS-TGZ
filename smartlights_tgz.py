#!/usr/bin/env python3 

import numpy as np
import matplotlib.pyplot as plt
import random
from collections import defaultdict

#####################################################
# Representación del entorno de tráfico
#####################################################

class Interseccion:
    def __init__(self, id, coordenadas, vias_conectadas):
        self.id = id
        self.coordenadas = coordenadas  # (lat, long)
        self.vias_conectadas = vias_conectadas  # lista de IDs de vías
        self.es_principal = False  # Flag para intersecciones en avenidas principales

class Via:
    def __init__(self, id, origen, destino, longitud, capacidad, sentido, es_principal=False):
        self.id = id
        self.origen = origen  # ID de intersección origen
        self.destino = destino  # ID de intersección destino
        self.longitud = longitud  # metros
        self.capacidad = capacidad  # vehículos/hora
        self.sentido = sentido  # 'unidireccional' o 'bidireccional'
        self.es_principal = es_principal  # Flag para avenidas principales
        self.tasa_llegada = {
            'manana': 0,  # Lambda para distribución Poisson de la mañana
            'mediodia': 0,  # Lambda para distribución Poisson del mediodía
            'tarde': 0,    # Lambda para distribución Poisson de la tarde
            'noche': 0     # Lambda para distribución Poisson de la noche
        }

class MapaVial:
    def __init__(self):
        self.intersecciones = {}  # {id: Interseccion}
        self.vias = {}  # {id: Via}
        self.rutas_principales = []  # Lista de secuencias de intersecciones que forman rutas principales

    def agregar_interseccion(self, interseccion):
        self.intersecciones[interseccion.id] = interseccion

    def agregar_via(self, via):
        self.vias[via.id] = via

    def definir_ruta_principal(self, lista_intersecciones):
        self.rutas_principales.append(lista_intersecciones)
        # Marcar las intersecciones y vías en la ruta como principales
        for i in range(len(lista_intersecciones)):
            interseccion_id = lista_intersecciones[i]
            self.intersecciones[interseccion_id].es_principal = True
            
            # Marcar la vía entre esta intersección y la siguiente como principal
            if i < len(lista_intersecciones) - 1:
                siguiente_id = lista_intersecciones[i + 1]
                for via_id, via in self.vias.items():
                    if ((via.origen == interseccion_id and via.destino == siguiente_id) or 
                        (via.destino == interseccion_id and via.origen == siguiente_id)):
                        via.es_principal = True

    def calcular_distancia_entre_intersecciones(self, id1, id2):
        """Calcula la distancia entre dos intersecciones utilizando las vías disponibles"""
        # Implementar algoritmo de camino más corto (Dijkstra) si es necesario
        # Aquí usamos una versión simplificada que busca una vía directa
        for via_id, via in self.vias.items():
            if (via.origen == id1 and via.destino == id2) or (via.origen == id2 and via.destino == id1):
                return via.longitud
        return float('inf')  # No hay conexión directa

#####################################################
# Generación de tráfico con distribución Poisson
#####################################################

def generar_llegadas_vehiculos(tasa_promedio, intervalo_tiempo):
    """
    Genera el número de vehículos que llegan en un intervalo de tiempo
    según una distribución Poisson
    
    Parámetros:
    tasa_promedio: vehículos por segundo
    intervalo_tiempo: duración del período en segundos
    
    Retorna: número de vehículos que llegan en ese intervalo
    """
    lambda_param = tasa_promedio * intervalo_tiempo
    return np.random.poisson(lambda_param)

def obtener_tasa_llegada(via, periodo):
    """
    Retorna la tasa de llegada de vehículos para una vía en un período específico
    
    Parámetros:
    via: objeto Via
    periodo: 'manana', 'mediodia', 'tarde', 'noche'
    
    Retorna: tasa de llegada en vehículos por segundo
    """
    return via.tasa_llegada[periodo] / 3600  # Convertir de vehículos/hora a vehículos/segundo

#####################################################
# Simulador de tráfico
#####################################################

class Vehiculo:
    def __init__(self, id, tiempo_llegada, via_id):
        self.id = id
        self.tiempo_llegada = tiempo_llegada  # Segundo en que llega a la intersección
        self.tiempo_salida = None  # Segundo en que sale de la intersección
        self.via_id = via_id  # ID de la vía en la que se encuentra
        self.tiempo_espera = 0  # Tiempo de espera en semáforo

class EstadoSemaforo:
    def __init__(self, tiempo_verde, tiempo_amarillo, offset=0):
        self.tiempo_verde = tiempo_verde
        self.tiempo_amarillo = tiempo_amarillo
        self.tiempo_rojo = 0  # Se calculará automáticamente
        self.offset = offset  # Desfase respecto al semáforo de referencia
        self.tiempo_ciclo = 0  # Tiempo total del ciclo (verde + amarillo + rojo)

class SimuladorTrafico:
    def __init__(self, mapa_vial, duracion_simulacion=3600, periodo='manana'):
        """
        Inicializa el simulador de tráfico
        
        Parámetros:
        mapa_vial: objeto MapaVial con la estructura de la red
        duracion_simulacion: duración de la simulación en segundos
        periodo: período del día ('manana', 'mediodia', 'tarde', 'noche')
        """
        self.mapa_vial = mapa_vial
        self.duracion_simulacion = duracion_simulacion
        self.periodo = periodo
        self.estados_semaforos = {}  # {interseccion_id: EstadoSemaforo}
        self.vehiculos = []  # Lista de todos los vehículos en la simulación
        self.colas = defaultdict(list)  # {interseccion_id: [vehículos en cola]}
        self.tiempo_actual = 0
        self.vehiculo_counter = 0
        
    def configurar_semaforos(self, genoma):
        """
        Configura los semáforos según el genoma proporcionado
        
        Formato del genoma: 
        [verde1, amarillo1, offset1, verde2, amarillo2, offset2, ...]
        """
        idx = 0
        for interseccion_id in sorted(self.mapa_vial.intersecciones.keys()):
            tiempo_verde = genoma[idx]
            tiempo_amarillo = genoma[idx + 1]
            offset = genoma[idx + 2]
            
            estado = EstadoSemaforo(tiempo_verde, tiempo_amarillo, offset)
            
            # Calcular tiempo en rojo basado en tiempos de semáforos adyacentes
            interseccion = self.mapa_vial.intersecciones[interseccion_id]
            tiempo_rojo_total = 0
            
            # Para simplificar, asumimos que el tiempo en rojo es proporcional al número de vías conectadas
            # En un modelo más sofisticado, se calcularía basado en los tiempos de las intersecciones conectadas
            num_vias_conectadas = len(interseccion.vias_conectadas)
            if num_vias_conectadas > 1:  # Si hay más de una vía conectada
                # El tiempo en rojo debe ser suficiente para que las otras vías tengan su tiempo en verde y amarillo
                tiempo_rojo_total = max(10, (num_vias_conectadas - 1) * (tiempo_verde + tiempo_amarillo))
            
            estado.tiempo_rojo = tiempo_rojo_total
            estado.tiempo_ciclo = tiempo_verde + tiempo_amarillo + tiempo_rojo_total
            
            self.estados_semaforos[interseccion_id] = estado
            
            idx += 3
    
    def esta_semaforo_en_verde(self, interseccion_id, tiempo):
        """
        Determina si el semáforo de una intersección está en verde en un momento dado
        
        Parámetros:
        interseccion_id: ID de la intersección
        tiempo: segundo de la simulación
        
        Retorna: True si está en verde, False en caso contrario
        """
        # Verificar si existe un semáforo para esta intersección
        if interseccion_id not in self.estados_semaforos:
            # Para intersecciones ficticias o sin semáforo, asumir siempre en verde
            return True
            
        estado = self.estados_semaforos[interseccion_id]
        
        # Ajustar el tiempo según el offset
        tiempo_ajustado = (tiempo - estado.offset) % estado.tiempo_ciclo
        
        # El semáforo está en verde si el tiempo ajustado está en el rango [0, tiempo_verde)
        return 0 <= tiempo_ajustado < estado.tiempo_verde
    
    def simular(self):
        """
        Realiza la simulación de tráfico
        
        Retorna:
        tiempo_promedio_espera: tiempo promedio de espera por vehículo
        longitud_promedio_cola: longitud promedio de las colas en las intersecciones
        """
        # Generar llegadas de vehículos para toda la simulación
        for via_id, via in self.mapa_vial.vias.items():
            tasa = obtener_tasa_llegada(via, self.periodo)
            
            # Generar llegadas para cada segundo de la simulación
            for t in range(self.duracion_simulacion):
                llegadas = generar_llegadas_vehiculos(tasa, 1)  # Generar para 1 segundo
                
                for _ in range(llegadas):
                    self.vehiculo_counter += 1
                    vehiculo = Vehiculo(
                        id=self.vehiculo_counter,
                        tiempo_llegada=t,
                        via_id=via_id
                    )
                    self.vehiculos.append(vehiculo)
                    
                    # Añadir a la cola de la intersección destino
                    self.colas[via.destino].append(vehiculo)
        
        # Procesar el movimiento de vehículos en cada intersección para cada segundo
        historial_colas = defaultdict(list)  # {interseccion_id: [longitudes de cola por segundo]}
        
        for t in range(self.duracion_simulacion):
            self.tiempo_actual = t
            
            # Registrar longitudes de cola actuales
            for interseccion_id, cola in self.colas.items():
                historial_colas[interseccion_id].append(len(cola))
            
            # Procesar cada intersección
            for interseccion_id, cola in list(self.colas.items()):
                if not cola:
                    continue
                
                # Verificar si el semáforo está en verde
                if self.esta_semaforo_en_verde(interseccion_id, t):
                    # Calcular cuántos vehículos pueden salir en este segundo
                    # Asumimos que pueden salir 1 vehículo cada 2 segundos cuando el semáforo está en verde
                    capacidad_salida = 1 if t % 2 == 0 else 0
                    
                    # Procesar salida de vehículos
                    for _ in range(min(capacidad_salida, len(cola))):
                        vehiculo = cola.pop(0)
                        vehiculo.tiempo_salida = t
                        vehiculo.tiempo_espera = t - vehiculo.tiempo_llegada
        
        # Calcular métricas
        tiempos_espera = [v.tiempo_espera for v in self.vehiculos if v.tiempo_salida is not None]
        
        if not tiempos_espera:
            return float('inf'), float('inf')  # Si no hay vehículos procesados, retornar valores altos
            
        tiempo_promedio_espera = sum(tiempos_espera) / len(tiempos_espera)
        
        # Calcular longitud promedio de cola
        todas_longitudes = []
        for interseccion_id, longitudes in historial_colas.items():
            todas_longitudes.extend(longitudes)
        
        longitud_promedio_cola = sum(todas_longitudes) / len(todas_longitudes) if todas_longitudes else 0
        
        return tiempo_promedio_espera, longitud_promedio_cola

#####################################################
# Algoritmo Genético
#####################################################

class AlgoritmoGenetico:
    def __init__(self, mapa_vial, periodos=['manana', 'mediodia', 'tarde', 'noche']):
        """
        Inicializa el algoritmo genético
        
        Parámetros:
        mapa_vial: objeto MapaVial con la estructura de la red
        periodos: lista de períodos del día a optimizar
        """
        self.mapa_vial = mapa_vial
        self.periodos = periodos
        self.poblacion = []
        self.mejor_fitness = 0
        self.mejor_individuo = None
        self.historial_fitness = []
        
        # Parámetros del AG
        self.tamano_poblacion = 80
        self.tasa_cruza = 0.85
        self.tasa_mutacion = 0.08
        self.num_generaciones = 500
        self.umbral_convergencia = 0.001
        self.porcentaje_elitismo = 0.1
        
        # Pesos para la función de fitness
        self.w_tiempo_espera = 0.7
        self.w_longitud_cola = 0.2
        self.w_coordinacion = 0.1
        
        # Configuración de genes
        self.min_tiempo_verde = 10
        self.max_tiempo_verde = 60
        self.min_tiempo_amarillo = 3
        self.max_tiempo_amarillo = 10
        self.max_offset = 120
    
    def generar_individuo_aleatorio(self):
        """
        Genera un individuo aleatorio
        
        Formato: [verde1, amarillo1, offset1, verde2, amarillo2, offset2, ...]
        
        Retorna: lista de genes
        """
        num_intersecciones = len(self.mapa_vial.intersecciones)
        genes = []
        
        for _ in range(num_intersecciones):
            # Tiempo en verde (segundos)
            genes.append(random.uniform(self.min_tiempo_verde, self.max_tiempo_verde))
            
            # Tiempo en amarillo (segundos)
            genes.append(random.uniform(self.min_tiempo_amarillo, self.max_tiempo_amarillo))
            
            # Offset (segundos)
            genes.append(random.uniform(0, self.max_offset))
        
        return genes
    
    def inicializar_poblacion(self):
        """Crea la población inicial de individuos aleatorios"""
        self.poblacion = [self.generar_individuo_aleatorio() for _ in range(self.tamano_poblacion)]
    
    def calcular_fitness(self, individuo):
        """
        Calcula el fitness de un individuo
        
        Parámetros:
        individuo: lista de genes
        
        Retorna: valor de fitness
        """
        fitness_por_periodo = {}
        
        for periodo in self.periodos:
            # Crear simulador para este período
            simulador = SimuladorTrafico(self.mapa_vial, duracion_simulacion=1800, periodo=periodo)
            
            # Configurar semáforos según el genoma del individuo
            simulador.configurar_semaforos(individuo)
            
            # Ejecutar simulación
            tiempo_espera, longitud_cola = simulador.simular()
            
            # Calcular penalización por falta de coordinación
            penalizacion_coordinacion = self.calcular_penalizacion_coordinacion(individuo)
            
            # Calcular fitness parcial
            if tiempo_espera == float('inf'):
                fitness_parcial = 0
            else:
                # Normalizar componentes (menor es mejor, por eso usamos 1/x)
                fitness_tiempo = 1 / max(1, tiempo_espera)
                fitness_cola = 1 / max(1, longitud_cola)
                fitness_coord = 1 / max(1, penalizacion_coordinacion)
                
                # Combinar componentes de fitness con pesos
                fitness_parcial = (
                    self.w_tiempo_espera * fitness_tiempo +
                    self.w_longitud_cola * fitness_cola +
                    self.w_coordinacion * fitness_coord
                )
            
            fitness_por_periodo[periodo] = fitness_parcial
        
        # Promedio de fitness en todos los periodos
        return sum(fitness_por_periodo.values()) / len(fitness_por_periodo)
    
    def calcular_penalizacion_coordinacion(self, individuo):
        """
        Calcula una penalización basada en la falta de coordinación entre semáforos
        en las rutas principales
        
        Retorna: valor de penalización (más alto = peor coordinación)
        """
        penalizacion = 0
        velocidad_promedio = 40  # km/h, convertido a m/s
        velocidad_ms = velocidad_promedio * 1000 / 3600
        
        # Para cada ruta principal
        for ruta in self.mapa_vial.rutas_principales:
            # Para cada par de intersecciones consecutivas en la ruta
            for i in range(len(ruta) - 1):
                id1 = ruta[i]
                id2 = ruta[i + 1]
                
                # Obtener la distancia entre estas intersecciones
                distancia = self.mapa_vial.calcular_distancia_entre_intersecciones(id1, id2)
                
                if distancia == float('inf'):
                    continue  # No hay conexión directa
                
                # Calcular el tiempo que tarda un vehículo en recorrer esta distancia
                tiempo_recorrido = distancia / velocidad_ms
                
                # Obtener los offsets de los semáforos
                idx1 = sorted(self.mapa_vial.intersecciones.keys()).index(id1) * 3 + 2
                idx2 = sorted(self.mapa_vial.intersecciones.keys()).index(id2) * 3 + 2
                
                offset1 = individuo[idx1]
                offset2 = individuo[idx2]
                
                # Calcular la diferencia entre el offset del segundo semáforo y
                # el tiempo que tardaría un vehículo en llegar desde el primero
                tiempo_verde1 = individuo[idx1 - 2]
                diff = abs((offset2 - offset1) % 120 - tiempo_recorrido)
                
                # Si el vehículo llega cuando el segundo semáforo está en rojo,
                # añadir una penalización
                if diff > tiempo_verde1 / 2:
                    penalizacion += diff
        
        return penalizacion
    
    def seleccionar_por_ruleta(self):
        """
        Selecciona un individuo mediante el método de la ruleta
        
        Retorna: individuo seleccionado
        """
        # Calcular fitness de todos los individuos
        fitness_total = sum(self.calcular_fitness(individuo) for individuo in self.poblacion)
        
        if fitness_total == 0:
            # Si el fitness total es 0, seleccionar aleatoriamente
            return random.choice(self.poblacion)
        
        # Girar la ruleta
        valor = random.uniform(0, fitness_total)
        acumulado = 0
        
        for individuo in self.poblacion:
            acumulado += self.calcular_fitness(individuo)
            if acumulado >= valor:
                return individuo
        
        # Por si acaso, retornar el último individuo
        return self.poblacion[-1]
    
    def cruzar(self, padre1, padre2):
        """
        Realiza la cruza en un punto entre dos padres
        
        Parámetros:
        padre1, padre2: individuos padres
        
        Retorna: dos hijos resultantes de la cruza
        """
        # Verificar si se debe realizar la cruza
        if random.random() > self.tasa_cruza:
            return padre1.copy(), padre2.copy()
        
        # Seleccionar punto de cruza (en múltiplos de 3 para mantener la estructura)
        punto_cruza = random.randint(1, len(padre1) // 3 - 1) * 3
        
        # Realizar cruza
        hijo1 = padre1[:punto_cruza] + padre2[punto_cruza:]
        hijo2 = padre2[:punto_cruza] + padre1[punto_cruza:]
        
        return hijo1, hijo2
    
    def mutar(self, individuo):
        """
        Aplica mutación a un individuo
        
        Parámetros:
        individuo: individuo a mutar
        
        Retorna: individuo mutado
        """
        for i in range(len(individuo)):
            # Verificar si se debe mutar este gen
            if random.random() <= self.tasa_mutacion:
                # Determinar qué tipo de gen es (verde, amarillo u offset)
                indice_tipo = i % 3
                
                if indice_tipo == 0:  # Tiempo verde
                    individuo[i] = random.uniform(self.min_tiempo_verde, self.max_tiempo_verde)
                elif indice_tipo == 1:  # Tiempo amarillo
                    individuo[i] = random.uniform(self.min_tiempo_amarillo, self.max_tiempo_amarillo)
                else:  # Offset
                    individuo[i] = random.uniform(0, self.max_offset)
        
        return individuo
    
    def seleccionar_nueva_poblacion(self, descendientes):
        """
        Selecciona la nueva población utilizando elitismo
        
        Parámetros:
        descendientes: lista de individuos descendientes
        
        Retorna: nueva población
        """
        # Calcular fitness de todos los individuos
        fitness_poblacion = [(individuo, self.calcular_fitness(individuo)) for individuo in self.poblacion]
        
        # Ordenar por fitness (de mayor a menor)
        fitness_poblacion.sort(key=lambda x: x[1], reverse=True)
        
        # Seleccionar elite
        num_elite = int(self.tamano_poblacion * self.porcentaje_elitismo)
        elite = [individuo for individuo, _ in fitness_poblacion[:num_elite]]
        
        # Completar con descendientes
        nueva_poblacion = elite + descendientes[:self.tamano_poblacion - num_elite]
        
        return nueva_poblacion
    
    def ejecutar(self):
        """
        Ejecuta el algoritmo genético
        
        Retorna: mejor individuo encontrado y su fitness
        """
        # Inicializar población
        self.inicializar_poblacion()
        
        for generacion in range(self.num_generaciones):
            # Evaluar fitness de la población actual
            fitness_actual = [self.calcular_fitness(individuo) for individuo in self.poblacion]
            mejor_fitness_actual = max(fitness_actual)
            idx_mejor = fitness_actual.index(mejor_fitness_actual)
            
            # Actualizar mejor individuo global
            if mejor_fitness_actual > self.mejor_fitness:
                self.mejor_fitness = mejor_fitness_actual
                self.mejor_individuo = self.poblacion[idx_mejor].copy()
            
            # Guardar historial de fitness
            self.historial_fitness.append(mejor_fitness_actual)
            
            # Criterio de parada por convergencia
            if generacion > 20 and abs(self.historial_fitness[-1] - self.historial_fitness[-20]) < self.umbral_convergencia:
                print(f"Convergencia alcanzada en generación {generacion}")
                break
            
            # Generar descendientes
            descendientes = []
            
            while len(descendientes) < self.tamano_poblacion:
                # Seleccionar padres
                padre1 = self.seleccionar_por_ruleta()
                padre2 = self.seleccionar_por_ruleta()
                
                # Cruzar
                hijo1, hijo2 = self.cruzar(padre1, padre2)
                
                # Mutar
                hijo1 = self.mutar(hijo1)
                hijo2 = self.mutar(hijo2)
                
                # Añadir a descendientes
                descendientes.extend([hijo1, hijo2])
            
            # Seleccionar nueva población
            self.poblacion = self.seleccionar_nueva_poblacion(descendientes)
            
            # Mostrar progreso
            if generacion % 10 == 0:
                print(f"Generación {generacion}, Mejor fitness: {mejor_fitness_actual:.6f}")
        
        return self.mejor_individuo, self.mejor_fitness
    
    def graficar_evolucion(self):
        """Grafica la evolución del fitness a lo largo de las generaciones"""
        plt.figure(figsize=(10, 6))
        plt.plot(self.historial_fitness)
        plt.title('Evolución del Fitness')
        plt.xlabel('Generación')
        plt.ylabel('Fitness')
        plt.grid(True)
        plt.show()
    
    def evaluar_solucion(self, individuo):
        """
        Evalúa detalladamente una solución
        
        Parámetros:
        individuo: individuo a evaluar
        
        Retorna: diccionario con métricas de desempeño
        """
        resultados = {}
        
        for periodo in self.periodos:
            # Crear simulador para este período
            simulador = SimuladorTrafico(self.mapa_vial, duracion_simulacion=3600, periodo=periodo)
            
            # Configurar semáforos según el genoma del individuo
            simulador.configurar_semaforos(individuo)
            
            # Ejecutar simulación
            tiempo_espera, longitud_cola = simulador.simular()
            
            # Guardar resultados
            resultados[periodo] = {
                'tiempo_promedio_espera': tiempo_espera,
                'longitud_promedio_cola': longitud_cola,
                'vehiculos_procesados': sum(1 for v in simulador.vehiculos if v.tiempo_salida is not None),
                'vehiculos_totales': len(simulador.vehiculos)
            }
        
        return resultados

#####################################################
# Ejemplo de uso
#####################################################

def crear_mapa_ejemplo():
    """Crea un mapa de ejemplo con 5 intersecciones"""
    mapa = MapaVial()
    
    # Crear intersecciones
    intersecciones = [
        Interseccion(1, (16.7689, -93.1502), []),
        Interseccion(2, (16.7645, -93.1489), []),
        Interseccion(3, (16.7601, -93.1476), []),
        Interseccion(4, (16.7558, -93.1463), []),
        Interseccion(5, (16.7514, -93.1450), [])
    ]
    
    # Añadir intersecciones al mapa
    for interseccion in intersecciones:
        mapa.agregar_interseccion(interseccion)
    
    # Crear vías principales (avenida norte-sur)
    vias_principales = [
        Via(1, 1, 2, 500, 1200, 'bidireccional', True),
        Via(2, 2, 3, 500, 1200, 'bidireccional', True),
        Via(3, 3, 4, 500, 1200, 'bidireccional', True),
        Via(4, 4, 5, 500, 1200, 'bidireccional', True)
    ]
    
    # Añadir vías principales al mapa
    for via in vias_principales:
        mapa.agregar_via(via)
        
        # Actualizar listas de vías conectadas en las intersecciones
        mapa.intersecciones[via.origen].vias_conectadas.append(via.id)
        mapa.intersecciones[via.destino].vias_conectadas.append(via.id)
    
    # Crear vías secundarias (este-oeste)
    vias_secundarias = []
    for i in range(1, 6):
        # Vía hacia el este desde cada intersección
        via_este = Via(
            10 + i, 
            i, 
            i + 100,  # ID ficticio para nodo externo
            300, 
            800, 
            'unidireccional', 
            False
        )
        
        # Vía desde el oeste hacia cada intersección
        via_oeste = Via(
            20 + i, 
            i + 200,  # ID ficticio para nodo externo
            i, 
            300, 
            800, 
            'unidireccional', 
            False
        )
        
        vias_secundarias.extend([via_este, via_oeste])
    
    # Añadir vías secundarias al mapa
    for via in vias_secundarias:
        if via.origen in mapa.intersecciones:
            mapa.agregar_via(via)
            mapa.intersecciones[via.origen].vias_conectadas.append(via.id)
        elif via.destino in mapa.intersecciones:
            mapa.agregar_via(via)
            mapa.intersecciones[via.destino].vias_conectadas.append(via.id)
    
    # Definir ruta principal norte-sur
    mapa.definir_ruta_principal([1, 2, 3, 4, 5])
    
    # Configurar tasas de llegada para las vías
    for via_id, via in mapa.vias.items():
        if via.es_principal:
            # Mayor flujo en vías principales
            via.tasa_llegada = {
                'manana': 800,    # Vehículos/hora en hora pico de la mañana
                'mediodia': 500,  # Vehículos/hora al mediodía
                'tarde': 900,     # Vehículos/hora en hora pico de la tarde
                'noche': 300      # Vehículos/hora en la noche
            }
        else:
            # Flujo normal en vías secundarias
            via.tasa_llegada = {
                'manana': 400,    # Vehículos/hora en hora pico de la mañana
                'mediodia': 300,  # Vehículos/hora al mediodía
                'tarde': 500,     # Vehículos/hora en hora pico de la tarde
                'noche': 200      # Vehículos/hora en la noche
            }
    
    return mapa

def ejecutar_optimizacion():
    """Ejecuta el proceso de optimización para el mapa de ejemplo"""
    # Crear mapa
    mapa = crear_mapa_ejemplo()
    
    # Crear algoritmo genético
    ag = AlgoritmoGenetico(mapa, periodos=['manana', 'tarde'])
    
    # Ejecutar optimización
    mejor_individuo, mejor_fitness = ag.ejecutar()
    
    print(f"Mejor fitness: {mejor_fitness}")
    print(f"Mejor individuo: {mejor_individuo}")
    
    # Evaluar solución
    resultados = ag.evaluar_solucion(mejor_individuo)
    print("\nResultados detallados:")
    for periodo, metricas in resultados.items():
        print(f"\n{periodo.capitalize()}:")
        for metrica, valor in metricas.items():
            print(f"  {metrica}: {valor}")
    
    # Graficar evolución
    ag.graficar_evolucion()
    
    return mejor_individuo, resultados

if __name__ == "__main__":
    # Establecer semilla para reproducibilidad
    np.random.seed(42)
    random.seed(42)
    
    # Ejecutar optimización
    mejor_solucion, resultados = ejecutar_optimizacion()
    
    # Visualizar la solución
    print("\nConfiguración de semáforos optimizada:")
    mapa = crear_mapa_ejemplo()
    
    for i, interseccion_id in enumerate(sorted(mapa.intersecciones.keys())):
        idx = i * 3
        tiempo_verde = mejor_solucion[idx]
        tiempo_amarillo = mejor_solucion[idx + 1]
        offset = mejor_solucion[idx + 2]
        
        print(f"Intersección {interseccion_id}:")
        print(f"  Tiempo en verde: {tiempo_verde:.2f} segundos")
        print(f"  Tiempo en amarillo: {tiempo_amarillo:.2f} segundos")
        print(f"  Offset: {offset:.2f} segundos")
        
        # Calcular tiempo en rojo (asumiendo ciclo similar al de la simulación)
        interseccion = mapa.intersecciones[interseccion_id]
        tiempo_rojo = max(10, (len(interseccion.vias_conectadas) - 1) * (tiempo_verde + tiempo_amarillo))
        tiempo_ciclo = tiempo_verde + tiempo_amarillo + tiempo_rojo
        
        print(f"  Tiempo en rojo estimado: {tiempo_rojo:.2f} segundos")
        print(f"  Tiempo total de ciclo: {tiempo_ciclo:.2f} segundos")           
