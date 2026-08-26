# RED Encuestas — Backend

API en FastAPI + PostgreSQL/PostGIS que recibe las encuestas y los turnos de asistencia
capturados desde la app de tablet, aplica las reglas anti-simulación, y sirve los datos
a las vistas de supervisor y administrador.

## 1. Requisitos

- Python 3.11+
- Docker (para levantar PostgreSQL fácil; si ya tienen un servidor Postgres propio, no hace falta)

## 2. Levantar la base de datos (local, para pruebas)

```bash
docker compose up -d
```

Esto levanta PostgreSQL con PostGIS ya instalado, en el puerto 5432.

## 3. Instalar dependencias de Python

```bash
python -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Abre `.env` y ajusta al menos `JWT_SECRET` (pon algo largo y aleatorio) y `CORS_ORIGINS`
(la URL real de tu app en Vercel, para que el navegador la deje llamar a esta API).

## 5. Crear el primer usuario administrador

```bash
python seed_admin.py
```

Esto crea un usuario con código `admin` y contraseña `cambia-esta-clave` — cámbiala
apenas puedas (todavía no hay endpoint de "cambiar mi propia contraseña", eso queda
pendiente; por ahora un admin puede desactivar/crear usuarios desde `/usuarios`).

## 6. Levantar el servidor

```bash
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000`. La documentación interactiva (para probar
cada endpoint a mano) está en `http://localhost:8000/docs`.

## 7. Crear coordinadores, supervisores y brigadistas

Con el token del admin (lo da `/auth/login`), llama a `POST /usuarios` una vez por
persona. Ejemplo del cuerpo:

```json
{
  "nombre": "Jonathan Reyes",
  "codigo": "coord01",
  "password": "temporal123",
  "rol": "coordinador",
  "supervisor_id": 2,
  "brigada_nombre": "Brigada Centro 1"
}
```

## Qué falta todavía (pendiente, no bloquea usar lo demás)

- **Storage de audio/fotos**: hoy se guardan en disco local del servidor (carpeta
  `storage/`). Cuando conecten un bucket tipo S3, solo hay que editar `app/storage.py`.
- **Transcripción de audio con IA**: no está implementada todavía — es la siguiente
  pieza sobre esta base.
- **Mapas de calor por pregunta / mapas con pines**: se generan aparte con el pipeline
  de PyQGIS, leyendo de esta base de datos una vez que haya datos reales.
- **Geocerca real por sección**: por ahora solo funciona si a un brigadista se le
  asigna manualmente una zona de referencia (`zona_lat`/`zona_lng` en su usuario);
  la integración con el mapa de disponibilidad territorial queda pendiente.
- **Cambiar mi propia contraseña**: no existe ese endpoint todavía, solo alta/baja
  por parte del administrador.

## Conectar la app de tablet a este backend

En `app.js` de la PWA, la función `sincronizar()` tiene comentado el `fetch` real —
hay que descomentarlo y apuntarlo a `https://TU-SERVIDOR/visitas` (y lo mismo para
turnos en `coordinador.js`) una vez que este backend esté corriendo en un servidor
con URL pública, no solo en tu compu.
