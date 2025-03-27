// Variables globales
let mapa = null;
let intersecciones = [];
let calles = [];
let semaforos = {};
let vehiculos = [];
let colas = {};
let markers = {};
let callePolylines = [];
let vehiculosElements = [];
let queueIndicators = {};
let interseccionSeleccionada = null;

// Variables de simulación
let tiempoActual = 0;
let tiempoEspera = 0;
let congestion = 0;
let vehiculosAtendidos = 0;
let tasaLlegada = 2.0;
let velocidadSimulacion = 5;
let enSimulacion = false;
let intervalId = null;

// Configuración de semáforos del AG
let configuracionAG = null;
let estadisticasOriginales = null;

// Función para cargar datos del AG y la zona delimitada
async function cargarDatos() {
    try {
        // Cargar configuración del AG
        const respuestaAG = await fetch('resultados_optimizacion.json');
        configuracionAG = await respuestaAG.json();

        // Cargar datos de la zona delimitada
        const respuestaZona = await fetch('zona_delimitada.json');
        const dataZona = await respuestaZona.json();

        intersecciones = dataZona.intersecciones;
        calles = dataZona.calles;

        // Inicializar semáforos y colas
        intersecciones.forEach(interseccion => {
            interseccion.semaforos.forEach(semaforo => {
                semaforos[semaforo.id] = {
                    ...semaforo,
                    tiempo_verde: semaforo.tiempo_verde_inicial,
                    tiempo_amarillo: semaforo.tiempo_amarillo_inicial,
                    tiempo_rojo: semaforo.tiempo_rojo_inicial,
                    desfase: 0,
                    ciclo_total: semaforo.tiempo_verde_inicial + semaforo.tiempo_amarillo_inicial + semaforo.tiempo_rojo_inicial
                };
                colas[semaforo.id] = [];
            });
        });

        // Obtener estadísticas originales del AG
        estadisticasOriginales = configuracionAG.soluciones.find(s => s.nombre === "Original (sin optimizar)");

        return true;
    } catch (error) {
        console.error("Error al cargar datos:", error);
        return false;
    }
}

// Inicializar mapa y visualización
function inicializarMapa() {
    // Crear mapa centrado en Tuxtla Gutiérrez
    mapa = L.map('mapa').setView([16.7506, -93.1029], 14);

    // Añadir capa de OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(mapa);

    // Añadir marcadores para intersecciones
    intersecciones.forEach(interseccion => {
        if (interseccion.coordenadas) {
            const marker = L.marker([interseccion.coordenadas.lat, interseccion.coordenadas.lng], {
                title: interseccion.nombre || `Intersección ${interseccion.id}`
            }).addTo(mapa);

            // Popup con información
            let popupContent = `<strong>${interseccion.nombre || `Intersección ${interseccion.id}`}</strong><br>`;
            popupContent += `${interseccion.semaforos.length} semáforos<br>`;
            marker.bindPopup(popupContent);
            marker.on('click', () => mostrarInfoInterseccion(interseccion));

            markers[interseccion.id] = marker;

            // Indicadores de cola
            interseccion.semaforos.forEach(semaforo => {
                const queueIndicator = L.divIcon({
                    className: 'queue-indicator',
                    html: '0',
                    iconSize: [20, 20]
                });

                // Posicionar indicador según dirección del semáforo
                const offset = 0.0001;
                let lat = interseccion.coordenadas.lat;
                let lng = interseccion.coordenadas.lng;

                switch(semaforo.direccion.toLowerCase()) {
                    case 'norte': lat += offset; break;
                    case 'sur': lat -= offset; break;
                    case 'este': lng += offset; break;
                    case 'oeste': lng -= offset; break;
                }

                queueIndicators[semaforo.id] = L.marker([lat, lng], {
                    icon: queueIndicator,
                    zIndexOffset: 1000
                }).addTo(mapa);
            });
        }
    });

    // Dibujar calles
    dibujarCalles();
}

// Dibujar calles en el mapa
function dibujarCalles() {
    let flujoMaximo = Math.max(...calles.map(c => 
        Math.max(c.flujo_promedio.mañana, c.flujo_promedio.tarde, c.flujo_promedio.noche)
    ));

    calles.forEach(calle => {
        const desde = intersecciones.find(i => i.id === calle.desde_interseccion);
        const hasta = intersecciones.find(i => i.id === calle.hasta_interseccion);

        if (desde?.coordenadas && hasta?.coordenadas) {
            const flujoPromedio = (calle.flujo_promedio.mañana + 
                                 calle.flujo_promedio.tarde + 
                                 calle.flujo_promedio.noche) / 3;
            
            const grosor = 2 + (flujoPromedio / flujoMaximo) * 8;
            const color = obtenerColorFlujo(flujoPromedio / flujoMaximo);

            const polyline = L.polyline([
                [desde.coordenadas.lat, desde.coordenadas.lng],
                [hasta.coordenadas.lat, hasta.coordenadas.lng]
            ], {
                color: color,
                weight: grosor,
                opacity: 0.7
            }).addTo(mapa);

            polyline.bindTooltip(`Flujo promedio: ${flujoPromedio.toFixed(1)} vehículos/h`);
            callePolylines.push({polyline, flujo: flujoPromedio, desde: desde.id, hasta: hasta.id});
        }
    });
}

