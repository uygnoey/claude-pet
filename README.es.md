# 🐱 Claude Pet

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **Español**

Una mascota de escritorio que flota en tu pantalla y vigila tu uso de Claude Code o Codex, al estilo de Codex Pets.
Renderizado nativo en macOS (AppKit): sin marco de ventana, sin fondo, sin estelas.

> 🧪 v0.24 — la app de macOS está notarizada; la versión de Windows se distribuye como instalador y zip (sin firmar — ver la sección Windows).

![Claude Pet](preview.png)

## Plataformas compatibles

|  | macOS | Windows |
| --- | --- | --- |
| Sistema | macOS 12 o posterior | Windows 10/11 (64 bits) |
| Chip | Apple Silicon e Intel (compilación universal) | x64 |
| Descarga | `ClaudePet.dmg` (Apple Silicon) · `ClaudePet-universal.dmg` (Intel) | `claude-pet-win-setup.exe` (instalador) · `claude-pet-win.zip` (portátil) |
| Firma | Firmada con Developer ID y notarizada por Apple | Sin firmar: Windows pregunta una vez antes de la primera ejecución |
| Actualizaciones | En la app: comprueba cada hora e instala desde el menú contextual | En la app: comprueba cada hora e instala desde el menú contextual (instalador o zip portátil) |
| Inicio al iniciar sesión | Menú contextual → “Abrir al iniciar sesión” (macOS 13+; en macOS 12, Preferencias del Sistema → Usuarios y grupos → Ítems de inicio) | Menú contextual → “Abrir al iniciar sesión” (también como opción del instalador) |
| Claude Code | Lee la credencial de Claude Code (Llavero o archivo de credenciales) | Lee el archivo de credenciales de Claude Code |
| Mascotas | Gato incluido + 4 más, y las tuyas en `~/.claude_pet/pets` | Igual, en `%USERPROFILE%\.claude_pet\pets` |
| Desinstalar | Clic derecho → Desinstalar por completo… | Configuración → Aplicaciones → Desinstalar |

## Descarga e instalación (recomendado)

**No necesitas Python** — va incluido dentro de la app, que está **certificada (notarized) por Apple**, así que se abre sin avisos de Gatekeeper.

