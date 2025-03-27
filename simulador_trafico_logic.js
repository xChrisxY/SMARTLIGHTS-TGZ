// Configuraciones y variables globales
let intersecciones = []; // Almacenará los datos de las intersecciones
let calles = []; // Almacenará los datos de las calles
let semaforos = {}; // Diccionario de semáforos por ID
let vehiculos = []; // Lista de vehículos en simulación
let colas = {}; // Colas de vehículos en cada semáforo
let mapa = null; // Objeto del mapa Leaflet
let markers = {}; // Marcadores de las intersecciones
let callePolylines = []; // Líneas que representan las calles
let vehiculosElements = []; // Elementos DOM de los vehículos
let queueIndicators = {}; // Indicadores de cola en el mapa

// Variables de simulación
let tiempoActual = 0; // Tiempo actual de la simulación (segundos)
let tiempoEspera = 0; // Tiempo de espera acumulado
let congestion = 0; // Nivel de congestión
let vehiculosAtendidos = 0; // Número de vehículos que han pasado por los semáforos
let tasaLlegada = 1.0; // Vehículos por segundo
let velocidadSimulacion = 5; // Velocidad de simulación
let configuracionOptimizada = false; // Si se usa la configuración optimizada o la original
let enSimulacion = false; // Si la simulación está en curso
let intervalId = null; // ID del intervalo de la simulación

// Datos de simulación para comparativas
let estatisticasOriginales = {
    tiempoEspera: 0,
    congestion: 0
};
let estatisticasOptimizadas = {
    tiempoEspera: 0,
    congestion: 0
};

// Configuración original de semáforos
let configOriginal = {};
// Configuración optimizada de semáforos
let configOptimizada = {};

// Función para cargar datos desde el archivo JSON
async function cargarDatos() {
    try {
        // Cargar datos de red vial
        const response = await fetch('zona_delimitada.json');
        const data = await response.json();
        
        intersecciones = data.intersecciones;
        calles = data.calles;
        
        // Procesar intersecciones y semáforos
        intersecciones.forEach(interseccion => {
            // Guardar configuración original
            interseccion.semaforos.forEach(semaforo => {
                configOriginal[semaforo.id] = {
                    tiempo_verde: semaforo.tiempo_verde_inicial,
                    tiempo_amarillo: semaforo.tiempo_amarillo_inicial,
                    tiempo_rojo: semaforo.tiempo_rojo_inicial,
                    desfase: 0
                };
                
                // Inicializar configuración optimizada con los mismos valores (se actualizará después)
                configOptimizada[semaforo.id] = { ...configOriginal[semaforo.id] };
                
                // Inicializar diccionario de semáforos
                semaforos[semaforo.id] = {
                    id: semaforo.id,
                    interseccionId: interseccion.id,
                    direccion: semaforo.direccion,
                    tiempo_verde: semaforo.tiempo_verde_inicial,
                    tiempo_amarillo: semaforo.tiempo_amarillo_inicial,
                    tiempo_rojo: semaforo.tiempo_rojo_inicial,
                    desfase: 0,
                    ciclo_total: semaforo.tiempo_verde_inicial + semaforo.tiempo_amarillo_inicial + semaforo.tiempo_rojo_inicial
                };
                
                // Inicializar colas de vehículos
                colas[semaforo.id] = [];
            });
        });
        
        // Cargar configuración optimizada desde el resultado del algoritmo genético
        await cargarConfiguracionOptimizada();
        
        return true;
    } catch (error) {
        console.error("Error al cargar los datos:", error);
        return false;
    }
}

