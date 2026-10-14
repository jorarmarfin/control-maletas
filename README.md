# Control Maletas

App de escritorio (Python + SQLite + CustomTkinter) para controlar el equipaje en eventos:
registro de personas y bultos, ubicación automática, ticket QR/código, búsqueda y retiro.
Licencias offline por evento.

## Uso en desarrollo
```bash
./run.sh            # crea .venv, instala dependencias y abre la app
python -m pytest    # tests (con .venv activado)
```

## Compilar
```bash
./build.sh              # Linux: dist/ControlMaletas/   ·  Windows (Git Bash): + portable .exe, Setup.exe (Inno), .msix
./build.sh --no-test
```
Windows necesita [Inno Setup 6](https://jrsoftware.org/isdl.php) y el Windows SDK (makeappx/signtool) para Setup.exe y .msix.
GitHub Actions (`.github/workflows/build.yml`) hace todo en cada push; en tags `v*` publica un Release.

**MSIX**: sin certificado real se firma con un autofirmado de prueba (`dist/ControlMaletas-test.cer`
debe instalarse como "Personas de confianza" para poder instalar el .msix). Para firma real, definir los
secrets `MSIX_PFX_PATH` / `MSIX_PFX_PASSWORD`.

## Licencias
- **Sin licencia (demo):** 1 evento y 5 personas registradas.
- **Evento:** válida para un evento (por nombre exacto), con vigencia y máximo de personas opcional.
- **Maestra:** sin límites.

```bash
python tools/gen_keys.py      # una sola vez: crea keys/private.key (NO subir, respaldar) y embebe la pública
python tools/gen_license.py --type event --event "Retiro Octubre" --licensee "Parroquia" \
       --from 2026-10-01 --to 2026-10-31 --max-people 500
python tools/gen_license.py --type master --licensee "Propietario"
```
> La clave pública actual está embebida en `src/control_maletas/license_keys.py`. Si regenera el par con
> `--force`, las licencias anteriores dejan de ser válidas y hay que recompilar.

## Datos
Base de datos en `%APPDATA%\ControlMaletas\maletas.db` (Windows) o `~/.local/share/ControlMaletas/`.
Al cerrar se guarda una copia en `backups/` (últimas 10). Variable `CONTROL_MALETAS_DATA` cambia la carpeta.

## Pantallas
- **Inicio:** dashboard (personas por evento, custodia, ocupación, actividad por hora).
- **Registrar**, **Buscar / Retirar**, **Ubicaciones**, **Eventos**, **Licencia**.

## Flujo del operador
1. **Eventos**: crear evento (crea zona A con 50 ubicaciones) y agregar zonas si hace falta.
2. **Registrar**: DNI, nombre, bultos → se asigna ubicación y se muestra el ticket (QR + código; imprimir o PDF).
3. **Buscar / Retirar**: por nombre, DNI o código. El lector QR escribe el código y Enter confirma la entrega.
