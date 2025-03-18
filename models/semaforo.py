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