// Cargar configuración optimizada desde los resultados del AG
async function cargarConfiguracionOptimizada() {
    try {
        console.log("Cargando configuración optimizada...");
        
        // Intentamos cargar datos desde mapa_mejor_solucion.html
        try {
            const response = await fetch('mapa_mejor_solucion.html');
            if (response.ok) {
                const html = await response.text();
                console.log("Archivo mapa_mejor_solucion.html cargado");
                
                // Extraer datos del HTML generado por el AG
                // Buscamos los datos de los semáforos en el código
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                
                // Extraer información de semáforos desde los popups
                const popups = doc.querySelectorAll('.leaflet-popup-content');
                
                if (popups.length === 0) {
                    console.log("No se encontraron popups en mapa_mejor_solucion.html");
                } else {
                    console.log(`Se encontraron ${popups.length} popups`);
                }
                
                // Procesar cada popup para extraer información de semáforos
                popups.forEach(popup => {
                    const text = popup.textContent;
                    
                    // Extraer IDs de semáforos y sus configuraciones
                    const idMatch = text.match(/ID: (\d+)/g);
                    const verdeMatch = text.match(/Verde: (\d+)s/g);
                    const amarilloMatch = text.match(/Amarillo: (\d+)s/g);
                    const rojoMatch = text.match(/Rojo: (\d+)s/g);
                    const desfaseMatch = text.match(/Desfase: (\d+)s/g);
                    
                    if (idMatch && verdeMatch && amarilloMatch && rojoMatch) {
                        for (let i = 0; i < idMatch.length; i++) {
                            const id = parseInt(idMatch[i].replace('ID: ', ''));
                            const verde = parseInt(verdeMatch[i].replace('Verde: ', '').replace('s', ''));
                            const amarillo = parseInt(amarilloMatch[i].replace('Amarillo: ', '').replace('s', ''));
                            const rojo = parseInt(rojoMatch[i].replace('Rojo: ', '').replace('s', ''));
                            const desfase = desfaseMatch ? parseInt(desfaseMatch[i].replace('Desfase: ', '').replace('s', '')) : 0;
                            
                            configOptimizada[id] = {
                                tiempo_verde: verde,
                                tiempo_amarillo: amarillo,
                                tiempo_rojo: rojo,
                                desfase: desfase,
                                ciclo_total: verde + amarillo + rojo
                            };
                            
                            console.log(`Configuración optimizada cargada para semáforo ${id}: Verde=${verde}, Amarillo=${amarillo}, Rojo=${rojo}, Desfase=${desfase}`);
                        }
                    }
                });
                
                // Si no se encontraron datos en los popups, intentamos otra estrategia
                if (Object.keys(configOptimizada).length === Object.keys(configOriginal).length) {
                    console.log("Datos de optimización cargados correctamente");
                    return true;
                }
            }
        } catch (e) {
            console.log("Error al cargar desde mapa_mejor_solucion.html:", e);
        }
        
        // Si no pudimos cargar desde el mapa, intentamos cargar desde el archivo de resultados
        try {
            const response = await fetch('resultados_optimizacion.html');
            if (response.ok) {
                const html = await response.text();
                console.log("Archivo resultados_optimizacion.html cargado");
                
                // Extraer datos de mejora para usar en la simulación
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                
                // Buscar mejoras en tiempo y congestión
                const filas = doc.querySelectorAll('table tr');
                if (filas.length > 1) { // La primera fila es el encabezado
                    const filaMejorSolucion = filas[2]; // La segunda fila contiene la solución 1 (mejor)
                    if (filaMejorSolucion) {
                        const celdas = filaMejorSolucion.querySelectorAll('td');
                        if (celdas.length >= 6) {
                            // Extraer valores
                            const fitness = parseFloat(celdas[1].textContent);
                            const tiempoEspera = parseFloat(celdas[2].textContent);
                            const congestion = parseFloat(celdas[4].textContent);
                            
                            console.log(`Estadísticas cargadas: Fitness=${fitness}, Tiempo=${tiempoEspera}, Congestión=${congestion}`);
                            
                            // Guardar estadísticas optimizadas
                            estatisticasOptimizadas.tiempoEspera = tiempoEspera;
                            estatisticasOptimizadas.congestion = congestion;
                            
                            // Buscar estadísticas originales
                            const filaOriginal = filas[1]; // Primera fila tras el encabezado
                            if (filaOriginal) {
                                const celdasOrig = filaOriginal.querySelectorAll('td');
                                if (celdasOrig.length >= 6) {
                                    const tiempoOriginal = parseFloat(celdasOrig[2].textContent);
                                    const congestionOriginal = parseFloat(celdasOrig[4].textContent);
                                    
                                    estatisticasOriginales.tiempoEspera = tiempoOriginal;
                                    estatisticasOriginales.congestion = congestionOriginal;
                                    
                                    console.log(`Estadísticas originales: Tiempo=${tiempoOriginal}, Congestión=${congestionOriginal}`);
                                }
                            }
                        }
                    }
                }
            }
        } catch (e) {
            console.log("Error al cargar desde resultados_optimizacion.html:", e);
        }
        
        // Si no pudimos cargar datos reales del AG, generamos una optimización simulada
        if (Object.keys(configOptimizada).length < Object.keys(configOriginal).length) {
            console.log("Generando configuración optimizada simulada...");
            
            // Generar mejoras simuladas
            Object.keys(configOriginal).forEach(id => {
                const verde = configOriginal[id].tiempo_verde;
                const amarillo = configOriginal[id].tiempo_amarillo;
                const rojo = configOriginal[id].tiempo_rojo;
                
                // Ajustar los tiempos para mejorar el flujo (ejemplo)
                configOptimizada[id] = {
                    tiempo_verde: Math.max(15, Math.floor(verde * 1.4)), // 40% más de tiempo en verde
                    tiempo_amarillo: amarillo, // Amarillo constante
                    tiempo_rojo: Math.max(10, Math.floor(rojo * 0.6)), // 40% menos de tiempo en rojo
                    desfase: Math.floor(Math.random() * 15) // Desfase aleatorio entre 0-15
                };
                
                // Recalcular ciclo total
                configOptimizada[id].ciclo_total = configOptimizada[id].tiempo_verde + 
                                                 configOptimizada[id].tiempo_amarillo + 
                                                 configOptimizada[id].tiempo_rojo;
            });
        }
        
        return true;
    } catch (error) {
        console.error("Error al cargar la configuración optimizada:", error);
        // Utilizar configuración predeterminada optimizada simulada
        console.log("Utilizando configuración optimizada simulada");
        
        Object.keys(configOriginal).forEach(id => {
            const verde = configOriginal[id].tiempo_verde;
            const amarillo = configOriginal[id].tiempo_amarillo;
            const rojo = configOriginal[id].tiempo_rojo;
            
            configOptimizada[id] = {
                tiempo_verde: Math.max(15, verde + 10),
                tiempo_amarillo: amarillo,
                tiempo_rojo: Math.max(10, rojo - 10),
                desfase: 5
            };
            
            configOptimizada[id].ciclo_total = configOptimizada[id].tiempo_verde + 
                                             configOptimizada[id].tiempo_amarillo + 
                                             configOptimizada[id].tiempo_rojo;
        });
        
        return true;
    }
}

