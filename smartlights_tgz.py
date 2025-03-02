#!/usr/bin/env python3 

import numpy as np
import random

# Parámetros globales
POPULATION_SIZE = 10
CYCLE_TIME = 120  # Tiempo total del ciclo en segundos
NUM_INTERSECTIONS = 5  # Número de intersecciones
MUTATION_RATE = 0.1  # Probabilidad de mutación

# Tasas de llegada (λ) para cada intersección (vehículos/segundo)
LAMBDA = [0.5, 0.8, 0.6, 0.4, 0.7]

# Generación inicial
population = [np.random.randint(1, CYCLE_TIME // 2, size=NUM_INTERSECTIONS) for _ in range(POPULATION_SIZE)]

def simulate_flows(lambda_rates, duration):
    """
    Genera un flujo de vehículos para cada intersección usando una distribución Poisson.
    
    Args:
        lambda_rates (list): Tasas de llegada para cada intersección (vehículos/segundo).
        duration (int): Duración del periodo de simulación en segundos.

    Returns:
        list: Lista de flujos simulados para cada intersección.
    """
    return [np.random.poisson(lam=l * duration) for l in lambda_rates]

def evaluate_fitness(individual):
    """
    Calcula el fitness de un individuo basado en el tiempo promedio de espera.

    Args:
        individual (list): Tiempos de luz roja para cada intersección.

    Returns:
        float: Valor de fitness (tiempo promedio de espera).
    """
    total_wait_time = 0

    # Simulación de flujos dinámicos (vehículos que llegan en un periodo)
    simulated_flows = simulate_flows(LAMBDA, CYCLE_TIME)

    for i, red_time in enumerate(individual):
        green_time = CYCLE_TIME - red_time

        if green_time <= 0 or red_time <= 0:
            return float('inf')  # Penalización por tiempos inválidos

        # Tiempo promedio de espera (W = λ * T_red / 2 * T_green)
        lambda_i = LAMBDA[i]
        vehicles = simulated_flows[i]
        wait_time = (vehicles * red_time) / (2 * green_time)
        total_wait_time += wait_time

    return total_wait_time

def tournament_selection(population, fitness_values, tournament_size=3):
    """
    Selección por torneo para elegir un individuo.

    Args:
        population (list): Población actual.
        fitness_values (list): Valores de fitness de la población.
        tournament_size (int): Tamaño del torneo.

    Returns:
        list: Individuo seleccionado.
    """
    selected_indices = random.sample(range(len(population)), tournament_size)
    best_index = min(selected_indices, key=lambda idx: fitness_values[idx])
    return population[best_index]

def crossover(parent1, parent2):
    """
    Cruza de un punto para generar descendencia.

    Args:
        parent1 (list): Primer padre.
        parent2 (list): Segundo padre.

    Returns:
        list: Descendencia generada.
    """
    point = random.randint(1, NUM_INTERSECTIONS - 1)
    return np.concatenate((parent1[:point], parent2[point:]))

def mutate(individual):
    """
    Mutación de un individuo modificando aleatoriamente un gen.

    Args:
        individual (list): Individuo a mutar.

    Returns:
        list: Individuo mutado.
    """
    if random.random() < MUTATION_RATE:
        index = random.randint(0, NUM_INTERSECTIONS - 1)
        individual[index] = random.randint(1, CYCLE_TIME // 2)
    return individual

def generate_new_population(population, fitness_values):
    """
    Genera una nueva población mediante selección, cruza y mutación.

    Args:
        population (list): Población actual.
        fitness_values (list): Valores de fitness de la población.

    Returns:
        list: Nueva población.
    """
    new_population = []

    for _ in range(POPULATION_SIZE):
        parent1 = tournament_selection(population, fitness_values)
        parent2 = tournament_selection(population, fitness_values)
        offspring = crossover(parent1, parent2)
        offspring = mutate(offspring)
        new_population.append(offspring)

    return new_population

# Evaluar la población inicial
fitness_values = [evaluate_fitness(individual) for individual in population]

# Generar nueva población
new_population = generate_new_population(population, fitness_values)
new_fitness_values = [evaluate_fitness(individual) for individual in new_population]

# Mostrar resultados iniciales y de la nueva generación
print("Población Inicial:")
for i, (individual, fitness) in enumerate(zip(population, fitness_values)):
    print(f"Individuo {i + 1}: {individual}, Fitness: {fitness:.2f}")

print("\nNueva Población:")
for i, (individual, fitness) in enumerate(zip(new_population, new_fitness_values)):
    print(f"Individuo {i + 1}: {individual}, Fitness: {fitness:.2f}")

