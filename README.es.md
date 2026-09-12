# 🐱 Claude Pet (Edición Patch)

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **Español**

Una mascota de escritorio: Patch flota en tu pantalla y vigila tu uso de tokens de Claude, al estilo de Codex Pets.
Renderizado nativo en macOS (AppKit): sin marco de ventana, sin fondo, sin estelas.

> 🧪 Actualmente **v0.1 (beta)** — experimental; el comportamiento y las etiquetas pueden cambiar.

![Patch](preview.png)

## Descarga e instalación (recomendado)

**No necesitas Python** — va incluido dentro de la app, que está **certificada (notarized) por Apple**, así que se abre sin avisos de Gatekeeper.

1. Descarga `ClaudePet.zip` desde [**Releases**](https://github.com/uygnoey/claude-pet/releases/latest) — en un **Mac Intel**, descarga `ClaudePet-universal.zip` (disponible desde v0.10)
2. Descomprime → mueve `ClaudePet.app` a tu carpeta de **Aplicaciones** → doble clic
3. macOS 12+ (Apple Silicon; Intel con el zip universal desde v0.10)

### Permisos (primer arranque)

La mascota solo lee **`~/.claude` (registros de uso) y el token OAuth de tu Llavero**. Nunca toca otras carpetas (Fotos, Descargas, Documentos, …). En el primer arranque solo verás esto:

| Aviso | Qué | Elige |
|---|---|---|
| **Llavero** — "Claude Code-credentials" | token OAuth para que el modo Exacto obtenga el % calculado por el servidor | **Permitir siempre** |
| **"datos de otras apps"** — `~/.claude` | leer los registros de uso | **Permitir** |

- El token se lee **una vez por arranque**, y como la app está firmada la decisión se recuerda: no se te volverá a preguntar.
- **No aparecen avisos de Fotos / Descargas / Música / Escritorio / Documentos / iCloud / volúmenes de red.** (Antes sí, porque la mascota lanzaba la CLI `claude` como proceso hijo y su escaneo del home se atribuía a la app; esa llamada a la CLI ahora está desactivada por defecto.)
  - Para complementar la fila por modelo (Fable) mediante la CLI, usa `CLAUDE_PET_USE_CLI=1`, pero entonces los avisos de carpetas vuelven.

### Se necesita Claude Code

La mascota es un HUD del **uso de Claude Code**: los datos de uso (registros y token) provienen del propio Claude Code. Por eso el **modo suscripción requiere tener Claude Code instalado.**

- Si Claude Code no está instalado, la mascota muestra **"Claude Code no instalado"** en lugar de los medidores. **Clic derecho → "⬇︎ Instalar Claude Code…"** ejecuta el instalador oficial ([`claude.ai/install.sh`](https://claude.ai/install.sh)) en Terminal y luego inicia sesión.
- Si está instalado pero sin sesión, **clic derecho → "🔑 Iniciar sesión en Claude Code…"** inicia el acceso.
- Al terminar, el uso aparece en la siguiente actualización, sin reiniciar.
- Nota: el **modo API** (clic derecho → Ajustes → clave de Admin API) funciona sin Claude Code.

### Actualizaciones

Al arrancar, la app comprueba la última versión en GitHub; si hay una nueva, **clic derecho → "⬆︎ Instalar nueva versión"** la descarga, reemplaza y reinicia automáticamente.

---

## Windows (beta)

Windows 10/11 (64 bits) tiene la misma píldora, paseos, ajustes y mascotas. Con cada versión se publican dos archivos:

- **`claude-pet-win-setup.exe`** — instalador. Se instala para el usuario actual (sin permisos de administrador), añade una entrada en el menú Inicio y otra en «Aplicaciones y características» para desinstalar, y ofrece **Iniciar Claude Pet al iniciar sesión**.
- **`claude-pet-win.zip`** — versión portátil y de actualización. Descomprímelo donde quieras y ejecuta `ClaudePet\ClaudePet.exe`.

**Sobre el aviso de SmartScreen.** La compilación para Windows aún no está firmada, así que la primera vez que ejecutes el instalador o `ClaudePet.exe` Windows muestra *«Windows protegió su PC»*. Pulsa **Más información** y luego **Ejecutar de todas formas**. Aparece una vez por archivo; es el aviso de que el editor es desconocido, no la detección de algo dañino. Si el navegador (Edge) bloquea la descarga por el mismo motivo, elige **Conservar** → **Conservar de todas formas**. La firma de código eliminará el aviso en una versión posterior.

Inicia sesión en Claude Code en Windows primero (`claude`) y luego abre Claude Pet: el modo Exacto lee el archivo de credenciales de Claude Code y la estimación lee los registros en `%USERPROFILE%\.claude`. Tus propias mascotas van en `%USERPROFILE%\.claude_pet\pets\<nombre>\` (clic derecho → Mascotas → Añadir mascota… abre esa carpeta). El icono de la bandeja queda por defecto en el desbordamiento de la barra de tareas (`^`); arrástralo fuera para verlo siempre. Clic derecho → Desinstalar por completo… borra ajustes y registros; el programa se quita desde «Aplicaciones y características».

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

./release.sh               # app autocontenida distribuible (py2app) + firma Developer ID + notarización + zip
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
- **Cuando el consumo de tokens se dispara** — pulso de color de alerta + cara de pánico, y ese medidor se pone rojo con ▲ en la píldora:
  - 🔴 pico de sesión / 🟣 pico de modelo (Fable/Opus) / 🟠 pico semanal
- **Cuando detecta un reinicio de sesión** — salta de alegría

## Controles

- **Rueda (sobre la mascota)**: cambiar tamaño (0.3×–2.0×, se guarda; por defecto 0.5×)
- **Clic (botón ⌄)**: mostrar/ocultar la píldora de uso
- **Arrastrar**: mover (se guarda la posición)
- **Clic derecho**: menú — Ajustes / Mostrar u ocultar / Pasear por la pantalla (activar/desactivar) / Restablecer tamaño / Mascotas (elegir o añadir) / Desinstalar / Salir / Buscar actualizaciones

## La píldora de uso

Una píldora pequeña junto a la mascota, en dos líneas:

- **Línea 1 — uso**: `Sesión 42% · Semanal 17% · Fable 12%` — sesión (5h) / total semanal / semanal por modelo. El medidor
  por modelo **detecta automáticamente** el nivel superior en los registros (fable → mythos → opus). En modo API muestra
  el coste: `Hoy $3.21 · Este mes $27.50`.
- **Línea 2 — reinicios**: `reinicio Sesión en 3h 42m · Semanal en 2d 3h` (con ventana móvil, semanal muestra `-`).
- **El color del número dice de dónde sale**: esmeralda = modo Exacto (% calculado por el servidor), ámbar = estimación
  por registros (los valores llevan ≈), coral = coste de API. Si el token de Claude Code ha caducado, la línea estimada
  termina en ⚠.
- **El color de la etiqueta dice cuánto queda**: blanco, amarillo desde el 50 %, rojo desde el 85 % — y rojo con ▲ mientras
  ese medidor se dispara.
- El texto usa la tipografía **Pretendard** incluida en la app (SIL Open Font License), así se ve igual en cualquier equipo.

## Tus propias mascotas

Clic derecho → **Mascotas** lista el gato integrado y cada carpeta de `~/.claude_pet/pets/`; **Añadir mascota…** abre esa
carpeta con un README que describe el formato. Una mascota es una carpeta con `pet.json` + `spritesheet.webp` (el README
tiene la disposición de la hoja). La lista se vuelve a leer cada vez que abres el menú, así que una carpeta nueva aparece sin
reiniciar. También se reconoce un zip extraído un nivel de más (`pets/nombre/nombre/pet.json`), y `__MACOSX` se ignora.

## Ajustes (clic derecho → Ajustes)

- **Fuente de datos**: suscripción (registros de Claude Code) / API (coste de Admin API — hoy y este mes; con un presupuesto mensual la píldora muestra `Este mes $27.50 / $50` y la etiqueta «Este mes» pasa a amarillo/rojo según la parte usada, mientras los importes siguen en coral)
- **🔧 Calibración (¡lo más importante!)**: los límites de tokens son privados de Anthropic, nadie los conoce.
  En su lugar, escribe el % que aparece en **Ajustes > Uso** de la app de Claude y guarda — la app despeja
  `límite = uso actual ÷ %`. Solo se aplican los campos que introduzcas.
- **Día/hora de reinicio semanal**: si la app dice "se reinicia sáb 20:00", pon sábado/20:00. 7 días rodantes si no se define.
- Palabra clave de modelo (auto recomendado), sensibilidad de picos, saludo del ratón on/off, clave de Admin API, presupuesto mensual

- **Pasear por la pantalla**: se activa o desactiva con la casilla del menú de clic derecho (activado por defecto); también cubre seguir al ratón
  y saltar entre monitores. Si en Accesibilidad de macOS está activado **Reducir movimiento**, la mascota no se mueve.
  Las posiciones a las que pasea o salta no se guardan; solo se recuerda donde la dejas al arrastrarla.

Todos los ajustes, tamaño y posición se guardan en `~/.claude_pet.json`.

## Límites (con honestidad)

- Los datos se basan en los registros locales de Claude Code — el uso del chat web/escritorio no se incluye. Por eso puede mostrar menos que el % de la app; recalibra periódicamente para mantener la precisión.
- El coste de Admin API es el de tu organización en Console, independiente del límite de la suscripción.
- La clave de Admin API se guarda en texto plano en `~/.claude_pet.json`, úsala solo en un equipo personal.
