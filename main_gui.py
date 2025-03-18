import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import os
from services.generate_results import GenerateResults
from models.algoritmo_genetico import AlgoritmoGenetico
from models.interseccion import Interseccion
from models.red_vial import RedVial
from models.semaforo import Semaforo
import json

# Configuración de CustomTkinter
ctk.set_appearance_mode("System")  # Puedes cambiar a "Dark" o "Light"
ctk.set_default_color_theme("blue")  # Temas: "blue", "green", "dark-blue"

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

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Optimización de Semáforos")
        self.root.geometry("1000x800")
        
        # Variables de control
        self.archivo_json = ctk.StringVar()
        self.tamaño_poblacion = ctk.IntVar(value=50)
        self.prob_cruce = ctk.DoubleVar(value=0.8)
        self.prob_mutacion = ctk.DoubleVar(value=0.1)
        self.elitismo = ctk.DoubleVar(value=0.05)
        self.max_generaciones = ctk.IntVar(value=100)
        
        # Crear widgets
        self.crear_widgets()
        
    def crear_widgets(self):
        # Frame principal
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Selección de archivo JSON
        ctk.CTkLabel(main_frame, text="Archivo JSON:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(main_frame, textvariable=self.archivo_json, width=400).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(main_frame, text="Buscar", command=self.seleccionar_archivo).grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        # Parámetros del algoritmo genético
        ctk.CTkLabel(main_frame, text="Tamaño de la población:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(main_frame, textvariable=self.tamaño_poblacion).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(main_frame, text="Probabilidad de cruce:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(main_frame, textvariable=self.prob_cruce).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(main_frame, text="Probabilidad de mutación:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(main_frame, textvariable=self.prob_mutacion).grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(main_frame, text="Elitismo:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(main_frame, textvariable=self.elitismo).grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(main_frame, text="Máximo de generaciones:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(main_frame, textvariable=self.max_generaciones).grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        
        # Botón para ejecutar la simulación
        ctk.CTkButton(main_frame, text="Ejecutar Simulación", command=self.ejecutar_simulacion).grid(row=6, column=0, columnspan=3, pady=10)
        
        # Área para mostrar resultados
        self.resultados_text = ctk.CTkTextbox(main_frame, height=150, width=800)
        self.resultados_text.grid(row=7, column=0, columnspan=3, padx=5, pady=10, sticky="ew")
        
        # Área para mostrar gráficos
        self.grafico_label = ctk.CTkLabel(main_frame, text="")
        self.grafico_label.grid(row=8, column=0, columnspan=3, padx=5, pady=10, sticky="ew")
        
    def seleccionar_archivo(self):
        archivo = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if archivo:
            self.archivo_json.set(archivo)
    
    def ejecutar_simulacion(self):
        if not self.archivo_json.get():
            messagebox.showerror("Error", "Por favor, selecciona un archivo JSON.")
            return
        
        try:
            # Cargar red vial desde JSON
            red_vial = cargar_red_vial(self.archivo_json.get())
            
            # Configurar y ejecutar algoritmo genético
            ag = AlgoritmoGenetico(
                tamaño_poblacion=self.tamaño_poblacion.get(),
                num_semaforos=len([s for i in red_vial.intersecciones for s in i.semaforos]),
                red_vial=red_vial,
                prob_cruce=self.prob_cruce.get(),
                prob_mutacion=self.prob_mutacion.get(),
                elitismo=self.elitismo.get(),
                max_generaciones=self.max_generaciones.get()
            )
            
            # Ejecutar algoritmo
            ag.ejecutar()
            
            # Graficar evolución
            ag.graficar_evolucion()
            
            # Obtener mejores soluciones
            mejores = ag.obtener_mejores_soluciones(3)
            
            # Mostrar resultados en el área de texto
            self.resultados_text.delete("1.0", "end")
            self.resultados_text.insert("end", "Las tres mejores soluciones:\n")
            for i, sol in enumerate(mejores):
                self.resultados_text.insert("end", f"\nSolución #{i+1} (Fitness: {sol.fitness:.6f}):\n")
                for semaforo in sol.cromosoma:
                    self.resultados_text.insert("end", f"{semaforo}\n")
            
            # Mostrar gráfico de evolución
            img = Image.open('evolucion_fitness.png')
            img = img.resize((800, 400), Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)
            self.grafico_label.configure(image=img_tk)
            self.grafico_label.image = img_tk
            
            # Generar visualizaciones completas
            resultados = GenerateResults()
            resultados.visualizar_resultados_completos(red_vial, mejores)
            
            messagebox.showinfo("Éxito", "Simulación completada con éxito.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error durante la simulación: {str(e)}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = App(root)
    root.mainloop()