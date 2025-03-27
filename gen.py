import numpy as np
import random
import matplotlib.pyplot as plt
from collections import deque
import json
import folium
import json
import matplotlib.colors as mcolors
from matplotlib.cm import get_cmap
import io
import base64
import copy

# Modificación en la función cargar_red_vial
def cargar_red_vial(archivo_json):
    """Carga la red vial desde un archivo JSON"""
    with open(archivo_json, 'r', encoding='utf-8') as f:
        datos = json.load(f)
    
    # Crear diccionario de intersecciones para referenciar
    intersecciones_dict = {}
    
    # Primero crear todas las intersecciones con sus semáforos
    for interseccion_data in datos['intersecciones']:
        semaforos = []
        for semaforo_data in interseccion_data['semaforos']:
            semaforo = Semaforo(
                id=semaforo_data['id'],
                tiempo_verde=semaforo_data['tiempo_verde_inicial'],
                tiempo_amarillo=semaforo_data['tiempo_amarillo_inicial'],
                tiempo_rojo=semaforo_data['tiempo_rojo_inicial'],
                desfase=0  # Inicialmente sin desfase
            )
            semaforos.append(semaforo)

        # Incluir coordenadas si están disponibles
        coordenadas = interseccion_data.get('coordenadas', None)
        
        interseccion = Interseccion(
            id=interseccion_data['id'],
            semaforos=semaforos,
            nombre=interseccion_data.get('nombre', ''),
            coordenadas=coordenadas
        )
        intersecciones_dict[interseccion.id] = interseccion

            # Luego establecer las conexiones entre intersecciones
    for interseccion_data in datos['intersecciones']:
        interseccion = intersecciones_dict[interseccion_data['id']]
        for conexion_id in interseccion_data['conexiones']:
            if conexion_id in intersecciones_dict:
                interseccion.conexiones.append(intersecciones_dict[conexion_id])
    
    # Crear la red vial
    red = RedVial(list(intersecciones_dict.values()))
    
    # Configurar las calles y flujos de tráfico
    for calle_data in datos['calles']:
        # Aquí puedes agregar más configuración según tus necesidades
        desde = intersecciones_dict[calle_data['desde_interseccion']]
        hasta = intersecciones_dict[calle_data['hasta_interseccion']]
        red.agregar_flujo_calle(
            desde.id, 
            hasta.id, 
            calle_data['flujo_promedio']['mañana'],
            calle_data['flujo_promedio']['tarde'],
            calle_data['flujo_promedio']['noche']
        )
    
    return red


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
    def __init__(self, id, semaforos, conexiones=None, nombre='', coordenadas=None):
        self.id = id
        self.semaforos = semaforos  # Lista de semáforos en esta intersección
        self.conexiones = conexiones if conexiones else []  # Conexiones a otras intersecciones
        self.cola_vehiculos = {s.id: deque() for s in semaforos}  # Colas de vehículos por dirección
        self.nombre = nombre
        self.coordenadas = coordenadas
    
    def __str__(self):
        return f"Intersección {self.id}: {len(self.semaforos)} semáforos, {len(self.conexiones)} conexiones"


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


