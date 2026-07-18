# 🐱 Claude Pet (Edición Patch)

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **Español**

Una mascota de escritorio: Patch flota en tu pantalla y vigila tu uso de tokens de Claude, al estilo de Codex Pets.
Renderizado nativo en macOS (AppKit): sin marco de ventana, sin fondo, sin estelas.

> 🧪 Actualmente **v0.1 (beta)** — experimental; el comportamiento y las etiquetas pueden cambiar.

![Patch](preview.png)

## Descarga e instalación (recomendado)

**No necesitas Python** — va incluido dentro de la app, que está **certificada (notarized) por Apple**, así que se abre sin avisos de Gatekeeper.

1. Descarga `ClaudePet.zip` desde [**Releases**](https://github.com/uygnoey/claude-pet/releases/latest) — en un **Mac Intel**, descarga `ClaudePet-universal.zip`
2. Descomprime → mueve `ClaudePet.app` a tu carpeta de **Aplicaciones** → doble clic
3. macOS 12+ (Apple Silicon; Intel con el zip universal)

### Permisos (primer arranque)

La mascota solo lee **`~/.claude` (registros de uso) y el token OAuth de tu Llavero**. Nunca toca otras carpetas (Fotos, Descargas, Documentos, …). En el primer arranque solo verás esto:

| Aviso | Qué | Elige |
|---|---|---|
| **Llavero** — "Claude Code-credentials" | token OAuth para que el modo Exacto obtenga el % calculado por el servidor | **Permitir siempre** |
| **"datos de otras apps"** — `~/.claude` | leer los registros de uso | **Permitir** |

- El token se lee **una vez por arranque**, y como la app está firmada la decisión se recuerda: no se te volverá a preguntar.
- **No aparecen avisos de Fotos / Descargas / Música / Escritorio / Documentos / iCloud / volúmenes de red.** (Antes sí, porque la mascota lanzaba la CLI `claude` como proceso hijo y su escaneo del home se atribuía a la app; esa llamada a la CLI ahora está desactivada por defecto.)
  - Para complementar la fila por modelo (Fable) mediante la CLI, usa `CLAUDE_PET_USE_CLI=1`, pero entonces los avisos de carpetas vuelven.

### Actualizaciones

Al arrancar, la app comprueba la última versión en GitHub; si hay una nueva, **clic derecho → "⬆︎ Instalar nueva versión"** la descarga, reemplaza y reinicia automáticamente.

---

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
- **Agarrar y arrastrar** — corre en la dirección del arrastre; **doble clic** = salto + **actualización de uso inmediata** (recarga ignorando la caché)
- **Cuando el consumo de tokens se dispara** — pulso de color de alerta + cara de pánico + ▲pico en el medidor:
  - 🔴 pico de sesión / 🟣 pico de modelo (Fable/Opus) / 🟠 pico semanal
- **Cuando detecta un reinicio de sesión** — salta de alegría

## Controles

- **Rueda (sobre la mascota)**: cambiar tamaño (0.3×–2.0×, se guarda; por defecto 0.5×)
- **Clic (botón ⌄)**: contraer/expandir el panel de medidores
- **Arrastrar**: mover (se guarda la posición)
- **Clic derecho**: menú — Ajustes / Contraer / Restablecer tamaño / Salir

## Tres medidores (modo suscripción)

Sesión (5h) / total semanal / semanal por modelo — cada uno con %, tokens restantes y cuenta atrás de reinicio.
El medidor por modelo **detecta automáticamente** el nivel superior en los registros (fable → mythos → opus).

## Ajustes (clic derecho → Ajustes)

- **Fuente de datos**: suscripción (registros de Claude Code) / API (coste de Admin API — hoy, este mes, medidor de presupuesto mensual)
- **🔧 Calibración (¡lo más importante!)**: los límites de tokens son privados de Anthropic, nadie los conoce.
  En su lugar, escribe el % que aparece en **Ajustes > Uso** de la app de Claude y guarda — la app despeja
  `límite = uso actual ÷ %`. Solo se aplican los campos que introduzcas.
- **Día/hora de reinicio semanal**: si la app dice "se reinicia sáb 20:00", pon sábado/20:00. 7 días rodantes si no se define.
- Palabra clave de modelo (auto recomendado), sensibilidad de picos, saludo del ratón on/off, clave de Admin API, presupuesto mensual

Todos los ajustes, tamaño y posición se guardan en `~/.claude_pet.json`.

## Límites (con honestidad)

- Los datos se basan en los registros locales de Claude Code — el uso del chat web/escritorio no se incluye. Por eso puede mostrar menos que el % de la app; recalibra periódicamente para mantener la precisión.
- El coste de Admin API es el de tu organización en Console, independiente del límite de la suscripción.
- La clave de Admin API se guarda en texto plano en `~/.claude_pet.json`, úsala solo en un equipo personal.
