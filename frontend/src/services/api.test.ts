import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, getAccessToken, setAccessToken, UNAUTHORIZED_EVENT } from "./api";

function respond(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      statusText: "",
      json: async () => body,
      text: async () => (typeof body === "string" ? body : JSON.stringify(body)),
    })
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("throws ApiError with the parsed FastAPI detail", async () => {
    respond(400, { detail: "Missing features: Flow Duration" });
    const err = await api.predict({}).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(400);
    expect(err.message).toBe("Missing features: Flow Duration");
  });

  it("clears the token and broadcasts on 401", async () => {
    setAccessToken("abc");
    const listener = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);
    respond(401, { detail: "Token expired" });
    await api.incidents().catch(() => undefined);
    window.removeEventListener(UNAUTHORIZED_EVENT, listener);
    expect(getAccessToken()).toBeNull();
    expect(listener).toHaveBeenCalledOnce();
  });

  it("does not broadcast for failed logins", async () => {
    const listener = vi.fn();
    window.addEventListener(UNAUTHORIZED_EVENT, listener);
    respond(401, { detail: "Invalid credentials" });
    await api.authLogin("a", "b").catch(() => undefined);
    window.removeEventListener(UNAUTHORIZED_EVENT, listener);
    expect(listener).not.toHaveBeenCalled();
  });
});
