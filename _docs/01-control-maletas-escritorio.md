# SPEC 01 — Sistema de control de maletas (escritorio)

**Estado:** Implemented
**Depende de:** ninguna
**Fecha:** 2026-10-14
**Actualizada:** 2026-10-14 (dashboard, selector de fecha, claves CM2, rendimiento)
**Objetivo:** App de escritorio (Python + SQLite + CustomTkinter) para registrar personas y su equipaje, asignar ubicación automática, emitir ticket QR/código, buscar y registrar el retiro, con licencias offline por evento (clave para pegar o archivo `.lic`) e instaladores Windows (.exe Inno Setup y .msix) generados en GitHub Actions.

## Alcance

### Dentro
- Registro de persona: nombre, DNI, teléfono (opcional), observaciones (opcional).
- Registro de 1..N bultos por persona, con descripción opcional por bulto.
- Asignación automática de ubicación libre en estantes/zonas configurables con capacidad.
- Ticket con QR + código corto (ej. `A3F7K2`): mostrar en pantalla, imprimir o exportar a PDF.
- Buscador por nombre (parcial, sin tildes) o DNI.
- Retiro: escanear QR (lector USB como teclado) o código manual / búsqueda → confirmar → liberar ubicación y registrar hora.
- Gestión de eventos (un evento activo a la vez) y configuración de zonas/ubicaciones.
- Licencia por evento firmada (Ed25519) y validada offline, en dos formas equivalentes:
  - **Clave `CM2.<payload>.<firma>`** para pegar (p. ej. enviada por WhatsApp); tolera saltos de línea y espacios.
  - **Archivo `.lic`** con esa misma cadena en una línea (UTF-8, tolera BOM/CRLF), cargado desde el explorador de archivos.
  - Formato `.lic` JSON v1 (`{payload, signature}`) aún aceptado por compatibilidad.
- Emisión de licencias: `tools/gen_license.py` (Python) y `tools/php/generar_clave.php` (PHP/sodium) para el sistema web del propietario; el payload admite campos extra opcionales que la app ignora.
- Licencia **maestra** (del propietario): mismo formato firmado, sin límite de eventos ni de registros, válida en cualquier evento; la emites tú con `tools/gen_license.py --type master`.
- **Modo sin licencia (demo)**: máximo 1 evento y 5 personas registradas ("usuarios" = personas con equipaje; no hay cuentas de login). Retiro, búsqueda y tickets funcionan normal dentro del límite.
- **Atado opcional a equipo**: la pantalla Licencia muestra el ID del equipo (`XXXX-XXXX-XXXX-XXXX`, base32, derivado de SHA-256 del identificador del sistema) con botón «Copiar»; si el payload trae `machine_id` debe coincidir (sin espacios/guiones, sin distinguir mayúsculas) o se rechaza con «licencia de otro equipo»; sin `machine_id` no se valida nada.
- **Aviso modal** destacado al superar la demo o el tope de la licencia, con botón directo a «Activar licencia».
- **Inicio (dashboard)**: personas por evento, custodia/entregados, ocupación, bultos con más tiempo en custodia, últimos registros, actividad por hora y ocupación por zona.
- **Selector de fecha** (calendario propio) en inicio/fin del evento, con validación de formato y rango.
- **Copia de seguridad** automática de la BD al cerrar (últimas 10) y exportación CSV del evento.
- Tema moderno con colores extraídos de `logo.png`, claro/oscuro.
- Entorno virtual, `run.sh`, `build.sh` (Linux y Windows vía Git Bash), workflow GitHub Actions.
- Instaladores: .exe portable (PyInstaller), Setup.exe (Inno Setup), .msix.

### Fuera (specs futuros)
- Login/roles de usuario, multi-PC o red.
- Foto del equipaje / webcam.
- Servidor de licencias online (la emisión ocurre en el sistema web del propietario; la app nunca consulta internet).
- Revocación de licencias (inviable offline; mitigación: licencias cortas por evento). Candidata a un spec propio con lista de revocados firmada.
- Firma con certificado de code signing real (paso opcional por secrets).
- Impresión directa ESC/POS (se usa impresión del sistema/PDF).
- Reportes avanzados más allá del dashboard de Inicio y la exportación CSV básica.

## Modelo de datos (SQLite)

