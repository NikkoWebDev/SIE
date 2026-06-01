export { renderers } from '../../renderers.mjs';

const prerender = false;
const RESPONSES = {
  rendimiento: [
    "El rendimiento académico general se encuentra en ",
    "seguimiento continuo. El promedio institucional ",
    "es de 3.8 sobre 5.0, lo que indica un desempeño ",
    "aceptable dentro de la metodología ABP. ",
    "Se recomienda reforzar las áreas de Humanidades ",
    "y Emprendimiento para alcanzar el umbral ",
    "sobresaliente de 4.0."
  ],
  samantha: [
    "Samantha Rojas presenta un rendimiento ",
    "sobresaliente en Tecnología ABP (4.5) y ",
    "Matemáticas ABP (4.2). Sin embargo, ",
    "Humanidades ABP (3.2) se encuentra por ",
    "debajo del umbral mínimo de 3.5. ",
    "Se sugiere asignar tutoría adicional ",
    "en comprensión lectora y producción textual."
  ],
  alerta: [
    "Se han detectado métricas críticas en ",
    "el área de Humanidades ABP con 3.2. ",
    "El sistema ha generado una alerta ",
    "de rendimiento. Se recomienda ",
    "intervención inmediata del docente ",
    "tutor y comunicación con acudientes."
  ],
  default: [
    "Basado en los datos del sistema VYNTRA, ",
    "el estudiante consultado presenta ",
    "un perfil académico en seguimiento. ",
    "Para obtener un análisis detallado, ",
    "consulta el tablero de rendimiento ",
    "o proporciona el nombre completo ",
    "del estudiante."
  ]
};
function findResponse(input) {
  const lower = input.toLowerCase();
  if (lower.includes("rendimiento") || lower.includes("promedio")) return RESPONSES.rendimiento;
  if (lower.includes("samantha") || lower.includes("rojas")) return RESPONSES.samantha;
  if (lower.includes("alerta") || lower.includes("critico") || lower.includes("critic")) return RESPONSES.alerta;
  return RESPONSES.default;
}
const POST = async ({ request }) => {
  const { message } = await request.json();
  const tokens = findResponse(message || "");
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      for (const token of tokens) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ token })}

`));
        await new Promise((r) => setTimeout(r, 40 + Math.random() * 30));
      }
      controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      controller.close();
    }
  });
  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive"
    }
  });
};

const _page = /*#__PURE__*/Object.freeze(/*#__PURE__*/Object.defineProperty({
  __proto__: null,
  POST,
  prerender
}, Symbol.toStringTag, { value: 'Module' }));

const page = () => _page;

export { page };
