# H.R-traders — Master/Followers (copia exacta)

App mínima lista para correr:

- **Backend**: FastAPI + SQLite. Sirve una UI sencilla (estática) y expone endpoints.
- **Función principal**: cuando el **master** crea una orden, se replica **exactamente** a todas las cuentas **followers** (DRY_RUN por defecto).
- **DRY_RUN**: simula envíos para que pruebes sin riesgo. Pon `DRY_RUN=false` + `TRADELOCKER_REST` correcto para mandar órdenes reales.

## Requisitos
- Docker y Docker Compose (recomendado), o Python 3.11 si prefieres correr sin Docker.

## Ejecutar con Docker
```bash
cd backend
docker build -t hrtraders .
docker run -p 8000:8000 -e DRY_RUN=true hrtraders
```
o con docker-compose desde la raíz:
```bash
docker-compose up --build
```

Abre: http://localhost:8000

## Flujo rápido en la UI
1) **Crear cuentas**:
   - Crea **1 master** (marca "Es Master").
   - Crea **followers** (is_master = false). Coloca las API keys reales cuando salgas de DRY_RUN.
2) **Probar**:
   - En el panel "Disparar orden del Master", manda una `order.create` (market/limit).
   - Revisa el **Order Map** para ver los follower_order_id simulados (o reales).
3) **Integrar con TradeLocker**:
   - Cambia `DRY_RUN=false` y ajusta `TRADELOCKER_REST`.
   - (Opcional) Añade autenticación y endpoints específicos del broker (cierre, modify, cancel).

## Endpoints útiles
- `GET /api/accounts` — listar cuentas
- `POST /api/accounts` — crear cuenta {name, tradelocker_account, api_key, is_master}
- `PATCH /api/accounts/{id}` — actualizar/activar/desactivar
- `GET /api/order-maps` — ver mapping master→followers
- `POST /api/master/event` — disparar evento del master (usa la UI)

## Notas
- Este scaffold guarda **master_order_id → follower_order_id** y estado básico.
- Si pones `DRY_RUN=false`, asegúrate que los followers tienen margen suficiente y símbolos idénticos.
- Para producción: agrega seguridad (auth), logs estructurados, reintentos, manejo de fills y cancelaciones.

¡Éxitos con H.R-traders!


## Nuevo (v0.2.0)
- **Replica order.modify, order.cancel y position.close** a todos los followers usando el mapeo `master_order_id → follower_order_id`.
- **Autenticación Bearer opcional**: establece `AUTH_TOKEN` y envía `Authorization: Bearer <AUTH_TOKEN>` en endpoints de escritura.
- **Notificaciones Telegram opcionales**: define `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` para recibir avisos de placed/modify/cancel/close.

### Variables de entorno
- `DRY_RUN=true|false`
- `TRADELOCKER_REST=https://...`
- `AUTH_TOKEN=tu_token_super_secreto`
- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_CHAT_ID=...`

### Ejemplos de llamadas (curl)
```bash
# order.create
curl -X POST http://localhost:8000/api/master/event \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer $AUTH_TOKEN" \
 -d '{"type":"order.create","payload":{"order_id":"M-1001","symbol":"XAUUSD","side":"buy","size":1,"type":"market"}}'

# order.modify (cambia precio de una limit o tamaño)
curl -X POST http://localhost:8000/api/master/event \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer $AUTH_TOKEN" \
 -d '{"type":"order.modify","payload":{"order_id":"M-1001","price":2410.5}}'

# order.cancel
curl -X POST http://localhost:8000/api/master/event \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer $AUTH_TOKEN" \
 -d '{"type":"order.cancel","payload":{"order_id":"M-1001"}}'

# position.close
curl -X POST http://localhost:8000/api/master/event \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer $AUTH_TOKEN" \
 -d '{"type":"position.close","payload":{"symbol":"XAUUSD"}}'
```



## Nuevo (v0.3.0)
- **Seguimiento de fills parciales** con la tabla `FillState` (master_filled, follower_filled, avg_price).
- Evento **`order.fill`**: envía `{order_id, size=<cumulative_filled>, price=<avg_price?>, extras: {is_final:true|false}}` para registrar/parcial/final.
- **Cierre parcial espejo**: evento `position.close_partial` con `{symbol, size}` envía órdenes `market reduce_only` a todos los followers.
- Reconciliación básica: si el master reporta `is_final` y algún follower quedó con remanente, el sistema intenta **cancelar** la orden seguidora para evitar sobrellenado posterior.
