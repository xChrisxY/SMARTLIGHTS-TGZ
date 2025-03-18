import json
from models.algoritmo_genetico import AlgoritmoGenetico
from models.interseccion import Interseccion
from models.red_vial import RedVial
from models.semaforo import Semaforo
from services.generate_results import GenerateResults

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
            
    resultados = GenerateResults()
    
    # Generar visualizaciones completas
    resultados.visualizar_resultados_completos(red_vial, mejores)

if __name__ == "__main__":
    main()