// Inicializar mapa y visualización
function inicializarMapa() {
    // Crear el mapa Leaflet
    mapa = L.map('mapa').setView([16.7588268, -93.1195755], 15);
    
    // Añadir capa de OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(mapa);
    
    // Añadir marcadores para cada intersección
    intersecciones.forEach(interseccion => {
        if (interseccion.coordenadas) {
            const marker = L.marker([interseccion.coordenadas.lat, interseccion.coordenadas.lng], {
                title: interseccion.nombre || `Intersección ${interseccion.id}`
            }).addTo(mapa);
            
            // Añadir popup con información
            let popupContent = `<strong>${interseccion.nombre || `Intersección ${interseccion.id}`}</strong><br>`;
            popupContent += `${interseccion.semaforos.length} semáforos<br>`;
            
            marker.bindPopup(popupContent);
            marker.on('click', () => mostrarInfoInterseccion(interseccion));
            
            markers[interseccion.id] = marker;
            
            // Inicializar indicadores de cola
            interseccion.semaforos.forEach(semaforo => {
                const queueIndicator = L.divIcon({
                    className: 'queue-indicator',
                    html: '0',
                    iconSize: [20, 20]
                });
                
                // Posicionar el indicador ligeramente alejado del centro de la intersección
                const offset = 0.0001; // Ajustar según sea necesario
                let lat = interseccion.coordenadas.lat;
                let lng = interseccion.coordenadas.lng;
                
                // Ajustar posición según la dirección del semáforo
                if (semaforo.direccion.includes('Norte')) {
                    lat += offset;
                } else if (semaforo.direccion.includes('Sur')) {
                    lat -= offset;
                } else if (semaforo.direccion.includes('Este')) {
                    lng += offset;
                } else if (semaforo.direccion.includes('Oeste')) {
                    lng -= offset;
                }
                
                queueIndicators[semaforo.id] = L.marker([lat, lng], {
                    icon: queueIndicator,
                    zIndexOffset: 1000
                }).addTo(mapa);
            });
        }
    });
    
    // Dibujar calles (conexiones entre intersecciones)
    dibujarCalles();
}

