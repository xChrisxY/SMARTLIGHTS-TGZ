import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
try:
    from PIL import ImageResampling
    LANCZOS = ImageResampling.LANCZOS
except ImportError:
    # Para versiones antiguas de Pillow
    LANCZOS = Image.LANCZOS
import os
import json
import webbrowser
from models.algoritmo_genetico import AlgoritmoGenetico
from services.utils import crear_red_original, visualizar_resultados_completos, visualizar_red_vial, cargar_red_vial

class TrafficOptimizationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Optimización de Semáforos - Algoritmo Genético")
        self.root.geometry("1200x800")
        
        # Configuración de tema
        ctk.set_appearance_mode("Dark")  # Puede ser "Dark", "Light" o "System"
        ctk.set_default_color_theme("dark-blue")  # Temas: "blue", "green", "dark-blue"
        
        # Variables de control
        self.json_path = ctk.StringVar()
        self.population_size = ctk.IntVar(value=50)
        self.crossover_prob = ctk.DoubleVar(value=0.8)
        self.mutation_prob = ctk.DoubleVar(value=0.1)
        self.elitism_rate = ctk.DoubleVar(value=0.05)
        self.max_generations = ctk.IntVar(value=100)
        self.simulation_time = ctk.IntVar(value=3600)
        self.arrival_rate = ctk.DoubleVar(value=0.2)
        
        # Resultados
        self.best_solutions = []
        self.red_vial = None
        
        # Crear interfaz
        self.create_widgets()
    
    def create_widgets(self):
        # Frame principal
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Panel de configuración (izquierda)
        config_frame = ctk.CTkFrame(main_frame, width=400)
        config_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        # Panel de resultados (derecha)
        results_frame = ctk.CTkFrame(main_frame)
        results_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # Configuración del archivo JSON
        ctk.CTkLabel(config_frame, text="Configuración de Red Vial", font=("Arial", 14, "bold")).pack(pady=5)
        
        file_frame = ctk.CTkFrame(config_frame)
        file_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(file_frame, text="Archivo JSON:").pack(side="left", padx=5)
        ctk.CTkEntry(file_frame, textvariable=self.json_path, width=250).pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(file_frame, text="Examinar", width=80, command=self.select_json_file).pack(side="right", padx=5)
        
        # Parámetros del algoritmo genético
        ctk.CTkLabel(config_frame, text="Parámetros del Algoritmo Genético", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.create_parameter_slider(config_frame, "Tamaño de población:", self.population_size, 10, 200)
        self.create_parameter_slider(config_frame, "Prob. de cruce:", self.crossover_prob, 0.0, 1.0)
        self.create_parameter_slider(config_frame, "Prob. de mutación:", self.mutation_prob, 0.0, 1.0)
        self.create_parameter_slider(config_frame, "Tasa de elitismo:", self.elitism_rate, 0.0, 0.5)
        self.create_parameter_slider(config_frame, "Máx. generaciones:", self.max_generations, 10, 500)
        
        # Parámetros de simulación
        ctk.CTkLabel(config_frame, text="Parámetros de Simulación", font=("Arial", 14, "bold")).pack(pady=5)
        
        self.create_parameter_slider(config_frame, "Duración simulación (s):", self.simulation_time, 60, 7200)
        self.create_parameter_slider(config_frame, "Tasa de llegada:", self.arrival_rate, 0.01, 2.0)
        
        # Botón de ejecución
        ctk.CTkButton(config_frame, text="Ejecutar Optimización", command=self.run_optimization, 
                      font=("Arial", 12, "bold"), height=40).pack(pady=20, fill="x")
        
        # Panel de resultados
        self.results_text = ctk.CTkTextbox(results_frame, wrap="word", font=("Consolas", 12))
        self.results_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Panel de visualización
        self.image_label = ctk.CTkLabel(results_frame, text="")
        self.image_label.pack(pady=5)
        
        # Botones para visualizar resultados
        buttons_frame = ctk.CTkFrame(results_frame)
        buttons_frame.pack(fill="x", pady=5)
        
        ctk.CTkButton(buttons_frame, text="Ver Mapa Original", command=self.show_original_map).pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(buttons_frame, text="Ver Mapa Optimizado", command=self.show_optimized_map).pack(side="left", padx=5, fill="x", expand=True)
        ctk.CTkButton(buttons_frame, text="Ver Comparativa", command=self.show_comparison).pack(side="left", padx=5, fill="x", expand=True)
    
    def create_parameter_slider(self, parent, label_text, variable, from_, to):
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(frame, text=label_text).pack(side="left", padx=5)
        
        if isinstance(from_, int):
            slider = ctk.CTkSlider(frame, variable=variable, from_=from_, to=to, number_of_steps=to-from_)
            entry = ctk.CTkEntry(frame, textvariable=variable, width=60)
        else:
            slider = ctk.CTkSlider(frame, variable=variable, from_=from_, to=to)
            entry = ctk.CTkEntry(frame, textvariable=variable, width=60)
        
        slider.pack(side="left", fill="x", expand=True, padx=5)
        entry.pack(side="right", padx=5)
    
    def select_json_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            self.json_path.set(file_path)
    
    def run_optimization(self):
        if not self.json_path.get():
            messagebox.showerror("Error", "Por favor seleccione un archivo JSON")
            return
        
        try:
            # Cargar red vial
            self.red_vial = cargar_red_vial(self.json_path.get())
            
            # Configurar algoritmo genético
            ag = AlgoritmoGenetico(
                tamaño_poblacion=self.population_size.get(),
                num_semaforos=len([s for i in self.red_vial.intersecciones for s in i.semaforos]),
                red_vial=self.red_vial,
                prob_cruce=self.crossover_prob.get(),
                prob_mutacion=self.mutation_prob.get(),
                elitismo=self.elitism_rate.get(),
                max_generaciones=self.max_generations.get()
            )
            
            # Ejecutar optimización
            self.results_text.delete("1.0", "end")
            self.results_text.insert("end", "Iniciando optimización...\n")
            self.root.update()
            
            ag.ejecutar()
            ag.graficar_evolucion()
            
            # Obtener resultados
            self.best_solutions = ag.obtener_mejores_soluciones(3)
            
            # Mostrar resultados
            self.results_text.delete("1.0", "end")
            self.results_text.insert("end", "Optimización completada!\n\n")
            self.results_text.insert("end", f"Mejor fitness: {ag.mejor_individuo.fitness:.6f}\n\n")
            
            for i, sol in enumerate(self.best_solutions):
                self.results_text.insert("end", f"Solución #{i+1} (Fitness: {sol.fitness:.6f}):\n")
                for semaforo in sol.cromosoma:
                    self.results_text.insert("end", f"  {semaforo}\n")
                self.results_text.insert("end", "\n")
            
            # Mostrar gráfico de evolución
            self.show_evolution_graph()
            
            # Generar visualizaciones
            visualizar_resultados_completos(self.red_vial, self.best_solutions)
            
            messagebox.showinfo("Éxito", "Optimización completada correctamente")
            
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error:\n{str(e)}")
    
    def show_evolution_graph(self):
        try:
            img = Image.open('evolucion_fitness.png')
            img = img.resize((800, 400), Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(img)
            
            self.image_label.configure(image=img_tk)
            self.image_label.image = img_tk
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el gráfico:\n{str(e)}")
    
    def show_original_map(self):
        if not self.red_vial:
            messagebox.showerror("Error", "Primero ejecute la optimización")
            return
        
        try:
            visualizar_red_vial(crear_red_original(self.red_vial), None, 'mapa_original.html')
            webbrowser.open('file://' + os.path.abspath('mapa_original.html'))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el mapa:\n{str(e)}")
    
    def show_optimized_map(self):
        if not self.best_solutions:
            messagebox.showerror("Error", "Primero ejecute la optimización")
            return
        
        try:
            visualizar_red_vial(self.red_vial, self.best_solutions[0], 'mapa_mejor_solucion.html')
            webbrowser.open('file://' + os.path.abspath('mapa_mejor_solucion.html'))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el mapa:\n{str(e)}")
    
    def show_comparison(self):
        if not self.best_solutions:
            messagebox.showerror("Error", "Primero ejecute la optimización")
            return
        
        try:
            webbrowser.open('file://' + os.path.abspath('resultados_optimizacion.html'))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la comparativa:\n{str(e)}")

if __name__ == "__main__":
    root = ctk.CTk()
    app = TrafficOptimizationApp(root)
    root.mainloop()