# Prompts y decisiones del proyecto

## Prompt inicial (/spec)
> hay que crear un sistema de control de maletas, para una institucion religiosa, las personas llegan
> se registra su nombre su dni se registra su equipaje y se guarda en una ubicacion indicada por el
> sistema, se le entrega un codigo o un QR o se imprime segun la necesidad, debe haber un buscador por
> nombres o dni, Python + SQLite + interfaz de escritorio, con instalador Windows y licencias por
> evento. con entorno virtuales, script bash para ejecutar run.sh y build.sh para compilar en linux y
> windows, debe poder compilarse en github debo poder generar .exe y .msix, usa interfaz moderna de
> python para el gestor de ventanas, usa colores del logo, amigable UI/UX, tendra un instalador
> amigable inno setup

## Ajuste posterior
> también poner una licencia que yo tendré, sin licencia solo pueden crear 1 evento y 5 usuarios
→ licencia maestra + modo demo (1 evento / 5 personas registradas).

## Respuestas de clarificación
CustomTkinter · estantes/zonas con capacidad · licencia firmada offline (Ed25519) · ticket QR + código
· retiro con QR/código/búsqueda · 1 PC sin login · PyInstaller + Inno + MSIX en CI · varios bultos,
teléfono y observaciones.

## Archivos
- `specs/01-control-maletas-escritorio.md` — spec original (copia en esta carpeta).
