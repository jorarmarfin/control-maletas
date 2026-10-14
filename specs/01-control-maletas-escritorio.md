# SPEC 01 — Sistema de control de maletas (escritorio)

**Estado:** Approved
**Depende de:** ninguna
**Fecha:** 2026-10-14
**Objetivo:** App de escritorio (Python + SQLite + CustomTkinter) para registrar personas y su equipaje, asignar ubicación automática, emitir ticket QR/código, buscar y registrar el retiro, con licencias offline por evento e instaladores Windows (.exe Inno Setup y .msix) generados en GitHub Actions.

## Alcance

### Dentro
- Registro de persona: nombre, DNI, teléfono (opcional), observaciones (opcional).
- Registro de 1..N bultos por persona, con descripción opcional por bulto.
- Asignación automática de ubicación libre en estantes/zonas configurables con capacidad.
- Ticket con QR + código corto (ej. `A3F7K2`): mostrar en pantalla, imprimir o exportar a PDF.
- Buscador por nombre (parcial, sin tildes) o DNI.
- Retiro: escanear QR (lector USB como teclado) o código manual / búsqueda → confirmar → liberar ubicación y registrar hora.
- Gestión de eventos (un evento activo a la vez) y configuración de zonas/ubicaciones.
- Licencia por evento: archivo firmado (Ed25519) validado offline; herramienta aparte para generarlas.
- Licencia **maestra** (del propietario): mismo formato firmado, sin límite de eventos ni de registros, válida en cualquier evento; la emites tú con `tools/gen_license.py --type master`.
- **Modo sin licencia (demo)**: máximo 1 evento y 5 personas registradas ("usuarios" = personas con equipaje; no hay cuentas de login). Retiro, búsqueda y tickets funcionan normal dentro del límite.
- Tema moderno con colores extraídos de `logo.png`, claro/oscuro.
- Entorno virtual, `run.sh`, `build.sh` (Linux y Windows vía Git Bash), workflow GitHub Actions.
- Instaladores: .exe portable (PyInstaller), Setup.exe (Inno Setup), .msix.

### Fuera (specs futuros)
- Login/roles de usuario, multi-PC o red.
- Foto del equipaje / webcam.
- Servidor de licencias online.
- Firma con certificado de code signing real (paso opcional por secrets).
- Impresión directa ESC/POS (se usa impresión del sistema/PDF).
- Reportes avanzados; solo exportación CSV básica del evento.

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
- Licencia: archivo `.lic` JSON (`type`, `event`, vigencia, `max_people`) + firma; límites demo (1 evento, 5 personas) fijos en código; la clave pública va embebida; la privada solo en la herramienta del emisor (no en el repo).

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

## Criterios de aceptación

- [ ] `./run.sh` crea `.venv` si falta, instala dependencias y abre la app.
- [ ] Registrar persona con 3 bultos asigna 3 ubicaciones libres y muestra ticket con QR y código.
- [ ] Un DNI duplicado en el mismo evento advierte y permite agregar bultos a la persona existente.
- [ ] Con zonas llenas, la app avisa claramente y no registra.
- [ ] Buscar por "perez" o "12345678" devuelve la persona en <1 s con 5 000 registros.
- [ ] Escanear QR/código marca bultos `delivered`, libera ubicaciones y guarda `delivered_at`.
- [ ] Sin licencia: se puede crear 1 evento; el 2.º evento es rechazado con mensaje que invita a activar licencia.
- [ ] Sin licencia: se registran 5 personas; la 6.ª es rechazada con mensaje claro (consultas y retiros siguen funcionando).
- [ ] Licencia de evento válida levanta los límites solo para su evento; vencida o de otro evento vuelve al modo demo.
- [ ] Licencia maestra válida levanta todos los límites en cualquier evento.
- [ ] Una licencia con firma alterada es rechazada; funciona sin internet.
- [ ] Ticket se exporta a PDF e imprime vía diálogo del sistema.
- [ ] `./build.sh` genera ejecutable en Linux y en Windows (Git Bash).
- [ ] GitHub Actions produce artefactos `.exe`, `Setup.exe` (Inno) y `.msix` en cada tag.
- [ ] Setup.exe instala, crea acceso directo y desinstala limpiamente sin borrar la BD sin confirmar.
- [ ] Tests unitarios de datos, asignación y licencias pasan en CI.

## Decisiones

- **CustomTkinter** sobre PySide6/Flet: ligero, moderno, empaquetado simple.
- **Licencia firmada offline (Ed25519)**: sin internet en el evento, difícil de falsificar.
- **Modo demo en vez de bloqueo total**: permite probar el sistema; límites 1 evento/5 personas. "Usuarios" interpretado como personas registradas, no cuentas.
- **Licencia maestra**: mismo mecanismo firmado, tipo `master`, emitida solo por el propietario.
- **Un PC, sin login**: SQLite sin concurrencia; roles y red quedan para otro spec.
- **QR + código corto siempre**: el operador elige mostrar/imprimir; el código sirve si falla el QR.
- **Ubicación por estantes con capacidad**: permite saber qué está lleno y localizar rápido.
- **MSIX sin firma real en CI**: firma opcional vía secrets; sin certificado, instalación solo en modo desarrollador.
- **Definición cerrada en una ronda de preguntas**; paleta exacta se deriva de `logo.png` en el paso 2.

## Riesgos

- MSIX requiere firma confiable para instalarse en equipos normales; el .exe/Inno es la vía principal.
- PyInstaller + CustomTkinter necesita incluir assets de tema (`--collect-data`).
- Antivirus puede marcar el ejecutable PyInstaller sin firma.
- Límites demo se evaden borrando la BD; se mitiga guardando contador en `meta` y un marcador secundario (no infalible; aceptable).
- Pérdida de la clave privada de licencias invalida la emisión futura; respaldarla fuera del repo.
- Impresión térmica varía por driver; validar con la impresora real.
- Si la PC falla durante el evento no hay respaldo: incluir copia automática de la BD al cerrar.