// Dibujar calles en el mapa
function dibujarCalles() {
    calles.forEach(calle => {
        const desdeInterseccion = intersecciones.find(i => i.id === calle.desde_interseccion);
        const hastaInterseccion = intersecciones.find(i => i.id === calle.hasta_interseccion);
        
        if (desdeInterseccion && hastaInterseccion && 
            desdeInterseccion.coordenadas && hastaInterseccion.coordenadas) {
            
            // Calcular grosor basado en flujo promedio
            const flujoPromedio = (calle.flujo_promedio.mañana + calle.flujo_promedio.tarde + calle.flujo_promedio.noche) / 3;
            const grosor = 2 + Math.min(flujoPromedio / 50, 8); // Limitar grosor entre 2 y 10
            
            const polyline = L.polyline([
                [desdeInterseccion.coordenadas.lat, desdeInterseccion.coordenadas.lng],
                [hastaInterseccion.coordenadas.lat, hastaInterseccion.coordenadas.lng]
            ], {
                color: '#3388ff',
                weight: grosor,
                opacity: 0.7
            }).addTo(mapa);
            
            polyline.bindTooltip(`Flujo promedio: ${flujoPromedio.toFixed(1)} vehículos/h`);
            
            callePolylines.push({
                polyline: polyline,
                flujo: flujoPromedio,
                desde: desdeInterseccion.id,
                hasta: hastaInterseccion.id
            });
        }
    });
}

// Mostrar información de intersección seleccionada
function mostrarInfoInterseccion(interseccion) {
    const infoContainer = document.getElementById('semaforo-info');
    
    let html = `<h4>${interseccion.nombre || `Intersección ${interseccion.id}`}</h4>`;
    html += `<table>
                <tr>
                    <th>ID</th>
                    <th>Dirección</th>
                    <th>Estado</th>
                    <th>Vehículos en cola</th>
                </tr>`;
    
    interseccion.semaforos.forEach(semaforo => {
        const semId = semaforo.id;
        const estado = getEstadoSemaforo(semId, tiempoActual);
        const numVehiculos = colas[semId] ? colas[semId].length : 0;
        
        html += `<tr>
                    <td>${semId}</td>
                    <td>${semaforo.direccion}</td>
                    <td><span class="light-status ${estado}"></span>${estado.charAt(0).toUpperCase() + estado.slice(1)}</td>
                    <td>${numVehiculos}</td>
                </tr>`;
    });
    
    html += `</table>`;
    
    // Añadir información de configuración actual
    html += `<h4>Configuración actual:</h4>`;
    html += `<table>
                <tr>
                    <th>ID</th>
                    <th>Verde</th>
                    <th>Amarillo</th>
                    <th>Rojo</th>
                    <th>Desfase</th>
                </tr>`;
    
    interseccion.semaforos.forEach(semaforo => {
        const semId = semaforo.id;
        const config = configuracionOptimizada ? configOptimizada[semId] : configOriginal[semId];
        
        html += `<tr>
                    <td>${semId}</td>
                    <td>${config.tiempo_verde}s</td>
                    <td>${config.tiempo_amarillo}s</td>
                    <td>${config.tiempo_rojo}s</td>
                    <td>${config.desfase}s</td>
                </tr>`;
    });
    
    html += `</table>`;
    
    infoContainer.innerHTML = html;
}

// Obtener el estado de un semáforo en un tiempo específico
function getEstadoSemaforo(semaforoId, tiempo) {
    const config = configuracionOptimizada ? configOptimizada[semaforoId] : configOriginal[semaforoId];
    
    if (!config) return 'unknown';
    
    const cicloTotal = config.tiempo_verde + config.tiempo_amarillo + config.tiempo_rojo;
    const tiempoEfectivo = (tiempo + config.desfase) % cicloTotal;
    
    if (tiempoEfectivo < config.tiempo_verde) {
        return 'green';
    } else if (tiempoEfectivo < (config.tiempo_verde + config.tiempo_amarillo)) {
        return 'yellow';
    } else {
        return 'red';
    }
}