1. Descarga `ClaudePet.zip` desde [**Releases**](https://github.com/uygnoey/claude-pet/releases/latest) — en un **Mac Intel**, descarga `ClaudePet-universal.zip` (disponible desde v0.10)
2. Descomprime → mueve `ClaudePet.app` a tu carpeta de **Aplicaciones** → doble clic
3. macOS 12+ (Apple Silicon; Intel con el zip universal desde v0.10)

### Permisos (primer arranque)

La mascota solo lee **`~/.claude` (registros de Claude Code, para las alertas de pico) y el token OAuth de tu Llavero** — y, si usas Codex, `~/.codex` (su archivo de sesión y sus registros, también para las alertas de pico). Nunca toca otras carpetas (Fotos, Descargas, Documentos, …). En el primer arranque solo verás esto:

| Aviso | Qué | Elige |
|---|---|---|
| **Llavero** — "Claude Code-credentials" | token OAuth para obtener el % calculado por el servidor | **Permitir siempre** |
| **"datos de otras apps"** — `~/.claude` | leer los registros para las alertas de pico (solo números, en este equipo) | **Permitir** |

- El token se lee **una vez por arranque**, y como la app está firmada la decisión se recuerda: no se te volverá a preguntar.
- **No aparecen avisos de Fotos / Descargas / Música / Escritorio / Documentos / iCloud / volúmenes de red.** (Antes sí, porque la mascota lanzaba la CLI `claude` como proceso hijo y su escaneo del home se atribuía a la app; esa llamada a la CLI ahora está desactivada por defecto.)
  - Para complementar la fila por modelo (Fable) mediante la CLI, usa `CLAUDE_PET_USE_CLI=1`, pero entonces los avisos de carpetas vuelven.

### Se necesita Claude Code o Codex

La mascota es un HUD del **uso de Claude Code o Codex**: los números son el % del servidor que se obtiene con la sesión de cada herramienta, y sus registros locales solo alimentan las alertas de pico. Por eso el **modo suscripción requiere tener Claude Code o Codex instalado y con sesión iniciada.**

- Si Claude Code no está instalado, la mascota muestra **"Claude Code no instalado"** en lugar de la píldora. **Clic derecho → "⬇︎ Instalar Claude Code…"** ejecuta el instalador oficial ([`claude.ai/install.sh`](https://claude.ai/install.sh)) en Terminal y luego inicia sesión.
- Si está instalado pero sin sesión, **clic derecho → "🔑 Iniciar sesión en Claude Code…"** inicia el acceso.
- Codex funciona igual: mientras Codex se muestra en la píldora sin sesión iniciada, **clic derecho → "⬇︎ Instalar Codex…"** (`npm install -g @openai/codex` y luego `codex login`, en Terminal) o **"🔑 Iniciar sesión en Codex…"** (`codex login`). En Windows se abren en una consola nueva de PowerShell.
- Al terminar, el uso aparece en la siguiente actualización, sin reiniciar.
- Nota: el **modo API** (clic derecho → Ajustes → clave de Admin API; para Codex, una clave de OpenAI Admin API) funciona sin iniciar sesión.

### Actualizaciones

Cada hora tras el arranque (nunca al arrancar) la app comprueba la última versión en GitHub; si hay una nueva, **clic derecho → "⬆︎ Instalar nueva versión"** la descarga, reemplaza y reinicia automáticamente. **Clic derecho → "⬆︎ Buscar actualizaciones…"** comprueba ahora mismo e instala directamente la última versión.

---

## Windows

Windows 10/11 (64 bits) tiene la misma píldora, paseos, ajustes y mascotas. Con cada versión se publican dos archivos:

- **`claude-pet-win-setup.exe`** — instalador. Se instala para el usuario actual (sin permisos de administrador), añade una entrada en el menú Inicio y otra en «Aplicaciones y características» para desinstalar, y ofrece **Iniciar Claude Pet al iniciar sesión**.
- **`claude-pet-win.zip`** — versión portátil y de actualización. Descomprímelo donde quieras y ejecuta `ClaudePet\ClaudePet.exe`.

**Sobre el aviso de SmartScreen.** La compilación para Windows aún no está firmada, así que la primera vez que ejecutes el instalador o `ClaudePet.exe` Windows muestra *«Windows protegió su PC»*. Pulsa **Más información** y luego **Ejecutar de todas formas**. En equipos con la comprobación de aplicaciones de SmartScreen desactivada aparece en su lugar el clásico *«Abrir archivo - Advertencia de seguridad»* (editor desconocido): pulsa **Ejecutar**. Con el instalador cualquiera de los dos avisos aparece una vez; con el zip portátil el diálogo clásico puede repetirse en cada inicio hasta que desmarques *Preguntar siempre antes de abrir este archivo* (o desbloquees el zip en sus Propiedades antes de extraerlo); es el aviso de que el editor es desconocido, no la detección de algo dañino. Si el navegador (Edge) bloquea la descarga por el mismo motivo, elige **Conservar** → **Conservar de todas formas**. La firma de código eliminará el aviso en una versión posterior.

Inicia sesión en Claude Code o Codex en Windows primero (`claude` / `codex login`) y luego abre Claude Pet: los números de uso salen del archivo de credenciales en `%USERPROFILE%\.claude` (o `%USERPROFILE%\.codex`), y los registros de ahí solo se leen para las alertas de pico. Tus propias mascotas van en `%USERPROFILE%\.claude_pet\pets\<nombre>\` (clic derecho → Mascotas → Añadir mascota… abre esa carpeta). El icono de la bandeja queda por defecto en el desbordamiento de la barra de tareas (`^`); arrástralo fuera para verlo siempre. Clic derecho → Desinstalar por completo… borra ajustes y registros; el programa se quita desde «Aplicaciones y características».

## Compilar desde el código (desarrolladores)

Para compilar necesitas un **Python compilado como framework**:

- **Homebrew**: `brew install python@3.13` (ya es framework)
- **pyenv**: instala con `--enable-framework`
  ```bash
  PYTHON_CONFIGURE_OPTS="--enable-framework" pyenv install 3.13.14 && pyenv global 3.13.14
  ```
  > ⚠️ No uses el Python del sistema (`/usr/bin/python3`, 3.9) — pyobjc no compila ahí.

```bash
./build_app.sh install     # build+firma local → instala en /Applications y ejecuta
python3 claude_pet.py --report   # solo informe en terminal, sin GUI

./release.sh build         # app autocontenida distribuible (py2app); sign / notarize / universal / dmg / publish son subcomandos aparte
```
`release.sh` requiere registrar las credenciales de notarización una vez (ver el comentario al inicio del script).

## Comportamiento

- **Quieta por defecto** — primer fotograma congelado; solo respira/parpadea una vez cada 25s
- **Cuando el ratón se acerca** — saluda con la mano (30s de enfriamiento)
- **Pasea por su cuenta de vez en cuando** — descansa en su sitio; cuando el ratón se está moviendo se acerca una vez y
  mira un momento, y si no, elige un punto al azar en cualquier parte de la pantalla, camina hasta allí y descansa donde llega
  (no vuelve al sitio anterior). Nunca camina sobre el cursor y se detiene donde está si la agarras o abres el menú o los Ajustes
- **A veces sigue al ratón** durante 10–20 segundos, despacio y a distancia, luego te mira y descansa donde se detuvo.
  **Con más de un monitor salta entre ellos** de vez en cuando: un pequeño brinco, un desvanecimiento y aterriza en un lugar seguro de la otra pantalla
- **Pliega la píldora al caminar** y solo se mueve la mascota. Al llegar muestra la píldora de uso un momento aunque la tengas
  plegada, y cuando termina de mirar recupera lo que tenías
- **Agarrar y arrastrar** — corre en la dirección del arrastre; **doble clic** = salto + **actualización de uso inmediata** (recarga ignorando la caché)
- **Cuando el consumo de tokens se dispara** — pulso de color de alerta + cara de pánico, y la etiqueta de sesión de ese proveedor se pone roja con ▲ en la píldora:
  - 🔴 pico de sesión (o de Codex) / 🟣 pico de modelo (Fable/Opus) / 🟠 pico semanal
  - Los picos se leen de los registros locales de Claude Code y Codex. El umbral usa un límite que la mascota **aprende del % del servidor**:
    no hay nada que configurar; hasta que lo aprende no hay alertas de pico (ni para un proveedor en modo API)
- **Cuando detecta un reinicio de sesión** (el % de sesión del servidor baja de más del 5 % a menos del 1 %) — salta de alegría

## Controles

- **Rueda (sobre la mascota)**: cambiar tamaño (0.3×–2.0×, se guarda; por defecto 0.5×)
- **Clic (botón ⌄)**: mostrar/ocultar la píldora de uso
- **Arrastrar**: mover (se guarda la posición)
- **Clic derecho**: menú — (Instalar / Iniciar sesión en Claude Code o Codex, cuando haga falta) / Ajustes / Mostrar u ocultar / Pasear por la pantalla (activar/desactivar) / Restablecer tamaño / Mascotas (elegir o añadir) / Desinstalar / Salir / Buscar actualizaciones

## La píldora de uso

Una píldora pequeña junto a la mascota, en dos líneas:

- **Línea 1 — uso**: `Sesión 42% · Semanal 17% · Fable 12%` — sesión (5h) / total semanal / semanal por modelo, tal como los
  da el servidor. Codex tiene su propio bloque (con su marca) junto al de Claude. Un proveedor en modo API muestra
  el coste: `Hoy $3.21 · Este mes $27.50`.
- **Línea 2 — reinicios**: `reinicio Sesión en 3h 42m · Semanal en 2d 3h`.
- **Los números son siempre del servidor**: esmeralda = % calculado por el servidor, coral = coste de API. La mascota nunca
  muestra un número estimado a partir de los registros: sin valor del servidor la píldora muestra un estado (p. ej. "Token
  expirado — ejecuta Claude Code una vez para restaurar el uso", un aviso de inicio de sesión o "Nada que mostrar" si ocultas
  ambos proveedores).
- **El color de la etiqueta dice cuánto queda**: blanco, amarillo desde el 50 %, rojo desde el 85 % — y rojo con ▲ mientras
  ese medidor se dispara.
- El texto usa la tipografía **Pretendard** incluida en la app (SIL Open Font License), así se ve igual en cualquier equipo.

## Tus propias mascotas

Clic derecho → **Mascotas** lista el gato integrado y cada carpeta de `~/.claude_pet/pets/`; **Añadir mascota…** abre esa
carpeta con un README que describe el formato. Una mascota es una carpeta con `pet.json` + `spritesheet.webp` (el README
tiene la disposición de la hoja). La lista se vuelve a leer cada vez que abres el menú, así que una carpeta nueva aparece sin
reiniciar. También se reconoce un zip extraído un nivel de más (`pets/nombre/nombre/pet.json`), y `__MACOSX` se ignora.

## Ajustes (clic derecho → Ajustes)

- **Claude Code** y **Codex** tienen cada uno su sección, con la misma forma:
  - **Mostrar en la píldora** sí/no
  - **Fuente de datos**: suscripción (cuenta con sesión iniciada) / API (coste de Admin API — hoy y este mes; con un presupuesto mensual la píldora muestra `Este mes $27.50 / $50` y la etiqueta «Este mes» pasa a amarillo/rojo según la parte usada, mientras los importes siguen en coral)
  - **Indicadores** visibles — Claude Code: sesión / semanal / por modelo / crédito; Codex: sesión / semanal
  - **Clave de Admin API** y **presupuesto mensual** — Codex usa una **clave de OpenAI Admin API**
- Después, sensibilidad de picos y saludo del ratón on/off. No hay nada que calibrar: los límites de las alertas de pico se aprenden del % del servidor.

- **Pasear por la pantalla**: se activa o desactiva con la casilla del menú de clic derecho (activado por defecto); también cubre seguir al ratón
  y saltar entre monitores. Si en Accesibilidad de macOS está activado **Reducir movimiento**, la mascota no se mueve.
  Las posiciones a las que pasea o salta no se guardan; solo se recuerda donde la dejas al arrastrarla.

Todos los ajustes, tamaño y posición se guardan en `~/.claude_pet.json`.

## Límites (con honestidad)

- Los números son el % del propio servidor, así que coinciden con las pantallas de uso de Claude y de Codex. Las alertas de pico salen de los registros locales, que no incluyen el chat web/escritorio.
- El coste de Admin API es el de tu organización en Console, independiente del límite de la suscripción.
- Las claves de Admin API (Anthropic y OpenAI) se guardan en texto plano en `~/.claude_pet.json`, úsalas solo en un equipo personal.

## Licencia

[MIT](LICENSE) © 2026 Yeongyu Yang. La tipografía Pretendard incluida usa la SIL Open Font License (`fonts/`).
