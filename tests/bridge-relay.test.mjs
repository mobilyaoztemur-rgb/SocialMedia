import test from "node:test";
import assert from "node:assert/strict";
import { relay } from "../scripts/cloudflare/bridge-relay.mjs";

const origin = "https://woodmood-test.example";
const headers = { Authorization: "Bearer synthetic-test-value-only" };

test("unauthenticated and cross-origin callers never reach the bridge", async () => {
  const send = () => assert.fail("unexpected upstream call");
  assert.equal((await relay(new Request(origin + "/v1/health"), send)).status, 401);
  assert.equal((await relay(new Request(origin + "/v1/health", {
    headers: { ...headers, Origin: "https://unrelated.example" },
  }), send)).status, 403);
});

test("callers cannot choose arbitrary paths, queries, schemes or methods", async () => {
  const send = () => assert.fail("unexpected upstream call");
  for (const path of ["/", "/v1/health?url=https://other.example", "/v1/cookies", "/v1/pages/invalid/snapshot"]) {
    assert.equal((await relay(new Request(origin + path, { headers }), send)).status, 404);
  }
  assert.equal((await relay(new Request("http://woodmood-test.example/v1/health", { headers }), send)).status, 400);
  assert.equal((await relay(new Request(origin + "/v1/health", { headers, method: "DELETE" }), send)).status, 405);
});

test("mutation body and idempotency key pass intact only to the fixed origin", async () => {
  const body = JSON.stringify({ url: "https://www.facebook.com/mobilyawoodmood" });
  const result = await relay(new Request(origin + "/v1/pages", {
    method: "POST", body,
    headers: { ...headers, "Content-Type": "application/json", "Idempotency-Key": "test-operation-123", Cookie: "private=unused" },
  }), async (url, options) => {
    assert.equal(url, "https://improve-hayes-everything-rehabilitation.trycloudflare.com/v1/pages");
    assert.equal(options.headers.get("Authorization"), headers.Authorization);
    assert.equal(options.headers.get("Idempotency-Key"), "test-operation-123");
    assert.equal(options.headers.has("Cookie"), false);
    assert.equal(await options.body.text(), body);
    assert.equal(options.redirect, "manual");
    return Response.json({ ok: true }, { headers: { "Set-Cookie": "not-forwarded=1" } });
  });
  assert.equal(result.headers.get("Cache-Control"), "no-store");
  assert.equal(result.headers.has("Set-Cookie"), false);
  assert.deepEqual(await result.json(), { ok: true });
});

test("redirects and failures do not leak credentials or follow another host", async () => {
  const request = () => new Request(origin + "/v1/health", { headers });
  const redirected = await relay(request(), async () => new Response(null, {
    status: 302, headers: { Location: "https://other.example" },
  }));
  assert.equal(redirected.status, 502);
  assert.equal(redirected.headers.has("Location"), false);
  const failed = await relay(request(), async () => { throw new Error(headers.Authorization); });
  assert.equal(failed.status, 502);
  assert.equal((await failed.text()).includes(headers.Authorization), false);
});

test("streamed oversized media never reaches the bridge", async () => {
  const request = new Request(origin + "/v1/media", {
    method: "POST", headers, body: new Uint8Array(25_000_001),
  });
  assert.equal((await relay(request, () => assert.fail("unexpected upstream call"))).status, 413);
});

test("binary screenshots and origin auth/pause statuses are preserved", async () => {
  for (const status of [401, 423]) {
    const result = await relay(new Request(origin + "/v1/health", { headers }),
      async () => Response.json({ detail: "Origin response" }, { status }));
    assert.equal(result.status, status);
  }
  const bytes = new Uint8Array([137, 80, 78, 71]);
  const response = await relay(new Request(origin + "/v1/pages/0123456789abcdef0123456789abcdef/screenshot", { headers }),
    async () => new Response(bytes, { headers: { "Content-Type": "image/png" } }));
  assert.equal(response.headers.get("Content-Type"), "image/png");
  assert.deepEqual(new Uint8Array(await response.arrayBuffer()), bytes);
});