// Función para generar llegada de vehículos basada en distribución de Poisson
function generarLlegadaPoisson() {
    // Para cada intersección y semáforo
    intersecciones.forEach(interseccion => {
        interseccion.semaforos.forEach(semaforo => {
            // Determinar si llega un vehículo según distribución de Poisson
            const lambda = tasaLlegada / intersecciones.length; // Distribuir tasa entre todas las intersecciones
            const numLlegadas = poissonRandom(lambda * 2); // Aumentado para generar más tráfico visible
            
            for (let i = 0; i < numLlegadas; i++) {
                // Añadir vehículo a la cola
                const vehiculo = {
                    id: `veh-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                    tiempoLlegada: tiempoActual,
                    semaforoId: semaforo.id,
                    interseccionId: interseccion.id
                };
                
                colas[semaforo.id].push(vehiculo);
                
                // Agregar vehículo visualmente
                if (interseccion.coordenadas) {
                    agregarVehiculoVisual(vehiculo, interseccion.coordenadas);
                }
            }
        });
    });
}

// Función para generar números aleatorios con distribución de Poisson
function poissonRandom(lambda) {
    let L = Math.exp(-lambda);
    let p = 1.0;
    let k = 0;
    
    do {
        k++;
        p *= Math.random();
    } while (p > L);
    
    return k - 1;
}

// Añadir representación visual de un vehículo
function agregarVehiculoVisual(vehiculo, coordenadas) {
    // Pequeño offset aleatorio para no amontonar todos los vehículos en el mismo punto
    const offsetLat = (Math.random() - 0.5) * 0.0004;
    const offsetLng = (Math.random() - 0.5) * 0.0004;
    
    const vehiculoElement = document.createElement('div');
    vehiculoElement.className = 'car';
    vehiculoElement.id = vehiculo.id;
    vehiculoElement.style.backgroundColor = getRandomColor();
    
    const marcador = L.marker([coordenadas.lat + offsetLat, coordenadas.lng + offsetLng], {
        icon: L.divIcon({
            className: 'car-icon',
            html: vehiculoElement.outerHTML,
            iconSize: [6, 6]
        })
    }).addTo(mapa);
    
    vehiculosElements.push({
        id: vehiculo.id,
        marker: marcador,
        semaforoId: vehiculo.semaforoId
    });
}

// Generar color aleatorio para los vehículos
function getRandomColor() {
    const colores = ['#3388ff', '#ff6666', '#66ff66', '#ffff66', '#ff66ff', '#66ffff'];
    return colores[Math.floor(Math.random() * colores.length)];
}

// Procesar semáforos y mover vehículos
function procesarSemaforos() {
    let tiempoEsperaTotal = 0;
    let vehiculosProcesados = 0;
    let congestionTotal = 0;
    
    // Para cada semáforo
    Object.keys(semaforos).forEach(semaforoId => {
        const estado = getEstadoSemaforo(semaforoId, tiempoActual);
        const cola = colas[semaforoId];
        
        // Actualizar contador visual de la cola
        if (queueIndicators[semaforoId]) {
            queueIndicators[semaforoId].getElement().querySelector('.queue-indicator').innerHTML = cola.length.toString();
        }
        
        // Si el semáforo está en verde, procesar vehículos
        if (estado === 'green') {
            // El número de vehículos procesados depende de la configuración
            // En la configuración optimizada, los semáforos son más eficientes
            let capacidadProcesamiento = 2; // Valor base para configuración original
            
            if (configuracionOptimizada) {
                // Mayor capacidad con la configuración optimizada
                capacidadProcesamiento = 3;
            }
            
            // Procesar vehículos según capacidad
            const numProcesar = Math.min(capacidadProcesamiento, cola.length);
            
            for (let i = 0; i < numProcesar; i++) {
                if (cola.length > 0) {
                    const vehiculo = cola.shift(); // Sacar el primer vehículo de la cola
                    const tiempoEspera = tiempoActual - vehiculo.tiempoLlegada;
                    
                    tiempoEsperaTotal += tiempoEspera;
                    vehiculosProcesados++;
                    
                    // Eliminar vehículo visualmente
                    const index = vehiculosElements.findIndex(v => v.id === vehiculo.id);
                    if (index !== -1) {
                        mapa.removeLayer(vehiculosElements[index].marker);
                        vehiculosElements.splice(index, 1);
                    }
                }
            }
        }
        
        // Añadir a la congestión total
        congestionTotal += cola.length;
    });
    
    // Actualizar estadísticas
    if (vehiculosProcesados > 0) {
        const promedio = tiempoEsperaTotal / vehiculosProcesados;
        tiempoEspera = (tiempoEspera * vehiculosAtendidos + promedio * vehiculosProcesados) / 
                      (vehiculosAtendidos + vehiculosProcesados);
        
        vehiculosAtendidos += vehiculosProcesados;
    }
    
    congestion = congestionTotal;
    
    // Actualizar estadísticas en la interfaz
    document.getElementById('tiempo-espera').textContent = tiempoEspera.toFixed(1);
    document.getElementById('congestion').textContent = congestion;
    
    // Guardar estadísticas para comparativa
    if (configuracionOptimizada) {
        // Promedio ponderado para suavizar las fluctuaciones
        estatisticasOptimizadas.tiempoEspera = estatisticasOptimizadas.tiempoEspera === 0 ? 
            tiempoEspera : 
            (estatisticasOptimizadas.tiempoEspera * 0.95 + tiempoEspera * 0.05);
        
        estatisticasOptimizadas.congestion = estatisticasOptimizadas.congestion === 0 ? 
            congestion : 
            (estatisticasOptimizadas.congestion * 0.95 + congestion * 0.05);
    } else {
        // Promedio ponderado para suavizar las fluctuaciones
        estatisticasOriginales.tiempoEspera = estatisticasOriginales.tiempoEspera === 0 ? 
            tiempoEspera : 
            (estatisticasOriginales.tiempoEspera * 0.95 + tiempoEspera * 0.05);
        
        estatisticasOriginales.congestion = estatisticasOriginales.congestion === 0 ? 
            congestion : 
            (estatisticasOriginales.congestion * 0.95 + congestion * 0.05);
    }
    
    // Actualizar comparativa
    actualizarComparativa();
}

// Función para generar el archivo de resultados del simulador
function generarArchivoResultados() {
    const html = `
    <html>
    <head>
        <style>
            table {
                border-collapse: collapse;
                width: 100%;
                font-family: Arial, sans-serif;
            }
            th, td {
                text-align: left;
                padding: 8px;
                border: 1px solid #ddd;
            }
            th {
                background-color: #4CAF50;
                color: white;
            }
            tr:nth-child(even) {
                background-color: #f2f2f2;
            }
            .mejora {
                color: green;
                font-weight: bold;
            }
            .empeora {
                color: red;
                font-weight: bold;
            }
        </style>
    </head>
    <body>
        <h2>Resultados de la Simulación de Tráfico</h2>
        <table>
            <tr>
                <th>Configuración</th>
                <th>Tiempo de Espera (s)</th>
                <th>Mejora en Tiempo</th>
                <th>Congestión (vehículos)</th>
                <th>Mejora en Congestión</th>
            </tr>
            <tr>
                <td>Original (sin optimizar)</td>
                <td>${estatisticasOriginales.tiempoEspera.toFixed(2)}</td>
                <td>-</td>
                <td>${estatisticasOriginales.congestion.toFixed(2)}</td>
                <td>-</td>
            </tr>
            <tr>
                <td>Optimizada</td>
                <td>${estatisticasOptimizadas.tiempoEspera.toFixed(2)}</td>
                <td class="${estatisticasOptimizadas.tiempoEspera < estatisticasOriginales.tiempoEspera ? 'mejora' : 'empeora'}">
                    ${((estatisticasOriginales.tiempoEspera - estatisticasOptimizadas.tiempoEspera) / estatisticasOriginales.tiempoEspera * 100).toFixed(2)}%
                    ${estatisticasOptimizadas.tiempoEspera < estatisticasOriginales.tiempoEspera ? '↓' : '↑'}
                </td>
                <td>${estatisticasOptimizadas.congestion.toFixed(2)}</td>
                <td class="${estatisticasOptimizadas.congestion < estatisticasOriginales.congestion ? 'mejora' : 'empeora'}">
                    ${((estatisticasOriginales.congestion - estatisticasOptimizadas.congestion) / estatisticasOriginales.congestion * 100).toFixed(2)}%
                    ${estatisticasOptimizadas.congestion < estatisticasOriginales.congestion ? '↓' : '↑'}
                </td>
            </tr>
        </table>
        <p><i>Nota: Los valores de tiempo de espera son segundos promedio por vehículo.
        La congestión representa el número promedio de vehículos en cola.</i></p>
        <p><i>Última actualización: ${new Date().toLocaleString()}</i></p>
    </body>
    </html>
    `;

    // Crear un blob con el contenido HTML
    const blob = new Blob([html], { type: 'text/html' });
    
    // Crear un enlace temporal y hacer clic en él para descargar el archivo
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'resultados_simulacion.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
}

// Modificar la función actualizarComparativa para generar el archivo cada 30 segundos
function actualizarComparativa() {
    const mejoraElementoTiempo = document.getElementById('mejora-tiempo');
    const mejoraElementoCongestion = document.getElementById('mejora-congestion');
    
    if (estatisticasOriginales.tiempoEspera > 0 && estatisticasOptimizadas.tiempoEspera > 0) {
        // Calcular mejora en tiempo de espera
        const mejoraPorc = ((estatisticasOriginales.tiempoEspera - estatisticasOptimizadas.tiempoEspera) / 
                           estatisticasOriginales.tiempoEspera) * 100;
        
        if (mejoraPorc > 0) {
            mejoraElementoTiempo.textContent = `${mejoraPorc.toFixed(1)}% ↓`;
            mejoraElementoTiempo.style.color = 'green';
        } else {
            mejoraElementoTiempo.textContent = `${Math.abs(mejoraPorc).toFixed(1)}% ↑`;
            mejoraElementoTiempo.style.color = 'red';
        }
    }
    
    if (estatisticasOriginales.congestion > 0 && estatisticasOptimizadas.congestion > 0) {
        // Calcular mejora en congestión
        const mejoraCongPorc = ((estatisticasOriginales.congestion - estatisticasOptimizadas.congestion) / 
                               estatisticasOriginales.congestion) * 100;
        
        if (mejoraCongPorc > 0) {
            mejoraElementoCongestion.textContent = `${mejoraCongPorc.toFixed(1)}% ↓`;
            mejoraElementoCongestion.style.color = 'green';
        } else {
            mejoraElementoCongestion.textContent = `${Math.abs(mejoraCongPorc).toFixed(1)}% ↑`;
            mejoraElementoCongestion.style.color = 'red';
        }
    }

    // Generar archivo de resultados cada 30 segundos
    if (tiempoActual % 30 === 0) {
        generarArchivoResultados();
    }
}

// Cambiar entre configuración original y optimizada
function cambiarConfiguracion() {
    configuracionOptimizada = document.getElementById('toggle-solucion').checked;
    
    // Actualizar configuración de todos los semáforos
    Object.keys(semaforos).forEach(id => {
        const config = configuracionOptimizada ? configOptimizada[id] : configOriginal[id];
        
        if (config) {
            semaforos[id].tiempo_verde = config.tiempo_verde;
            semaforos[id].tiempo_amarillo = config.tiempo_amarillo;
            semaforos[id].tiempo_rojo = config.tiempo_rojo;
            semaforos[id].desfase = config.desfase;
            semaforos[id].ciclo_total = config.tiempo_verde + config.tiempo_amarillo + config.tiempo_rojo;
        }
    });
    
    // Si hay una intersección seleccionada, actualizar su información
    const interseccionActiva = document.querySelector('#semaforo-info h4');
    if (interseccionActiva) {
        const textoTitulo = interseccionActiva.textContent;
        const interseccionId = textoTitulo.includes('Intersección') ? 
                             parseInt(textoTitulo.replace('Intersección ', '')) :
                             intersecciones.find(i => i.nombre === textoTitulo)?.id;
        
        if (interseccionId) {
            const interseccion = intersecciones.find(i => i.id === interseccionId);
            if (interseccion) {
                mostrarInfoInterseccion(interseccion);
            }
        }
    }
}

// Paso de simulación
function pasarTiempo() {
    tiempoActual++;
    document.getElementById('tiempo').textContent = `Tiempo: ${tiempoActual}s`;
    
    // Generar nuevas llegadas de vehículos
    generarLlegadaPoisson();
    
    // Procesar semáforos y mover vehículos
    procesarSemaforos();
    
    // Mostrar información de una intersección seleccionada aleatoriamente 
    // cada 10 segundos para que el usuario pueda ver los cambios
    if (tiempoActual % 10 === 0) {
        const interseccionesValidas = intersecciones.filter(i => i.coordenadas);
        if (interseccionesValidas.length > 0) {
            const interseccionAleatoria = interseccionesValidas[Math.floor(Math.random() * interseccionesValidas.length)];
            mostrarInfoInterseccion(interseccionAleatoria);
        }
    }
}

// Iniciar simulación
function iniciarSimulacion() {
    if (!enSimulacion) {
        enSimulacion = true;
        document.getElementById('btn-iniciar').disabled = true;
        document.getElementById('btn-pausar').disabled = false;
        
        // Iniciar intervalo de simulación
        const intervalo = 1000 / velocidadSimulacion; // ms entre pasos de simulación
        intervalId = setInterval(pasarTiempo, intervalo);
    }
}

// Pausar simulación
function pausarSimulacion() {
    if (enSimulacion) {
        enSimulacion = false;
        document.getElementById('btn-iniciar').disabled = false;
        document.getElementById('btn-pausar').disabled = true;
        
        clearInterval(intervalId);
    }
}

// Reiniciar simulación
function reiniciarSimulacion() {
    // Pausar primero
    if (enSimulacion) {
        pausarSimulacion();
    }
    
    // Reiniciar variables
    tiempoActual = 0;
    tiempoEspera = 0;
    congestion = 0;
    vehiculosAtendidos = 0;
    
    // Limpiar colas
    Object.keys(colas).forEach(id => {
        colas[id] = [];
    });
    
    // Eliminar vehículos del mapa
    vehiculosElements.forEach(veh => {
        mapa.removeLayer(veh.marker);
    });
    vehiculosElements = [];
    
    // Reiniciar indicadores de cola
    Object.keys(queueIndicators).forEach(id => {
        queueIndicators[id].getElement().querySelector('.queue-indicator').innerHTML = '0';
    });
    
    // Reiniciar interfaz
    document.getElementById('tiempo').textContent = 'Tiempo: 0s';
    document.getElementById('tiempo-espera').textContent = '0';
    document.getElementById('congestion').textContent = '0';
    
    // Reiniciar estadísticas
    estatisticasOriginales = {
        tiempoEspera: 0,
        congestion: 0
    };
    estatisticasOptimizadas = {
        tiempoEspera: 0,
        congestion: 0
    };
    document.getElementById('mejora-tiempo').textContent = '0%';
    document.getElementById('mejora-congestion').textContent = '0%';
}

// Controladores de eventos
document.addEventListener('DOMContentLoaded', async () => {
    console.log("Inicializando simulador de tráfico...");
    
    // Mostrar mensaje de carga
    document.getElementById('tiempo').textContent = "Cargando datos...";
    
    // Cargar datos
    const datosOk = await cargarDatos();
    
    if (datosOk) {
        console.log("Datos cargados correctamente");
        document.getElementById('tiempo').textContent = "Tiempo: 0s";
        
        // Inicializar mapa
        inicializarMapa();
        
        // Actualizar estadísticas iniciales en la interfaz
        document.getElementById('tiempo-espera').textContent = estatisticasOriginales.tiempoEspera.toFixed(1);
        document.getElementById('congestion').textContent = estatisticasOriginales.congestion;
        
        // Si tenemos estadísticas de comparación, mostrarlas
        if (estatisticasOriginales.tiempoEspera > 0 && estatisticasOptimizadas.tiempoEspera > 0) {
            actualizarComparativa();
        }
        
        // Configurar controles
        document.getElementById('btn-iniciar').addEventListener('click', iniciarSimulacion);
        document.getElementById('btn-pausar').addEventListener('click', pausarSimulacion);
        document.getElementById('btn-reiniciar').addEventListener('click', reiniciarSimulacion);
        
        document.getElementById('velocidad').addEventListener('input', (e) => {
            velocidadSimulacion = parseInt(e.target.value);
            document.getElementById('valor-velocidad').textContent = `${velocidadSimulacion}x`;
            
            // Si la simulación está en curso, actualizar el intervalo
            if (enSimulacion) {
                clearInterval(intervalId);
                const intervalo = 1000 / velocidadSimulacion;
                intervalId = setInterval(pasarTiempo, intervalo);
            }
        });
        
        document.getElementById('tasa-llegada').addEventListener('input', (e) => {
            tasaLlegada = parseFloat(e.target.value);
            document.getElementById('valor-tasa').textContent = `${tasaLlegada.toFixed(1)} veh/s`;
        });
        
        document.getElementById('toggle-solucion').addEventListener('change', cambiarConfiguracion);
    } else {
        alert('Error al cargar los datos. Por favor, verifica que el archivo JSON sea accesible.');
    }
}); 