// Obtener color según flujo
function obtenerColorFlujo(normalizado) {
    const colores = ['#ffffb2', '#fecc5c', '#fd8d3c', '#e31a1c'];
    const indice = Math.floor(normalizado * (colores.length - 1));
    return colores[Math.min(indice, colores.length - 1)];
}

// Mostrar información de intersección
function mostrarInfoInterseccion(interseccion) {
    interseccionSeleccionada = interseccion;
    actualizarInfoInterseccion();
}

// Nueva función para actualizar la información de la intersección
function actualizarInfoInterseccion() {
    if (!interseccionSeleccionada) return;
    
    const infoContainer = document.getElementById('semaforo-info');
    
    let html = `<h4>${interseccionSeleccionada.nombre || `Intersección ${interseccionSeleccionada.id}`}</h4>`;
    html += `<table>
                <tr>
                    <th>ID</th>
                    <th>Dirección</th>
                    <th>Estado</th>
                    <th>Cola</th>
                </tr>`;

    interseccionSeleccionada.semaforos.forEach(semaforo => {
        const estado = obtenerEstadoSemaforo(semaforo.id);
        const numVehiculos = colas[semaforo.id]?.length || 0;

        html += `<tr>
                    <td>${semaforo.id}</td>
                    <td>${semaforo.direccion}</td>
                    <td><div class="traffic-light-container">
                        <div class="traffic-light ${estado}"></div>
                        <span class="traffic-light-text">${estado}</span>
                    </div></td>
                    <td>${numVehiculos}</td>
                </tr>`;
    });

    html += '</table>';
    infoContainer.innerHTML = html;
}

// Obtener estado de semáforo
function obtenerEstadoSemaforo(semaforoId) {
    const semaforo = semaforos[semaforoId];
    if (!semaforo) return 'unknown';

    const tiempoEfectivo = (tiempoActual + semaforo.desfase) % semaforo.ciclo_total;

    if (tiempoEfectivo < semaforo.tiempo_verde) return 'verde';
    if (tiempoEfectivo < semaforo.tiempo_verde + semaforo.tiempo_amarillo) return 'amarillo';
    return 'rojo';
}

