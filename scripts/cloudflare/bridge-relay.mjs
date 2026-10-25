// Cloudflare Worker module. No passwords/tokens belong in this file.
// This is the only destination; callers cannot choose another upstream.
const UPSTREAM = "https://improve-hayes-everything-rehabilitation.trycloudflare.com";
const MAX_BYTES = 25_000_000;
const ROUTE = /^\/v1\/(?:health|pages|media|operations\/[a-zA-Z0-9_-]{8,100}|pages\/[a-f0-9]{32}(?:\/(?:snapshot|screenshot|navigate|actions))?)$/;

function error(status, detail) {
  return Response.json({ detail }, {
    status,
    headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
  });
}

export async function relay(request, send = fetch) {
  const url = new URL(request.url);
  if (url.protocol !== "https:") return error(400, "HTTPS required");
  if (request.headers.has("Origin")) return error(403, "Browser-origin requests are disabled");
  if (!ROUTE.test(url.pathname) || url.search) return error(404, "Unknown bridge path");
  if (!["GET", "POST"].includes(request.method)) return error(405, "Method not allowed");
  const authorization = request.headers.get("Authorization");
  if (!/^Bearer \S+$/.test(authorization || "")) return error(401, "Authentication required");

  const headers = new Headers({ Authorization: authorization });
  for (const name of ["Content-Type", "Idempotency-Key", "Accept"]) {
    if (request.headers.has(name)) headers.set(name, request.headers.get(name));
  }
  let body;
  if (request.method === "POST") {
    const declared = request.headers.get("Content-Length");
    if (declared && (!/^\d+$/.test(declared) || Number(declared) > MAX_BYTES)) {
      return error(413, "Request exceeds size limit");
    }
    // Enforce the limit for streamed/chunked requests too.
    const reader = request.body?.getReader();
    const chunks = [];
    let size = 0;
    if (reader) {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          size += value.byteLength;
          if (size > MAX_BYTES) {
            await reader.cancel();
            return error(413, "Request exceeds size limit");
          }
          chunks.push(value);
        }
      } catch {
        return error(400, "Request body could not be read");
      }
    }
    body = new Blob(chunks);
  }
  try {
    const upstream = await send(UPSTREAM + url.pathname, {
      method: request.method, headers, body, redirect: "manual",
    });
    if (upstream.status >= 300 && upstream.status < 400) {
      await upstream.body?.cancel();
      return error(502, "Bridge redirected the request");
    }
    const responseHeaders = new Headers({
      "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    });
    for (const name of ["Content-Type", "WWW-Authenticate"]) {
      if (upstream.headers.has(name)) responseHeaders.set(name, upstream.headers.get(name));
    }
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return error(502, "Bridge connection failed");
  }
}

export default { fetch: request => relay(request) };
