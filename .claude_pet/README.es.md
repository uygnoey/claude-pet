# `.claude_pet/pets` — conjunto de compañeros de ejemplo

[English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **Español**

Mascotas personalizadas listas para usar con **claude-pet**.
Se incluyen cuatro compañeros: **Dog · Fox · Scorpion · Elephant**.

> ℹ️ **La app las instala por ti: normalmente no tienes que copiar nada.**
> claude-pet carga las mascotas personalizadas desde tu directorio de inicio, `~/.claude_pet/pets/`.
> Este árbol se distribuye dentro de la app y **en cada arranque la app copia lo que falte** en tu
> carpeta de inicio: los cuatro `README*.md` en `~/.claude_pet/` y cada mascota en
> `~/.claude_pet/pets/<nombre>/`.
>
> La copia es **solo de lo que falta y nunca destructiva**. Un README que ya existe se deja intacto y
> una carpeta de mascota que ya existe se omite **entera** — la app no mira dentro, así que una
> mascota que hayas editado nunca se sobrescribe a medias. Nada se sobrescribe ni se borra.
> Si borras una mascota de serie, el siguiente arranque la repone; si editas una, se queda como está.
>
> En un sistema de archivos donde no se puede garantizar una instalación segura (algunas carpetas de
> inicio en red o montadas), la app **se salta las mascotas** en lugar de dejar una a medio hacer. Los
> cuatro `README*.md` sí pueden aparecer, así que encontrarlos aquí **no** significa que las mascotas
> hayan llegado: mira en `~/.claude_pet/pets/` y, si está vacía, usa el **caso 2** de la copia manual
> de abajo. En ese sistema de archivos una mascota borrada tampoco se repone, así que la copia que
> hagas a mano es la única que tienes: consérvala.
>
> Ten en cuenta que esto también es distinto del archivo de configuración `~/.claude_pet.json` (un archivo JSON, no una carpeta).

---

## Copia manual (opcional)

La app lo hace sola, así que normalmente no necesitas esta sección. Hay dos casos en los que sí:

**1. Quieres una segunda copia de una mascota con un nombre tuyo** — ya tienes las de serie y
quieres un duplicado editable al lado:

```bash
cd ~/.claude_pet
cp -R pets/dog pets/dog-mia         # a un nombre que aún no exista
```

El nombre del menú sale de `displayName` dentro de `pet.json`, **no** de la carpeta. Abre
`pets/dog-mia/pet.json` y cambia `"displayName": "Dog"` por el tuyo — o borra esa línea para que use
el nombre de la carpeta. Si no, el menú muestra dos entradas que ponen «Dog».

**2. La app no pudo instalarlas** (véase la nota de arriba). Entonces `~/.claude_pet/pets/` está
vacía, así que el origen tiene que ser el paquete de la app:

```bash
mkdir -p ~/.claude_pet/pets
cp -R /Applications/ClaudePet.app/Contents/Resources/.claude_pet/pets/dog ~/.claude_pet/pets/dog
```

¿Ejecutas desde el código fuente? El mismo origen está en `.claude_pet/pets/dog` del repositorio.

> ⚠️ En ambos casos, copia **a un nombre que aún no exista**. Si el destino ya existe, `cp -R` mete
> la copia *dentro* de él y acabas con `pets/dog/dog/`, una carpeta sobrante dentro de tu mascota. Y
> copiar dentro de `pets/` sin dar un nombre sobrescribe los archivos que se llamen igual y pierdes
> tus ediciones. El sembrado de la app nunca toca una carpeta de mascota que ya está; no lo hagas tú
> a mano.

Después de copiar, **haz clic derecho en la propia mascota → elige una mascota** y aparecerá el nuevo compañero.
(No hay icono en la barra de menús ni en el Dock: el menú solo está en la mascota que ves en pantalla.)
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
