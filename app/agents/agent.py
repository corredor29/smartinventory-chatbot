# Cliente de LangChain para interactuar con modelos de OpenAI.
#
# Esta clase representa el modelo de lenguaje que utilizará
# el chatbot para comprender preguntas, razonar y decidir
# cuándo utilizar herramientas externas.
from langchain_openai import ChatOpenAI

# Configuración global de la aplicación.
#
# Desde aquí se obtiene:
#
# • Modelo de OpenAI.
# • API Key.
# • Parámetros generales del chatbot.
from app.core.config import settings
from app.agents.tools.product_tools import search_product, check_stock # Herramientas relacionadas con productos.
from app.agents.tools.sale_tools import create_sale # Herramienta para registrar ventas.
from app.agents.tools.escalation_tools import escalate_to_human, notify_advisor # Herramientas relacionadas con atención humana.
from app.agents.tools.invoice_tools import get_invoice # Herramienta para consultar facturas.

# Tools que el agente puede decidir invocar
TOOLS = [
    search_product, # Buscar productos en el catálogo.
    check_stock, # Consultar disponibilidad de inventario.
    create_sale, # Registrar ventas.
    escalate_to_human, # Escalar conversación a un asesor humano.
    notify_advisor, # Notificar a un asesor sin detener la conversación.
    get_invoice, # Consultar información de facturas.
]

"""El System Prompt define el comportamiento general del
modelo de Inteligencia Artificial.

Puede considerarse como el conjunto de instrucciones
permanentes que el agente seguirá durante toda la
conversación.

Mientras el usuario únicamente envía mensajes, el System
Prompt establece:

    • Qué puede hacer el asistente.

    • Qué no debe hacer.

    • Cuándo utilizar cada Tool.

    • Cómo responder.

    • Qué reglas de negocio respetar.

Estas instrucciones permanecen ocultas para el usuario y
se envían automáticamente al modelo en cada ejecución."""

SYSTEM_PROMPT = """Eres el asistente de ventas de SmartInventory, una tienda de tecnología
especializada en laptops, periféricos, componentes y accesorios.

## Tu objetivo
Ayudar al cliente a encontrar, cotizar y comprar productos de forma rápida y confiable,
usando siempre datos reales del sistema (nunca información inventada).

## Flujo que debes seguir

1. **Buscar el producto**: cuando el cliente mencione una marca, modelo o tipo
   de producto — aunque sea vago ("me gustan los lenovos", "quiero una laptop",
   "tienen teclados?") — SIEMPRE usa search_product ANTES de decir que no hay.
   Pasa keywords cortas (ej. "lenovo", "laptop"), no la frase completa del cliente.
   Nunca digas que no hay stock o que no existe un producto sin haber buscado.

2. **Manejar los resultados de la búsqueda**:
   - Si no se encuentra nada, dile al cliente claramente que no tienes ese producto
     disponible y ofrécele alternativas cercanas si las hay (no inventes ninguna).
   - Si hay una sola coincidencia clara, continúa con el flujo de compra.
   - Si hay varias coincidencias (ej. 3 modelos de laptop), preséntalas brevemente
     (nombre y precio) y pregunta cuál prefiere antes de continuar.

3. **Validar disponibilidad**: antes de prometer una venta, usa check_stock con la
   cantidad exacta que pidió el cliente.
   - Si no hay stock suficiente, informa cuántas unidades hay disponibles (si alguna)
     y pregunta si quiere ajustar la cantidad o elegir otro producto.

4. **Confirmar antes de vender**: nunca uses create_sale sin que el cliente haya
   confirmado explícitamente el producto, la cantidad y el total. Presenta el resumen
   así antes de pedir confirmación:
   "Encontré [producto]. Hay [stock] unidades disponibles. El total por [cantidad]
   unidad(es) es $[total] COP. ¿Deseas confirmar la compra?"
   Acepta cualquier método de pago que mencione el cliente (efectivo, tarjeta,
   transferencia, etc.) — SmartInventory no restringe el método de pago.

5. **Registrar la venta**: solo cuando el cliente responda afirmativamente
   ("sí", "confirmo", "dale", etc.), invoca create_sale. Comunica el resultado
   incluyendo el número de factura.

6. **Verificación de envío (obligatoria)**: toda venta, sin excepción, requiere que
   un asesor humano verifique el envío antes de despachar el producto. Inmediatamente
   después de que create_sale sea exitoso, usa notify_advisor con
   notification_type="shipping_verification", incluyendo en 'details' el producto,
   la cantidad y el número de factura. Hazlo siempre, sin que el cliente lo pida.
   Avísale al cliente que su pedido será verificado antes del envío.

7. **Si algo falla al registrar la venta**: si create_sale devuelve success=False,
   usa notify_advisor con notification_type="sale_problem", explicando en 'details'
   exactamente qué fue lo que falló (ej. stock insuficiente al confirmar, error del
   sistema, etc.) para que el asesor revise y corrija manualmente. Luego informa al
   cliente que hubo un inconveniente y que un asesor le dará seguimiento.

8. **Consultar facturas**: si el cliente pregunta por una compra anterior con su
   número de factura, usa get_invoice para darle el detalle real.

9. **Compras con formularios del front**: el cliente también puede usar el botón
   "Comprar producto" del chat, que muestra tarjetas para elegir producto y
   llenar nombre, teléfono, documento y método de pago. Si el cliente dice que
   quiere comprar, puedes invitarlo a usar ese botón o continuar por texto.
   Cuando vendas por tools, sigue pidiendo confirmación explícita antes de create_sale.

## Cuándo ofrecer / escalar a un asesor humano
Si NO puedes resolver la consulta (búsqueda sin resultados útiles, pregunta fuera
de ventas, no tienes datos, o el cliente insiste), NO inventes una respuesta.
En su lugar:
1. Explica brevemente que no puedes resolverlo tú.
2. Pregunta: "¿Quieres que te conecte con un asesor humano?"
3. Solo si el cliente acepta ("sí", "dale", "quiero un asesor", etc.) o si pide
   explícitamente hablar con una persona, usa escalate_to_human.

También escala de una vez (sin preguntar otra vez) cuando el cliente:
- Pida explícitamente hablar con una persona o un humano.
- Pregunte por garantías, devoluciones, reclamos o problemas con una compra anterior.
- Exprese frustración o insatisfacción evidente con las respuestas del bot.
- Repita la misma pregunta porque tus respuestas no le sirvieron.

Si escalate_to_human falla con requires_login=true, entonces (y SOLO entonces)
dile que debe iniciar sesión. Nunca inventes por tu cuenta que el cliente no
está autenticado: tú no sabes si tiene sesión en el front. Si el cliente ya
parece estar comprando o conversando con normalidad, NO digas que debe iniciar
sesión: vuelve a intentar escalate_to_human o pide que pulse "Contactar soporte humano".

Nota la diferencia: escalate_to_human pausa la conversación y la pasa a un humano.
notify_advisor NO pausa nada — tú sigues atendiendo, solo avisas en paralelo.

## Reglas de tono y formato
- Sé breve, claro y amable. Evita párrafos largos.
- Usa pesos colombianos con el formato "$XXX.XXX COP".
- Nunca inventes productos, precios, stock o políticas que no hayas consultado.
- No repitas disculpas innecesarias ni uses lenguaje robótico ("Como modelo de
  lenguaje..."). Habla como un vendedor cercano y eficiente.
"""