// Generar llegadas de vehículos (Poisson)
function generarLlegadasPoisson() {
    intersecciones.forEach(interseccion => {
        interseccion.semaforos.forEach(semaforo => {
            const lambda = tasaLlegada / intersecciones.length;
            const llegadas = poissonRandom(lambda);

            for (let i = 0; i < llegadas; i++) {
                const vehiculo = {
                    id: `v-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
                    tiempoLlegada: tiempoActual,
                    semaforoId: semaforo.id,
                    interseccionId: interseccion.id
                };

                colas[semaforo.id].push(vehiculo);
                if (interseccion.coordenadas) {
                    agregarVehiculoVisual(vehiculo, interseccion.coordenadas);
                }
            }
        });
    });
}

// Distribución de Poisson
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

// Agregar vehículo visual al mapa
function agregarVehiculoVisual(vehiculo, coordenadas) {
    const offset = {
        lat: (Math.random() - 0.5) * 0.0004,
        lng: (Math.random() - 0.5) * 0.0004
    };

    const vehiculoMarker = L.marker([coordenadas.lat + offset.lat, coordenadas.lng + offset.lng], {
        icon: L.divIcon({
            className: 'vehicle',
            html: '',
            iconSize: [8, 8]
        })
    }).addTo(mapa);

    vehiculosElements.push({
        id: vehiculo.id,
        marker: vehiculoMarker,
        semaforoId: vehiculo.semaforoId
    });
}

// Procesar semáforos y mover vehículos
function procesarSemaforos() {
    let tiempoEsperaTotal = 0;
    let vehiculosProcesados = 0;
    let congestionTotal = 0;

    Object.keys(semaforos).forEach(semaforoId => {
        const estado = obtenerEstadoSemaforo(semaforoId);
        const cola = colas[semaforoId];

        // Actualizar indicador de cola
        if (queueIndicators[semaforoId]) {
            queueIndicators[semaforoId].getElement().innerHTML = cola.length.toString();
        }

        if (estado === 'verde') {
            const capacidad = 3; // Vehículos por ciclo verde
            const numProcesar = Math.min(capacidad, cola.length);

            for (let i = 0; i < numProcesar; i++) {
                if (cola.length > 0) {
                    const vehiculo = cola.shift();
                    const tiempoEspera = tiempoActual - vehiculo.tiempoLlegada;

                    tiempoEsperaTotal += tiempoEspera;
                    vehiculosProcesados++;

                    // Eliminar vehículo visual
                    const index = vehiculosElements.findIndex(v => v.id === vehiculo.id);
                    if (index !== -1) {
                        mapa.removeLayer(vehiculosElements[index].marker);
                        vehiculosElements.splice(index, 1);
                    }
                }
            }
        }

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

    // Actualizar UI
    actualizarEstadisticas();
}

// Actualizar estadísticas en la UI
function actualizarEstadisticas() {
    document.getElementById('tiempo-espera').textContent = `${tiempoEspera.toFixed(1)}s`;
    document.getElementById('congestion').textContent = congestion;
    document.getElementById('vehiculos-procesados').textContent = vehiculosAtendidos;

    // Comparar con resultados del AG
    if (estadisticasOriginales) {
        const mejoraTime = ((estadisticasOriginales.tiempo_espera - tiempoEspera) / 
                           estadisticasOriginales.tiempo_espera * 100);
        const mejoraCong = ((estadisticasOriginales.congestion - congestion) / 
                           estadisticasOriginales.congestion * 100);

        document.getElementById('mejora-tiempo').textContent = `${mejoraTime.toFixed(1)}%`;
        document.getElementById('mejora-tiempo').className = `stats-value ${mejoraTime >= 0 ? 'improvement' : 'deterioration'}`;

        document.getElementById('mejora-congestion').textContent = `${mejoraCong.toFixed(1)}%`;
        document.getElementById('mejora-congestion').className = `stats-value ${mejoraCong >= 0 ? 'improvement' : 'deterioration'}`;
    }
}

// Paso de simulación
function pasarTiempo() {
    tiempoActual++;
    document.getElementById('tiempo').textContent = `Tiempo: ${tiempoActual}s`;
    
    // Generar nuevas llegadas de vehículos
    generarLlegadasPoisson();
    
    // Procesar semáforos y mover vehículos
    procesarSemaforos();
    
    // Actualizar estadísticas
    actualizarEstadisticas();
    
    // Actualizar información de la intersección si hay una seleccionada
    actualizarInfoInterseccion();
}

// Iniciar simulación
function iniciarSimulacion() {
    if (!enSimulacion) {
        enSimulacion = true;
        document.getElementById('btn-iniciar').disabled = true;
        document.getElementById('btn-pausar').disabled = false;

        intervalId = setInterval(pasarTiempo, 1000 / velocidadSimulacion);
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
    if (enSimulacion) {
        pausarSimulacion();
    }

    tiempoActual = 0;
    tiempoEspera = 0;
    congestion = 0;
    vehiculosAtendidos = 0;

    // Limpiar colas y vehículos
    Object.keys(colas).forEach(id => colas[id] = []);
    vehiculosElements.forEach(veh => mapa.removeLayer(veh.marker));
    vehiculosElements = [];

    // Reiniciar indicadores
    Object.values(queueIndicators).forEach(indicator => {
        indicator.getElement().innerHTML = '0';
    });

    // Actualizar UI
    document.getElementById('tiempo').textContent = 'Tiempo: 0s';
    actualizarEstadisticas();
}

// Inicialización
document.addEventListener('DOMContentLoaded', async () => {
    console.log('Inicializando simulación...');

    const datosOK = await cargarDatos();
    if (datosOK) {
        inicializarMapa();

        // Event listeners
        document.getElementById('btn-iniciar').addEventListener('click', iniciarSimulacion);
        document.getElementById('btn-pausar').addEventListener('click', pausarSimulacion);
        document.getElementById('btn-reiniciar').addEventListener('click', reiniciarSimulacion);

        document.getElementById('velocidad').addEventListener('input', (e) => {
            velocidadSimulacion = parseInt(e.target.value);
            document.getElementById('valor-velocidad').textContent = `${velocidadSimulacion}x`;

            if (enSimulacion) {
                clearInterval(intervalId);
                intervalId = setInterval(pasarTiempo, 1000 / velocidadSimulacion);
            }
        });

        document.getElementById('tasa-llegada').addEventListener('input', (e) => {
            tasaLlegada = parseFloat(e.target.value);
            document.getElementById('valor-tasa').textContent = `${tasaLlegada.toFixed(1)} veh/s`;
        });

        console.log('Simulación inicializada correctamente');
    } else {
        alert('Error al cargar los datos. Verifica que los archivos necesarios estén disponibles.');
    }
}); 