| Tabla | Campos clave |
|---|---|
| `events` | id, name, starts_at, ends_at, license_id, active, created_at |
| `zones` | id, event_id, code (A, B…), name, capacity |
| `locations` | id, zone_id, label (`A-01`), occupied (bool) |
| `people` | id, event_id, full_name, full_name_norm, dni, phone, notes, ticket_code (único por evento), created_at |
| `luggage` | id, person_id, ticket_code (copia del de la persona), description, location_id, status (`stored`/`delivered`), stored_at, delivered_at |
| `meta` | key, value (schema_version) |
| `licenses` | id, type (`event`/`master`), event_name, starts_at, ends_at, max_people (nullable), raw_file, activated_at |

- Índices: `people(event_id, dni)`, `people(full_name_norm)`, `luggage(ticket_code)`.
- Un ticket por persona agrupa sus bultos; ubicación se asigna por bulto (prefiere misma zona).
- Migraciones por `schema_version` en `meta`.
- BD en directorio de datos del usuario (`%APPDATA%/ControlMaletas`, `~/.local/share/...`).
- Payload de licencia (JSON): `id`, `type` (`event`/`master`), `event`, `licensee`, `starts_at`, `ends_at` (`YYYY-MM-DD` o null), `max_people` (int o null), `issued_at`, `machine_id` (opcional); se ignoran campos desconocidos.
- Clave v2: `CM2.<base64url(payload)>.<base64url(firma Ed25519)>`; la firma cubre los **bytes exactos** del payload (sin canonicalizar), por lo que cualquier lenguaje puede emitirla.
- Límites demo (1 evento, 5 personas) fijos en código, con contadores en `meta`; la clave pública va embebida; la privada (semilla de 32 bytes) solo en el emisor, nunca en el repo.
- El nombre del evento de la licencia debe coincidir con el del evento en la app (sin distinguir mayúsculas).

## Plan de implementación

1. **Scaffold**: estructura `src/control_maletas/`, `requirements.txt`, `.venv`, `run.sh`, `.gitignore`. App abre ventana vacía con tema.
2. **Tema**: extraer paleta de `logo.png`, tokens de color/tipografía, logo en cabecera.
3. **Capa de datos**: esquema SQLite, migraciones, repositorios; tests.
4. **Eventos y zonas**: pantalla de configuración; generación de ubicaciones por capacidad.
5. **Registro**: formulario persona + bultos, validación DNI (8 dígitos, duplicado por evento), asignación de ubicación.
6. **Ticket**: generación QR + código, vista previa, imprimir y PDF.
7. **Búsqueda**: buscador por nombre/DNI con resultados en vivo.
8. **Retiro**: escaneo/código, confirmación, liberación.
9. **Licencias**: validación offline, pantalla de activación, límites demo (1 evento / 5 personas), licencia maestra, mensajes de límite alcanzado; `tools/gen_license.py` (tipos `event` y `master`).
10. **Empaquetado**: `build.sh` (PyInstaller), script Inno Setup `.iss`, manifiesto MSIX.
11. **CI**: workflow GitHub Actions (tests + build Windows .exe/Setup/.msix, artefactos y release por tag; Linux build).
12. **Pulido UX**: estados vacíos, errores, atajos de teclado, textos en español.
13. **Inicio (dashboard)**: consultas agregadas por evento y vista de resumen; pantalla inicial de la app.
14. **Selector de fecha** propio y validación de fechas del evento.
15. **Aviso de límite** modal con acceso directo a la activación de licencia.
16. **Licencias v2**: clave `CM2` pegable y `.lic` de una línea; emisor PHP/sodium; compatibilidad con v1.
17. **Rendimiento**: cuadrículas de ubicaciones en un solo canvas; barra de scroll solo si hace falta.

## Criterios de aceptación