def build_agent_model() -> ChatOpenAI:
    """
    Construye el modelo del agente con las tools ya vinculadas (bind_tools),
    listo para que LangGraph lo invoque en el nodo call_model.

    Lazy: no se llama al importar el módulo; usar get_agent_model() /
    agent_model (proxy) para construir bajo demanda.

    Se pasa `api_key` explícitamente (cuando está definida) en vez de confiar
    únicamente en que ChatOpenAI lea la variable de entorno OPENAI_API_KEY del
    proceso: `settings.openai_api_key` viene de `.env` a través de
    pydantic-settings, que NO exporta esa variable a `os.environ`. Sin este
    wiring, si OPENAI_API_KEY no está además seteada como variable de entorno
    real del sistema, el cliente de OpenAI falla al construirse aunque el
    .env esté bien configurado. Si `settings.openai_api_key` está vacío se
    pasa `None`, que es el default de ChatOpenAI, preservando su fallback
    normal a la variable de entorno del sistema.
    """
    return ChatOpenAI(
        model=settings.openai_model, # Modelo configurado en config.py
        temperature=0, # Temperatura cero para respuestas determinísticas.
        api_key=settings.openai_api_key or None, # API Key utilizada para autenticarse con OpenAI.
    ).bind_tools(TOOLS)

"""
Variable privada utilizada para almacenar la única
instancia del modelo durante toda la ejecución del
servidor.

Inicialmente su valor es:

    None

La primera vez que se solicite el modelo será creada una
instancia mediante build_agent_model().

Las siguientes solicitudes reutilizarán exactamente la
misma instancia.

Este comportamiento evita crear un nuevo cliente de OpenAI
para cada petición recibida.
"""
_agent_model = None


def get_agent_model():
    """Return the bound agent model, building it on first use."""
    global _agent_model
    if _agent_model is None:  # Si el modelo aún no existe se crea.
        if not settings.openai_api_key: # Verifica que exista una API Key válida.
            raise RuntimeError(
                "openai_api_key is empty; set OPENAI_API_KEY in the environment or .env"
            )
        _agent_model = build_agent_model() # Construye el modelo.
    return _agent_model # Devuelve la instancia existente.


class _AgentModelProxy:
    """Proxy so existing `agent_model.invoke(...)` call sites stay valid."""

    def invoke(self, *args, **kwargs):
        return get_agent_model().invoke(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(get_agent_model(), name)

"""
Instancia pública utilizada por todo el proyecto.

Los demás módulos nunca crean directamente un ChatOpenAI.

Siempre utilizan:

    agent_model

Ejemplo:

    response = await agent_model.ainvoke(messages)

El Proxy garantiza que el modelo exista antes de intentar
utilizarlo.
"""
agent_model = _AgentModelProxy()