def visualizar_red_vial(red_vial, mejor_solucion=None, archivo_salida='mapa_semaforos.html'):
    """
    Visualiza la red vial y los semáforos optimizados en un mapa interactivo usando Folium
    
    Parámetros:
    - red_vial: objeto RedVial con las intersecciones y conexiones
    - mejor_solucion: objeto IndividuoAG con la mejor solución del algoritmo genético
    - archivo_salida: nombre del archivo HTML donde se guardará el mapa
    """
    # Obtener el centro aproximado del mapa (promedio de coordenadas)
    coordenadas = [i.coordenadas for i in red_vial.intersecciones if i.coordenadas]
    
    if not coordenadas:
        # Default coordinates for Tuxtla Gutiérrez if no coordinates in data
        centro_mapa = [16.7506, -93.1029]
    else:
        # Check the format of coordinates
        first_coord = coordenadas[0]
        
        # If coordinates are in dictionary format
        if isinstance(first_coord, dict):
            # Determine the key names (they might be 'lat'/'lng' or 'latitude'/'longitude')
            lat_key = next(key for key in first_coord.keys() if 'lat' in key.lower())
            lng_key = next(key for key in first_coord.keys() if 'lon' in key.lower() or 'lng' in key.lower())
            
            latitudes = [c[lat_key] for c in coordenadas]
            longitudes = [c[lng_key] for c in coordenadas]
        # If coordinates are in a list/tuple format but need to be accessed differently
        elif hasattr(first_coord, '__iter__') and not isinstance(first_coord, (str, bytes)):
            latitudes = [c[0] if isinstance(c, (list, tuple)) else c.latitude for c in coordenadas]
            longitudes = [c[1] if isinstance(c, (list, tuple)) else c.longitude for c in coordenadas]
        else:
            # Print debug info
            print(f"Coordinate format: {type(first_coord)}")
            print(f"Sample coordinate: {first_coord}")
            # Default to center of Tuxtla Gutiérrez
            centro_mapa = [16.7506, -93.1029]
            return
            
        centro_mapa = [sum(latitudes) / len(latitudes), sum(longitudes) / len(longitudes)]
    # Crear mapa base
    mapa = folium.Map(location=centro_mapa, zoom_start=14, 
                     tiles='OpenStreetMap')
    
    # Crear colormap para representar flujo de tráfico
    cmap = get_cmap('YlOrRd')
    
    # Encontrar el flujo máximo para normalizar colores
    flujo_max = 0
    for (desde_id, hasta_id), flujos in red_vial.flujos_calles.items():
        for periodo, flujo in flujos.items():
            flujo_max = max(flujo_max, flujo)
    
    # Aplicar la solución del AG si existe
    if mejor_solucion:
        semaforo_idx = 0
        for interseccion in red_vial.intersecciones:
            ids_originales = [sem.id for sem in interseccion.semaforos]
            for i, _ in enumerate(interseccion.semaforos):
                if semaforo_idx < len(mejor_solucion.cromosoma):
                    # Actualizar semáforos con la mejor solución
                    nuevo_semaforo = Semaforo(
                        id=ids_originales[i],
                        tiempo_verde=mejor_solucion.cromosoma[semaforo_idx].tiempo_verde,
                        tiempo_amarillo=mejor_solucion.cromosoma[semaforo_idx].tiempo_amarillo,
                        tiempo_rojo=mejor_solucion.cromosoma[semaforo_idx].tiempo_rojo,
                        desfase=mejor_solucion.cromosoma[semaforo_idx].desfase
                    )
                    interseccion.semaforos[i] = nuevo_semaforo
                    semaforo_idx += 1
    
    # Crear líneas para representar las calles
    for interseccion in red_vial.intersecciones:
        # Verificar si hay coordenadas y validar que sean numéricas
        if not interseccion.coordenadas:
            print(f"Advertencia: La intersección {interseccion.id} no tiene coordenadas")
            continue
        
        # Imprimir para depuración
        print(f"Procesando intersección: {interseccion.id}, coordenadas: {interseccion.coordenadas}, tipo: {type(interseccion.coordenadas)}")
        
        # Verificar el formato de las coordenadas y convertirlas a valores numéricos
        try:
            if isinstance(interseccion.coordenadas, dict):
                # Si es un diccionario, intenta extraer lat/lng o latitude/longitude
                keys = interseccion.coordenadas.keys()
                lat_key = next((k for k in keys if 'lat' in k.lower()), None)
                lng_key = next((k for k in keys if 'lng' in k.lower() or 'lon' in k.lower()), None)
                
                if lat_key and lng_key:
                    origen_lat = float(interseccion.coordenadas[lat_key])
                    origen_lon = float(interseccion.coordenadas[lng_key])
                else:
                    print(f"Error: No se pueden identificar las claves lat/lng en: {interseccion.coordenadas}")
                    continue
            elif isinstance(interseccion.coordenadas, (list, tuple)) and len(interseccion.coordenadas) >= 2:
                # Si es una lista o tupla, toma los primeros dos elementos
                origen_lat = float(interseccion.coordenadas[0])
                origen_lon = float(interseccion.coordenadas[1])
            else:
                # Intenta acceder a los atributos latitude/longitude
                try:
                    origen_lat = float(interseccion.coordenadas.latitude)
                    origen_lon = float(interseccion.coordenadas.longitude)
                except AttributeError:
                    print(f"Error: Formato de coordenadas no reconocido: {interseccion.coordenadas}")
                    continue
        except (ValueError, TypeError) as e:
            print(f"Error al convertir coordenadas para la intersección {interseccion.id}: {e}")
            print(f"Valor de coordenadas: {interseccion.coordenadas}")
            continue
        
        # Añadir marcador para cada intersección
        popup_text = f"<b>Intersección: {interseccion.nombre or interseccion.id}</b><br>"
        popup_text += "<b>Semáforos:</b><br>"
        
        for semaforo in interseccion.semaforos:
            popup_text += f"ID: {semaforo.id}<br>"
            popup_text += f"Verde: {semaforo.tiempo_verde}s, "
            popup_text += f"Amarillo: {semaforo.tiempo_amarillo}s, "
            popup_text += f"Rojo: {semaforo.tiempo_rojo}s, "
            popup_text += f"Desfase: {semaforo.desfase}s<br>"
        
        # Crear gráfico de pastel para mostrar distribución de tiempos en semáforo
        if interseccion.semaforos:
            fig, ax = plt.subplots(figsize=(4, 3))
            semaforo = interseccion.semaforos[0]  # Tomamos el primer semáforo como ejemplo
            tiempos = [semaforo.tiempo_verde, semaforo.tiempo_amarillo, semaforo.tiempo_rojo]
            labels = ['Verde', 'Amarillo', 'Rojo']
            colors = ['green', 'yellow', 'red']
            ax.pie(tiempos, labels=labels, colors=colors, autopct='%1.1f%%')
            ax.set_title(f'Distribución de tiempos\nSemáforo {semaforo.id}')
            
            # Convertir gráfico a imagen codificada en base64
            img = io.BytesIO()
            plt.savefig(img, format='png', bbox_inches='tight')
            plt.close(fig)
            img.seek(0)
            img_str = base64.b64encode(img.read()).decode()
            
            # Añadir gráfico al popup
            popup_text += f'<img src="data:image/png;base64,{img_str}" width="300">'
        
        # Verificar que las coordenadas sean válidas para folium
        try:
            folium.Marker(
                [origen_lat, origen_lon],
                popup=folium.Popup(popup_text, max_width=400),
                tooltip=f"Intersección {interseccion.id}",
                icon=folium.Icon(icon='traffic-light', prefix='fa', color='blue')
            ).add_to(mapa)
        except ValueError as e:
            print(f"Error al crear marcador para la intersección {interseccion.id}: {e}")
            print(f"Coordenadas: lat={origen_lat}, lon={origen_lon}")
            continue
        
        # Dibujar líneas para conectar las intersecciones
        for conexion in interseccion.conexiones:
            if not conexion.coordenadas:
                continue
            
            # Aplicar la misma lógica de validación de coordenadas para la conexión
            try:
                if isinstance(conexion.coordenadas, dict):
                    keys = conexion.coordenadas.keys()
                    lat_key = next((k for k in keys if 'lat' in k.lower()), None)
                    lng_key = next((k for k in keys if 'lng' in k.lower() or 'lon' in k.lower()), None)
                    
                    if lat_key and lng_key:
                        destino_lat = float(conexion.coordenadas[lat_key])
                        destino_lon = float(conexion.coordenadas[lng_key])
                    else:
                        continue
                elif isinstance(conexion.coordenadas, (list, tuple)) and len(conexion.coordenadas) >= 2:
                    destino_lat = float(conexion.coordenadas[0])
                    destino_lon = float(conexion.coordenadas[1])
                else:
                    try:
                        destino_lat = float(conexion.coordenadas.latitude)
                        destino_lon = float(conexion.coordenadas.longitude)
                    except AttributeError:
                        continue
            except (ValueError, TypeError):
                continue
            
            # Obtener el flujo de tráfico para esta calle
            flujo_calle = 100  # Valor por defecto
            
            # Buscar el flujo real en los datos
            if (interseccion.id, conexion.id) in red_vial.flujos_calles:
                # Tomar el promedio de los tres periodos
                flujos = red_vial.flujos_calles[(interseccion.id, conexion.id)]
                flujo_calle = (flujos['mañana'] + flujos['tarde'] + flujos['noche']) / 3
            
            # Normalizar el flujo para obtener color
            flujo_norm = min(flujo_calle / flujo_max, 1.0) if flujo_max > 0 else 0.5
            color_calle = mcolors.to_hex(cmap(flujo_norm))
            
            # Añadir línea con grosor proporcional al flujo
            grosor = 2 + (flujo_norm * 8)  # Grosor entre 2 y 10
            
            try:
                folium.PolyLine(
                    [(origen_lat, origen_lon), (destino_lat, destino_lon)],
                    color=color_calle,
                    weight=grosor,
                    opacity=0.8,
                    popup=f"Flujo promedio: {flujo_calle:.1f} vehículos/h"
                ).add_to(mapa)
            except ValueError:
                continue
    
    # Añadir leyenda para flujo de tráfico
    leyenda_html = '''
    <div style="position: fixed; 
                bottom: 50px; left: 50px; width: 200px; height: 140px; 
                border:2px solid grey; z-index:9999; font-size:14px;
                background-color: white; padding: 10px;
                border-radius: 5px;">
        <p style="margin-top: 0; margin-bottom: 5px;"><b>Flujo de tráfico</b></p>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background-color: #ffffb2; width: 20px; height: 10px; margin-right: 5px;"></div>
            <div>Bajo</div>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background-color: #fecc5c; width: 20px; height: 10px; margin-right: 5px;"></div>
            <div>Medio</div>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <div style="background-color: #fd8d3c; width: 20px; height: 10px; margin-right: 5px;"></div>
            <div>Alto</div>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="background-color: #e31a1c; width: 20px; height: 10px; margin-right: 5px;"></div>
            <div>Muy alto</div>
        </div>
    </div>
    '''
    mapa.get_root().html.add_child(folium.Element(leyenda_html))
    
    # Guardar mapa a archivo HTML
    mapa.save(archivo_salida)
    print(f"Mapa guardado en {archivo_salida}")
    
    # Mostrar estadísticas de la solución
    if mejor_solucion:
        print("\nEstadísticas de la mejor solución:")
        print(f"Fitness: {mejor_solucion.fitness:.6f}")
        # Puedes calcular otras estadísticas aquí
    
    return mapa

