import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { ErrorState } from "./ErrorState";
import { ApiError } from "../../services/api";
import { describeError } from "../../lib/errors";

describe("describeError / ErrorState", () => {
  it("uses the FastAPI detail string from an ApiError", () => {
    const err = new ApiError({ status: 404, message: "Incident not found", detail: "Incident not found", path: "/api/incidents/x" });
    const info = describeError(err);
    expect(info.title).toBe("Not found");
    expect(info.message).toBe("Incident not found");
    expect(info.status).toBe(404);
  });

  it("lists validation errors from a 422 detail array", () => {
    const err = new ApiError({
      status: 422,
      message: "x",
      path: "/api/predict",
      detail: [
        { loc: ["body", "features"], msg: "field required", type: "missing" },
        { loc: ["body", "persist"], msg: "value is not a valid boolean", type: "bool" },
      ],
    });
    render(<ErrorState error={err} />);
    expect(screen.getByRole("alert").textContent).toContain("Invalid input");
    expect(screen.getByText("features: field required")).toBeTruthy();
    expect(screen.getByText("persist: value is not a valid boolean")).toBeTruthy();
    expect(screen.getByText("HTTP 422")).toBeTruthy();
  });

  it('parses a raw `{"detail": ...}` JSON body thrown as an Error message', () => {
    const info = describeError(new Error('{"detail":"Model artifacts missing"}'));
    expect(info.message).toBe("Model artifacts missing");
  });

  it("reads nested {detail: {message}} objects", () => {
    const err = new ApiError({ status: 403, message: "x", path: "/api/r", detail: { code: "FORBIDDEN", message: "Role lacks approve_response" } });
    expect(describeError(err).message).toBe("Role lacks approve_response");
    expect(describeError(err).title).toBe("Permission denied");
  });

  it("recognises network failures as offline", () => {
    const info = describeError(new TypeError("Failed to fetch"));
    expect(info.offline).toBe(true);
    expect(info.title).toMatch(/can't reach/i);
  });

  it("renders a retry button that calls onRetry", () => {
    const onRetry = vi.fn();
    render(<ErrorState error="boom" onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
