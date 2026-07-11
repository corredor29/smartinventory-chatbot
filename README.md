# SmartInventory Chatbot

## Ecosistema del Proyecto (Enlaces Directos)

Este proyecto es uno de los tres componentes principales del sistema **Smart Inventory**. Cada componente cumple una función específica y se integra con los demás:

- 🖥️ **Backend / API:** [SmartInventoryAPI](https://github.com/corredor29/SmartInventoryAPI)
- 🌐 **Frontend Web:** [SmartInventory Frontend](https://github.com/corredor29/smartinventory-frontend.git)
- 🤖 **Chatbot IA:** Este repositorio

## Descripción

**SmartInventory Chatbot** es el componente de inteligencia artificial del ecosistema Smart Inventory. Es un servicio Python basado en FastAPI que utiliza LangChain y LangGraph para proporcionar un asistente conversacional inteligente capaz de:

- Responder consultas sobre productos, ventas y facturas del inventario
- Procesar lenguaje natural para entender las intenciones del usuario
- Ejecutar acciones específicas mediante herramientas (tools) que interactúan con la API .NET
- Mantener el contexto de la conversación a través de sesiones en memoria
- Escalar conversaciones complejas a asesores humanos cuando es necesario

### Interacción con el Ecosistema

1. **Con la API .NET (SmartInventoryAPI):**
   - El chatbot actúa como cliente HTTP asíncrono que consume los endpoints de la API .NET
   - Utiliza herramientas especializadas para consultar productos, ventas, facturas y realizar operaciones de negocio
   - Autenticación mediante `DOTNET_SERVICE_API_KEY`

2. **Con el Frontend Web:**
   - El frontend envía mensajes del usuario a este chatbot a través del endpoint `/chat/message`
   - El chatbot procesa el mensaje utilizando el grafo de LangGraph y devuelve la respuesta
   - El frontend presenta las respuestas del chatbot al usuario final

## Tecnologías Utilizadas

- **Python 3.12** - Lenguaje principal
- **FastAPI 0.115.6** - Framework web para APIs
- **Uvicorn** - Servidor ASGI
- **LangChain 0.3.14** - Framework para aplicaciones LLM
- **LangGraph 0.2.62** - Orquestación de agentes y flujos conversacionales
- **OpenAI GPT-4o-mini** - Modelo de lenguaje principal
- **HTTPX 0.28.1** - Cliente HTTP asíncrono para comunicación con la API .NET
- **Pydantic 2.10.5** - Validación de datos
- **Redis 5.2.1** - (Opcional) Almacenamiento de sesiones
- **Loguru 0.7.3** - Logging estructurado
- **Pytest** - Framework de testing

## Requisitos Previos e Instalación

### Requisitos Previos

- Python 3.12 o superior
- pip (gestor de paquetes de Python)
- Acceso a la API .NET (SmartInventoryAPI) ejecutándose
- API Key de.OpenAI

### Instalación

1. **Clonar el repositorio:**
```bash
git clone https://github.com/corredor29/smartinventory-chatbot.git
cd smartinventory-chatbot
```

2. **Crear entorno virtual (recomendado):**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

3. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno:**
```bash
cp .env.example .env
```

Editar el archivo `.env` con los valores necesarios:
```env
# Entorno
APP_ENV=development
APP_NAME=SmartInventory-Chatbot
DEBUG=true
LOG_LEVEL=INFO

# Servidor
HOST=0.0.0.0
PORT=8000

# Conexión con la API .NET
DOTNET_API_BASE_URL=https://localhost:5001/api
DOTNET_API_TIMEOUT=30
DOTNET_SERVICE_API_KEY=tu_api_key_aqui
DOTNET_MAX_RETRIES=3
DOTNET_RETRY_BACKOFF_SECONDS=0.5

# LLM
OPENAI_API_KEY=tu_openai_api_key_aqui
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

# Sesión
SESSION_STORE=memory
SESSION_TTL_SECONDS=3600
SESSION_CLEANUP_INTERVAL_SECONDS=300

# Grafo
GRAPH_TIMEOUT_SECONDS=60

# CORS
ALLOWED_ORIGINS=https://localhost:5001
```

### Ejecución

**Modo desarrollo:**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Modo producción:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Con Docker:**
```bash
docker build -t smartinventory-chatbot .
docker run -p 8000:8000 --env-file .env smartinventory-chatbot
```

### Ejecutar Tests

```bash
pytest
```

## Estructura del Proyecto

```
smartinventory-chatbot/
├── app/
│   ├── agents/           # Agentes de LangChain y configuración del LLM
│   ├── api/              # Rutas de la API FastAPI
│   │   └── routes/
│   │       ├── chat.py   # Endpoint principal de chat
│   │       └── health.py # Endpoint de health check
│   ├── clients/          # Clientes HTTP para servicios externos
│   │   └── dotnet_client.py  # Cliente asíncrono para la API .NET
│   ├── core/             # Configuración y utilidades centrales
│   │   ├── config.py     # Configuración de la aplicación
│   │   ├── logging.py    # Configuración de logging
│   │   └── metrics.py    # Métricas y monitoreo
│   ├── graph/            # Grafo de LangGraph y nodos
│   │   ├── builder.py    # Construcción del grafo conversacional
│   │   ├── nodes.py      # Nodos del grafo
│   │   └── edges.py      # Transiciones y condiciones
│   ├── schemas/          # Modelos de datos Pydantic
│   │   └── chat.py       # Esquemas de request/response
│   ├── session/          # Gestión de sesiones
│   │   └── memory_store.py  # Almacenamiento en memoria de sesiones
│   └── main.py           # Punto de entrada de la aplicación
├── tests/                # Tests unitarios y de integración
│   ├── conftest.py       # Configuración de pytest
│   ├── test_chat_route.py
│   ├── test_dotnet_client.py
│   ├── test_edges.py
│   ├── test_escalation_tools.py
│   ├── test_graph_integration.py
│   ├── test_invoice_tools.py
│   ├── test_product_tools.py
│   └── test_sale_tools.py
├── .dockerignore         # Archivos ignorados por Docker
├── .env.example          # Plantilla de variables de entorno
├── .gitignore            # Archivos ignorados por Git
├── Dockerfile            # Configuración de Docker
├── pytest.ini            # Configuración de pytest
└── requirements.txt      # Dependencias de Python
```

## Endpoints Principales

- `GET /health` - Health check del servicio
- `POST /chat/message` - Envía un mensaje al chatbot y recibe la respuesta

## Características Clave

- **Gestión de Sesiones:** Mantiene el contexto de conversación en memoria con TTL configurable
- **Timeouts:** Protección contra timeouts en la ejecución del grafo y llamadas a la API
- **Escalado a Humanos:** Sistema para escalar conversaciones complejas a asesores humanos
- **Logging Estructurado:** Logging detallado con contextos por sesión
- **Métricas:** Sistema de métricas para monitoreo del rendimiento
- **Retry Logic:** Reintentos automáticos en llamadas a la API .NET
- **CORS Configurable:** Configuración flexible de CORS para múltiples orígenes
