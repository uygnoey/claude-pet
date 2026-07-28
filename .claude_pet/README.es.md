# `.claude_pet/pets` — conjunto de compañeros de ejemplo

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **Español**

Mascotas personalizadas listas para usar con **claude-pet (v0.18)**.
Se incluyen cuatro compañeros: **Dog · Fox · Scorpion · Elephant**.

> ⚠️ **Importante: la app no lee esta carpeta directamente.**
> claude-pet carga las mascotas personalizadas desde tu directorio de inicio, `~/.claude_pet/pets/`.
> La carpeta `.claude_pet/pets/` de este repositorio es un **conjunto de ejemplo distribuible** que copias
> a esa carpeta del inicio; la app nunca copia ni referencia automáticamente esta ruta del repositorio.
>
> Ten en cuenta que esto también es distinto del archivo de configuración `~/.claude_pet.json` (un archivo JSON, no una carpeta).

---

## Inicio rápido (instalación)

```bash
mkdir -p ~/.claude_pet/pets
cp -R dog fox scorpion elephant ~/.claude_pet/pets/
```

Después de copiar, **haz clic derecho en el icono de la barra de menús → elige una mascota** y aparecerán los nuevos compañeros.
El menú vuelve a escanear la carpeta cada vez que se abre, así que **no hace falta reiniciar la app**.

El menú «Abrir carpeta de mascotas» de la app crea `~/.claude_pet/pets/` si no existe y coloca allí
una guía de uso (`README.txt`) antes de abrirla en el Finder.

---

## Estructura de carpetas

```
<nombre-mascota>/
├── pet.json          # metadatos + convención de sprites (obligatorio)
├── spritesheet.webp  # hoja de sprites (obligatorio — la única imagen que se carga realmente)
└── preview.png       # imagen de vista previa (opcional, no se usa en ejecución — solo docs/galería)
```

- **El ID interno de una mascota es el nombre de su carpeta**, no el campo `id` de `pet.json`.
- En ejecución solo se leen `pet.json` y `spritesheet.webp`.
  `preview.png` no lo referencia el código (existe para las vistas previas del repositorio).

---

## Esquema de `pet.json`

```json
{
  "id": "dog",
  "displayName": "Dog",
  "description": "Un perro compañero y amistoso …",
  "spriteVersionNumber": 2,
  "spritesheetPath": "spritesheet.webp"
}
```

| Campo | Obligatorio | Significado |
|---|---|---|
| `id` | Recomendado | Para identificación. La app usa en realidad el **nombre de la carpeta** como ID. |
| `displayName` | Recomendado | Nombre mostrado en el menú del clic derecho. Si falta, se usa el nombre de la carpeta. |
| `description` | Opcional | Solo documentación; no se usa en ejecución. |
| `spriteVersionNumber` | Recomendado | Convención de la cuadrícula de la hoja de sprites. Hoy solo se define la **2**; los valores desconocidos usan la v2. |
| `spritesheetPath` | Opcional | Ruta relativa de la hoja. Por defecto `"spritesheet.webp"`. |

---

## Convención de la hoja de sprites (spriteVersionNumber 2)

La hoja se divide en una **cuadrícula fija de 8 columnas × 11 filas**.

- Tamaño de celda = `ancho de la hoja / 8` × `alto de la hoja / 11`
- Las mascotas incluidas son todas de **1536 × 2288** → celdas de **192 × 208**
- Cada estado de animación llena una **fila** dada desde la columna 0, de izquierda → derecha, con un número fijo de fotogramas.

| Fila (row) | Estado | Fotogramas |
|---|---|---|
| 0 | `idle` | 7 |
| 1 | `running-right` | 8 |
| 2 | `running-left` | 8 |
| 3 | `waving` | 4 |
| 4 | `jumping` | 5 |
| 5 | `failed` | 8 |
| 6 | `waiting` | 6 |
| 7 | `running` | 6 |
| 8 | `review` | 6 |
| 9–10 | (reservado, sin uso) | — |

- **`idle` es obligatorio.** Una mascota sin fotogramas `idle` utilizables se considera inválida.
- Mantén transparentes (alfa) los márgenes/fondo de cada celda.

### Tiempos de animación

En lugar de fps fijos, cada estado tiene una **duración por fotograma (ms)** (aproximada):

| Estado | Por fotograma | Reproducción |
|---|---|---|
| `idle` | 430 ms | en bucle (~25 s de pausa entre bucles) |
| `waiting` | 340 ms | en bucle |
| `review` | 360 ms | en bucle |
| `failed` | 260 ms | en bucle |
| `waving` | 200 ms | se reproduce una vez |
| `jumping` | 150 ms | se reproduce una vez |
| `running` / `running-left` / `running-right` | 90 ms | en bucle (≈ 11 fps) |

Los estados no listados usan el valor por defecto de 400 ms, en bucle.

---

## Crea tu propia mascota

1. Crea `~/.claude_pet/pets/<nombre>/`.
2. Coloca `spritesheet.webp` según la cuadrícula 8×11 anterior (como mínimo la fila `idle`).
3. Escribe `pet.json` (`spriteVersionNumber: 2`).
4. Vuelve a abrir el menú del clic derecho y tu mascota aparecerá.

> El formato antiguo también es compatible: en lugar de `pet.json`, una mascota puede ser **subcarpetas por estado
> con secuencias PNG** (`idle/`, `running/`, …). El gato integrado usa este método. Para mascotas nuevas, usa el formato de hoja.

---

## Cuando falta la carpeta

La app funciona sin `~/.claude_pet/pets/`, y el valor por defecto es el **gato integrado (Cat 🐱)**.
Si una mascota guardada desaparece o se corrompe, vuelve automáticamente a esta mascota integrada.

---

> 🛍️ **Muy pronto:** un marketplace de mascotas para explorar y añadir nuevos compañeros con un clic.
