from models.semaforo import Semaforo
import base64
import folium
from matplotlib.cm import get_cmap
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import io
from collections import deque
import copy

class GenerateResults:
  
    def visualizar_red_vial(self, red_vial, mejor_solucion=None, archivo_salida='mapa_semaforos.html'):
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

        

 
    def crear_red_original(self, red_vial):
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
        

    def simular_y_obtener_metricas(self, red_vial, duracion_sim):
        """Simula el tráfico y retorna métricas de rendimiento"""
        # Reiniciar colas de vehículos
        for interseccion in red_vial.intersecciones:
            for semaforo_id in interseccion.cola_vehiculos:
                interseccion.cola_vehiculos[semaforo_id] = deque()
        
        # Simular llegadas con tasa promedio
        tasa_llegada = 0.4  # Ejemplo, ajustar según necesidad
        red_vial.simular_llegada_poisson(tasa_llegada, duracion_sim)
        
        # Simular tráfico
        tiempo_promedio, congestion = red_vial.simular_trafico(duracion_sim)

        # Garantizar que no haya valores nulos o negativos
        tiempo_promedio = max(0.01, tiempo_promedio)
        congestion = max(0.01, congestion)  # Evitar congestión cero
        
        return tiempo_promedio, congestion

    def aplicar_solucion(self, red_vial, solucion):
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

    def generar_visualizacion_comparativa(self, red_vial, soluciones, duracion_sim=3600):
        """
        Genera gráficos comparativos de las soluciones obtenidas por el algoritmo genético
        
        Parámetros:
        - red_vial: objeto RedVial 
        - soluciones: lista de objetos IndividuoAG (mejores soluciones)
        - duracion_sim: duración de la simulación en segundos
        """
        # Configuración inicial sin optimizar
        red_original = self.crear_red_original(red_vial)
        
        # Simular y obtener métricas para la configuración original
        tiempo_esp_original, congestion_original = self.simular_y_obtener_metricas(red_original, duracion_sim)

        # Fix: Ensure minimum values for metrics
        tiempo_esp_original = max(0.01, tiempo_esp_original)
        congestion_original = max(0.01, congestion_original)
        
        # Simular y obtener métricas para cada solución
        tiempos_espera = [tiempo_esp_original]
        congestiones = [congestion_original]
        etiquetas = ['Original']
        
        for i, solucion in enumerate(soluciones):
            red_tmp = self.aplicar_solucion(red_vial, solucion)
            tiempo_esp, congestion = self.simular_y_obtener_metricas(red_tmp, duracion_sim)
            
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
        self.crear_tabla_resultados(soluciones, tiempos_espera[1:], congestiones[1:], tiempo_esp_original, congestion_original)
        
        return fig


    def crear_tabla_resultados(self,soluciones, tiempos_espera, congestiones, tiempo_original, congestion_original):
        
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
            if tiempo_original > 0.1:  # Only calculate if original value is meaningful
                mejora_tiempo = ((tiempo_original - tiempos_espera[i]) / tiempo_original) * 100
                clase_tiempo = "mejora" if mejora_tiempo > 0 else "empeora"
                texto_tiempo = "{:.2f}%{}".format(abs(mejora_tiempo), "↓" if mejora_tiempo > 0 else "↑")
            else:
                mejora_tiempo = 0
                clase_tiempo = ""
                texto_tiempo = "N/A"
            
            # Fix: Handle edge case with appropriate checks
            if congestion_original > 1:  # Only calculate if original value is meaningful
                mejora_congestion = ((congestion_original - congestiones[i]) / congestion_original) * 100
                clase_congestion = "mejora" if mejora_congestion > 0 else "empeora"
                texto_congestion = "{:.2f}%{}".format(abs(mejora_congestion), "↓" if mejora_congestion > 0 else "↑")
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
        
        with open('resultados_optimizacion.html', 'w') as f:
            f.write(html)
        
        print("Tabla de resultados generada y guardada como 'resultados_optimizacion.html'")

    def visualizar_resultados_completos(self, red_vial, mejores_soluciones):
        """Función principal para generar todas las visualizaciones de resultados"""
        # 1. Generar mapa con la mejor solución
        mapa = self.visualizar_red_vial(red_vial, mejores_soluciones[0], 'mapa_mejor_solucion.html')
        
        # 2. Generar mapa para comparar estado original
        mapa_original = self.visualizar_red_vial(self.crear_red_original(red_vial), None, 'mapa_original.html')
        
        # 3. Generar gráficos comparativos
        grafico = self.generar_visualizacion_comparativa(red_vial, mejores_soluciones)
        
        # 4. Visualizar las tres mejores soluciones (opcional)
        for i, solucion in enumerate(mejores_soluciones[:3]):
            self.visualizar_red_vial(red_vial, solucion, f'mapa_solucion_{i+1}.html')
        
        print("\nVisualización completa de resultados generada con éxito.")
        print("Archivos generados:")
        print("- mapa_mejor_solucion.html (Mapa con la mejor configuración)")
        print("- mapa_original.html (Mapa con la configuración original)")
        print("- comparativa_soluciones.png (Gráfico comparativo)")
        print("- resultados_optimizacion.html (Tabla de resultados)")
        for i in range(min(3, len(mejores_soluciones))):
            print(f"- mapa_solucion_{i+1}.html (Mapa con la solución #{i+1})")