- [x] `./run.sh` crea `.venv` si falta, instala dependencias y abre la app.
- [x] Registrar persona con 3 bultos asigna 3 ubicaciones libres y muestra ticket con QR y código.
- [x] Un DNI duplicado en el mismo evento advierte y permite agregar bultos a la persona existente.
- [x] Con zonas llenas, la app avisa claramente y no registra.
- [x] Buscar por "perez" o "12345678" devuelve la persona en <1 s con 5 000 registros.
- [x] Escanear QR/código marca bultos `delivered`, libera ubicaciones y guarda `delivered_at`.
- [x] Sin licencia: se puede crear 1 evento; el 2.º evento es rechazado con mensaje que invita a activar licencia.
- [x] Sin licencia: se registran 5 personas; la 6.ª es rechazada con mensaje claro (consultas y retiros siguen funcionando).
- [x] Licencia de evento válida levanta los límites solo para su evento; vencida o de otro evento vuelve al modo demo.
- [x] Licencia maestra válida levanta todos los límites en cualquier evento.
- [x] Una licencia con firma alterada es rechazada; funciona sin internet.
- [x] Una clave `CM2` emitida desde PHP/sodium se valida; pegada con saltos de línea y desde `.lic` con BOM/CRLF también.
- [x] Al superar la demo o el tope se muestra un aviso modal con botón «Activar licencia».
- [x] Inicio muestra personas por evento, custodia, ocupación y actividad por hora.
- [x] Abrir Ubicaciones con 300 ubicaciones tarda < 0,5 s.
- [x] Ticket se exporta a PDF; la impresión por diálogo del sistema queda por validar en Windows con impresora real.
- [x] `./build.sh` genera ejecutable en Linux; **Windows (Git Bash) pendiente de validar**.
- [ ] (pendiente, requiere Windows/CI) GitHub Actions produce artefactos `.exe`, `Setup.exe` (Inno) y `.msix` en cada tag.
- [ ] (pendiente, requiere Windows) Setup.exe instala, crea acceso directo y desinstala limpiamente sin borrar la BD sin confirmar.
- [x] Tests unitarios de datos, asignación y licencias pasan en CI.

## Decisiones

- **CustomTkinter** sobre PySide6/Flet: ligero, moderno, empaquetado simple.
- **Licencia firmada offline (Ed25519)**: sin internet en el evento, difícil de falsificar.
- **Modo demo en vez de bloqueo total**: permite probar el sistema; límites 1 evento/5 personas. "Usuarios" interpretado como personas registradas, no cuentas.
- **Licencia maestra**: mismo mecanismo firmado, tipo `master`, emitida solo por el propietario.
- **Un PC, sin login**: SQLite sin concurrencia; roles y red quedan para otro spec.
- **QR + código corto siempre**: el operador elige mostrar/imprimir; el código sirve si falla el QR.
- **Ubicación por estantes con capacidad**: permite saber qué está lleno y localizar rápido.
- **MSIX sin firma real en CI**: firma opcional vía secrets; sin certificado, instalación solo en modo desarrollador.
- **Clave `CM2` con firma sobre bytes exactos** en lugar de JSON canónico: evita fallas de interoperabilidad entre PHP/Node/Python. El `.lic` v1 se mantiene solo por compatibilidad.
- **Atado a equipo opcional** (`machine_id`): licencia por cliente de tipo master, atada solo si el emisor lo pide; la huella no es reversible y no hay validación en línea.
- **Sin servidor de licencias en la app**: el sistema web del propietario emite y registra; la app solo verifica. Revocación diferida a otro spec.
- **Calendario propio** en vez de `tkcalendar`: sin dependencias extra y con el tema de la app.
- **Cuadrículas en un solo canvas** en vez de un botón por ubicación: 300 ubicaciones pasaron de ~5 s a ~0,1 s.
- **Dashboard en Inicio**: se permite como funcionalidad básica; reportes avanzados siguen fuera.
- **Definición cerrada en una ronda de preguntas**; paleta exacta derivada de `logo.png` (azul, marino, amarillo, naranja).

## Riesgos

- MSIX requiere firma confiable para instalarse en equipos normales; el .exe/Inno es la vía principal.
- PyInstaller + CustomTkinter necesita incluir assets de tema (`--collect-data`).
- Antivirus puede marcar el ejecutable PyInstaller sin firma.
- Límites demo se evaden borrando la BD; se mitiga guardando contador en `meta` y un marcador secundario (no infalible; aceptable).
- Pérdida de la clave privada de licencias invalida la emisión futura; respaldarla fuera del repo.
- Impresión térmica varía por driver; validar con la impresora real.
- La copia automática de BD solo ocurre al cerrar la app; un corte de luz no la genera (SQLite sí conserva lo ya confirmado).
- Nombre de evento distinto entre la licencia y la app invalida la licencia: el sistema web debe emitirla con el nombre exacto.
- Sin revocación offline: una clave filtrada sirve hasta que venza; usar vigencia corta y `max_people`.
- Un reloj del equipo adelantado/atrasado puede extender una licencia; no hay detección de retroceso de fecha.
- Rutas de Windows (Inno, MSIX, CI) escritas pero no ejecutadas en esta etapa.