def generar_visualizacion_comparativa(red_vial, soluciones, duracion_sim=3600):
    """
    Genera gráficos comparativos de las soluciones obtenidas por el algoritmo genético
    
    Parámetros:
    - red_vial: objeto RedVial 
    - soluciones: lista de objetos IndividuoAG (mejores soluciones)
    - duracion_sim: duración de la simulación en segundos
    """
    # Configuración inicial sin optimizar
    red_original = crear_red_original(red_vial)
    
    # Simular y obtener métricas para la configuración original
    tiempo_esp_original, congestion_original = simular_y_obtener_metricas(red_original, duracion_sim)

    # Fix: Ensure minimum values for metrics
    tiempo_esp_original = max(0.01, tiempo_esp_original)
    congestion_original = max(0.01, congestion_original)
    
    # Simular y obtener métricas para cada solución
    tiempos_espera = [tiempo_esp_original]
    congestiones = [congestion_original]
    etiquetas = ['Original']
    
    for i, solucion in enumerate(soluciones):
        red_tmp = aplicar_solucion(red_vial, solucion)
        tiempo_esp, congestion = simular_y_obtener_metricas(red_tmp, duracion_sim)
        
        # Fix: Ensure metrics are valid
        tiempo_esp = max(0.01, tiempo_esp)
        congestion = max(0.01, congestion)
        
        tiempos_espera.append(tiempo_esp)
        congestiones.append(congestion)
        etiquetas.append(f'Solución {i+1}')
    
    # Crear gráfico de tiempos de espera
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Gráfico de tiempos de espera
    colores = ['gray'] + [plt.cm.viridis(i/len(soluciones)) for i in range(len(soluciones))]
    
    ax1.bar(etiquetas, tiempos_espera, color=colores)
    ax1.set_title('Tiempo promedio de espera')
    ax1.set_ylabel('Tiempo (segundos)')
    ax1.tick_params(axis='x', rotation=45)

    # Fix: Only show improvement percentages if original time is meaningful
    if tiempo_esp_original > 0.1:  # Threshold for meaningful comparison
        for i in range(1, len(tiempos_espera)):
            if tiempos_espera[i] < tiempo_esp_original:  # Only show if there's improvement
                porcentaje = ((tiempo_esp_original - tiempos_espera[i]) / tiempo_esp_original) * 100
                ax1.text(i, tiempos_espera[i] + 1, f'{porcentaje:.1f}%↓', 
                        ha='center', va='bottom', fontweight='bold')
    
    # Gráfico de congestión
    ax2.bar(etiquetas, congestiones, color=colores)
    ax2.set_title('Nivel de congestión')
    ax2.set_ylabel('Vehículos en cola')
    ax2.tick_params(axis='x', rotation=45)
    
    # Fix: Only show improvement percentages if there's meaningful congestion
    if congestion_original > 1:  # Threshold for meaningful comparison
        for i in range(1, len(congestiones)):
            if congestiones[i] < congestion_original:  # Only show if there's improvement
                porcentaje = ((congestion_original - congestiones[i]) / congestion_original) * 100
                ax2.text(i, congestiones[i] + 1, f'{porcentaje:.1f}%↓', 
                        ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('comparativa_soluciones.png')
    
    print("Gráfico comparativo generado y guardado como 'comparativa_soluciones.png'")
    
    # Crear tabla de resultados
    crear_tabla_resultados(soluciones, tiempos_espera[1:], congestiones[1:], tiempo_esp_original, congestion_original)
    
    return fig

def crear_red_original(red_vial):
    """Crea una copia de la red vial con la configuración original de semáforos"""
    # Se debe implementar una copia profunda de la red vial aquí
    # Este es un ejemplo simplificado
    #return red_vial  # Asumiendo que la red vial actual es la original
    """
    Crea una copia profunda de la red vial con la configuración original de semáforos
    
    Parámetros:
    - red_vial: objeto RedVial con la configuración actual
    
    Retorna:
    - Una copia profunda de la red vial original
    """
    # Crear una copia profunda de la red vial
    red_copia = copy.deepcopy(red_vial)
    
    # Restaurar los tiempos originales de los semáforos
    for interseccion in red_copia.intersecciones:
        for semaforo in interseccion.semaforos:
            # Restaurar a valores típicos o los que consideres originales
            semaforo.tiempo_verde = 30
            semaforo.tiempo_amarillo = 3
            semaforo.tiempo_rojo = 30
            semaforo.desfase = 0
            semaforo.ciclo_total = semaforo.tiempo_verde + semaforo.tiempo_amarillo + semaforo.tiempo_rojo
    
    return red_copia

def aplicar_solucion(red_vial, solucion):
    """Aplica una solución del AG a una copia de la red vial y la retorna"""
    # Se debe implementar una copia profunda de la red vial aquí
    # y luego aplicar la solución
    # Este es un ejemplo simplificado
    #return red_vial  # Idealmente, retornaría una nueva instancia con la solución aplicada
    """
    Aplica una solución del AG a una copia de la red vial
    
    Parámetros:
    - red_vial: objeto RedVial original
    - solucion: objeto IndividuoAG con la solución a aplicar
    
    Retorna:
    - Una copia de la red vial con la solución aplicada
    """
    # Crear una copia profunda de la red vial
    red_copia = copy.deepcopy(red_vial)
    
    # Aplicar la solución a la copia
    semaforo_idx = 0
    for interseccion in red_copia.intersecciones:
        # Guardar los IDs originales
        ids_originales = [sem.id for sem in interseccion.semaforos]
        
        for i, _ in enumerate(interseccion.semaforos):
            if semaforo_idx < len(solucion.cromosoma):
                # Crear un nuevo semáforo con la configuración de la solución pero conservando el ID original
                nuevo_semaforo = Semaforo(
                    id=ids_originales[i],
                    tiempo_verde=solucion.cromosoma[semaforo_idx].tiempo_verde,
                    tiempo_amarillo=solucion.cromosoma[semaforo_idx].tiempo_amarillo,
                    tiempo_rojo=solucion.cromosoma[semaforo_idx].tiempo_rojo,
                    desfase=solucion.cromosoma[semaforo_idx].desfase
                )
                interseccion.semaforos[i] = nuevo_semaforo
                semaforo_idx += 1
    
    # Reiniciar las colas de vehículos
    for interseccion in red_copia.intersecciones:
        for semaforo_id in interseccion.cola_vehiculos:
            interseccion.cola_vehiculos[semaforo_id] = deque()
    
    return red_copia

def simular_y_obtener_metricas(red_vial, duracion_sim):
    """Simula el tráfico y retorna métricas de rendimiento"""
    # Reiniciar colas de vehículos
    for interseccion in red_vial.intersecciones:
        for semaforo_id in interseccion.cola_vehiculos:
            interseccion.cola_vehiculos[semaforo_id] = deque()
    
    # Simular llegadas con tasa promedio
    tasa_llegada = 2.0  # Ejemplo, ajustar según necesidad
    red_vial.simular_llegada_poisson(tasa_llegada, duracion_sim)
    
    # Simular tráfico
    tiempo_promedio, congestion = red_vial.simular_trafico(duracion_sim)

    # Garantizar que no haya valores nulos o negativos
    tiempo_promedio = max(0.01, tiempo_promedio)
    congestion = max(0.01, congestion)  # Evitar congestión cero

    print("Resultados de simular y obtener metricas.")
    print(tiempo_promedio)
    print(congestion)

    return tiempo_promedio, congestion

def crear_tabla_resultados(soluciones, tiempos_espera, congestiones, tiempo_original, congestion_original):
    # Crear estructura de datos para JSON
    resultados_json = {
        "soluciones": [
            {
                "nombre": "Original (sin optimizar)",
                "fitness": None,
                "tiempo_espera": tiempo_original,
                "mejora_tiempo": None,
                "congestion": congestion_original,
                "mejora_congestion": None
            }
        ]
    }
    
    # Agregar datos de cada solución al JSON
    for i, solucion in enumerate(soluciones):
        mejora_tiempo = ((tiempo_original - tiempos_espera[i]) / tiempo_original) * 100 if tiempo_original > 0 else 0
        mejora_congestion = ((congestion_original - congestiones[i]) / congestion_original) * 100 if congestion_original > 0 else 0
        
        resultados_json["soluciones"].append({
            "nombre": f"Solución {i+1}",
            "fitness": float(solucion.fitness),
            "tiempo_espera": float(tiempos_espera[i]),
            "mejora_tiempo": float(mejora_tiempo),
            "congestion": float(congestiones[i]),
            "mejora_congestion": float(mejora_congestion)
        })
    
    # Guardar JSON
    with open('resultados_optimizacion.json', 'w', encoding='utf-8') as f:
        json.dump(resultados_json, f, indent=4, ensure_ascii=False)
    
    print("Resultados guardados en formato JSON en 'resultados_optimizacion.json'")
    
    # Generar HTML como antes
    html = """
    <html>
    <head>
        <style>
            table {{
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
            }}
            th, td {{
                text-align: left;
                padding: 8px;
                border: 1px solid #ddd;
            }}
            th {{
                background-color: #4CAF50;
                color: white;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .mejora {{
                color: green;
                font-weight: bold;
            }}
            .empeora {{
                color: red;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h2>Comparativa de Soluciones para Optimización de Semáforos</h2>
        <table>
            <tr>
                <th>Solución</th>
                <th>Fitness</th>
                <th>Tiempo de Espera (s)</th>
                <th>Mejora en Tiempo</th>
                <th>Congestión (vehículos)</th>
                <th>Mejora en Congestión</th>
            </tr>
            <tr>
                <td>Original (sin optimizar)</td>
                <td>-</td>
                <td>{:.2f}</td>
                <td>-</td>
                <td>{:.2f}</td>
                <td>-</td>
            </tr>
    """.format(tiempo_original, congestion_original)

    for i, solucion in enumerate(soluciones):
        # Fix: Handle edge case with appropriate checks
        if tiempo_original > 0:  # Only calculate if original value is meaningful
            mejora_tiempo = ((tiempo_original - tiempos_espera[i]) / tiempo_original) * 100
            clase_tiempo = "mejora" if mejora_tiempo > 0 else "empeora"
            # Replace Unicode arrow with HTML entity
            texto_tiempo = "{:.2f}%{}".format(abs(mejora_tiempo), "&darr;" if mejora_tiempo > 0 else "&uarr;")
        else:
            mejora_tiempo = 0
            clase_tiempo = ""
            texto_tiempo = "N/A"

        # Fix: Handle edge case with appropriate checks
        if congestion_original > 0:  # Only calculate if original value is meaningful
            mejora_congestion = ((congestion_original - congestiones[i]) / congestion_original) * 100
            clase_congestion = "mejora" if mejora_congestion > 0 else "empeora"
            # Replace Unicode arrow with HTML entity
            texto_congestion = "{:.2f}%{}".format(abs(mejora_congestion), "&darr;" if mejora_congestion > 0 else "&uarr;")
        else:
            mejora_congestion = 0
            clase_congestion = ""
            texto_congestion = "N/A"
        
        html += """
            <tr>
                <td>Solución {}</td>
                <td>{:.6f}</td>
                <td>{:.2f}</td>
                <td class="{}">{}</td>
                <td>{:.2f}</td>
                <td class="{}">{}</td>
            </tr>
        """.format(i+1, solucion.fitness, tiempos_espera[i], clase_tiempo, texto_tiempo, 
                  congestiones[i], clase_congestion, texto_congestion)
    
    html += """
        </table>
        <p><i>Nota: Los valores de tiempo de espera son segundos promedio por vehículo.
        La congestión representa el número promedio de vehículos en cola.</i></p>
    </body>
    </html>
    """
    
    # Explicitly specify UTF-8 encoding when writing the file
    with open('resultados_optimizacion.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("Tabla de resultados generada y guardada como 'resultados_optimizacion.html'")

def visualizar_resultados_completos(red_vial, mejores_soluciones):
    """Función principal para generar todas las visualizaciones de resultados"""
    # 1. Generar mapa con la mejor solución
    mapa = visualizar_red_vial(red_vial, mejores_soluciones[0], 'mapa_mejor_solucion.html')
    
    # 2. Generar mapa para comparar estado original
    mapa_original = visualizar_red_vial(crear_red_original(red_vial), None, 'mapa_original.html')
    
    # 3. Generar gráficos comparativos
    grafico = generar_visualizacion_comparativa(red_vial, mejores_soluciones)
    
    # 4. Visualizar las tres mejores soluciones (opcional)
    for i, solucion in enumerate(mejores_soluciones[:3]):
        visualizar_red_vial(red_vial, solucion, f'mapa_solucion_{i+1}.html')
    
    print("\nVisualización completa de resultados generada con éxito.")
    print("Archivos generados:")
    print("- mapa_mejor_solucion.html (Mapa con la mejor configuración)")
    print("- mapa_original.html (Mapa con la configuración original)")
    print("- comparativa_soluciones.png (Gráfico comparativo)")
    print("- resultados_optimizacion.html (Tabla de resultados)")

    for i in range(min(3, len(mejores_soluciones))):
        print(f"- mapa_solucion_{i+1}.html (Mapa con la solución #{i+1})")

# Modificar la función main para incluir la visualización
def main():
    # Cargar red vial desde JSON
    red_vial = cargar_red_vial("zona_delimitada.json")
    
    # Configurar y ejecutar algoritmo genético
    ag = AlgoritmoGenetico(
        tamaño_poblacion=50,
        num_semaforos=len([s for i in red_vial.intersecciones for s in i.semaforos]),
        red_vial=red_vial,
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
    
    # Generar visualizaciones completas
    visualizar_resultados_completos(red_vial, mejores)

if __name__ == "__main__":
    main()