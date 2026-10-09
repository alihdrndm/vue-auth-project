import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia, type Pinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter, type Router } from "vue-router";

import { resetCsrfToken } from "../api/client";
import {
  json,
  mockFetch,
  problem,
  sessionBody,
  setCsrfCookie,
} from "../testing/http";
import SignInView from "./SignInView.vue";

let pinia: Pinia;
let router: Router;
const Stub = { template: "<p>stub</p>" };

beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  resetCsrfToken();
  setCsrfCookie("token");
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "home", component: Stub },
      { path: "/sign-in", name: "sign-in", component: SignInView },
      { path: "/app/:rest(.*)*", name: "app", component: Stub },
    ],
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function mountAt(path = "/sign-in") {
  await router.push(path);
  await router.isReady();
  return mount(SignInView, { global: { plugins: [pinia, router] } });
}

async function fillAndSubmit(
  wrapper: Awaited<ReturnType<typeof mountAt>>,
  email: string,
  password: string,
) {
  await wrapper.get("#sign-in-email").setValue(email);
  await wrapper.get("#sign-in-password").setValue(password);
  await wrapper.get("form").trigger("submit");
  await flushPromises();
}

describe("SignInView", () => {
  it("has labelled fields and the sandbox link", async () => {
    mockFetch(() => json(200, sessionBody()));
    const wrapper = await mountAt();

    expect(wrapper.get('label[for="sign-in-email"]').text()).toBe("Email");
    expect(wrapper.get('label[for="sign-in-password"]').text()).toBe(
      "Password",
    );
    const link = wrapper.get(".sandbox-link");
    expect(link.text()).toBe("Open the sandbox instead");
    expect(link.attributes("href")).toBe("/");
  });

  it("asks for missing fields without calling the API", async () => {
    const calls = mockFetch(() => json(200, sessionBody()));
    const wrapper = await mountAt();

    await wrapper.get("form").trigger("submit");

    expect(wrapper.text()).toContain("Enter your email address.");
    expect(wrapper.text()).toContain("Enter your password.");
    expect(wrapper.get("#sign-in-email").attributes("aria-invalid")).toBe(
      "true",
    );
    expect(calls).toHaveLength(0);
  });

  it("signs in, shows the loading state and opens the inbox", async () => {
    let release: (response: Response) => void = () => undefined;
    const calls = mockFetch(
      () =>
        new Promise<Response>((resolve) => {
          release = resolve;
        }),
    );
    const wrapper = await mountAt();

    await fillAndSubmit(wrapper, " anna@example.com ", "secret");

    const submit = wrapper.get('button[type="submit"]');
    expect(submit.text()).toBe("Signing in…");
    expect(submit.attributes("disabled")).toBeDefined();

    release(json(200, sessionBody()));
    await flushPromises();

    expect(JSON.parse(calls[0]?.body ?? "{}")).toEqual({
      email: "anna@example.com",
      password: "secret",
    });
    expect(router.currentRoute.value.path).toBe("/app/inbox");
  });

  it("returns to the requested app page", async () => {
    mockFetch(() => json(200, sessionBody()));
    const wrapper = await mountAt("/sign-in?redirect=/app/approvals");

    await fillAndSubmit(wrapper, "anna@example.com", "secret");

    expect(router.currentRoute.value.path).toBe("/app/approvals");
  });

  it("ignores redirects that leave the app", async () => {
    mockFetch(() => json(200, sessionBody()));
    const wrapper = await mountAt("/sign-in?redirect=//evil.example/app/");

    await fillAndSubmit(wrapper, "anna@example.com", "secret");

    expect(router.currentRoute.value.path).toBe("/app/inbox");
  });

  it("shows INVALID_CREDENTIALS inline in a live region", async () => {
    mockFetch(() =>
      problem(
        400,
        "INVALID_CREDENTIALS",
        "The email address or password is not correct.",
      ),
    );
    const wrapper = await mountAt();

    await fillAndSubmit(wrapper, "anna@example.com", "wrong");

    const alert = wrapper.get(".form-error");
    expect(alert.attributes("role")).toBe("alert");
    expect(alert.text()).toBe("The email address or password is not correct.");
    expect(router.currentRoute.value.path).toBe("/sign-in");
    expect(wrapper.get('button[type="submit"]').text()).toBe("Sign in");
  });

  it("puts validation problems next to their fields", async () => {
    mockFetch(() =>
      problem(422, "VALIDATION_FAILED", "One or more fields are invalid.", {
        errors: [
          {
            path: "email",
            code: "invalid",
            message: "Enter a valid email address.",
          },
        ],
      }),
    );
    const wrapper = await mountAt();

    await fillAndSubmit(wrapper, "anna", "secret");

    expect(wrapper.get("#sign-in-email-error").text()).toBe(
      "Enter a valid email address.",
    );
    expect(wrapper.get("#sign-in-email").attributes("aria-describedby")).toBe(
      "sign-in-email-error",
    );
  });

  it("shows and hides the password", async () => {
    mockFetch(() => json(200, sessionBody()));
    const wrapper = await mountAt();

    await wrapper.get('button[aria-label="Show password"]').trigger("click");

    expect(wrapper.get("#sign-in-password").attributes("type")).toBe("text");
    expect(
      wrapper
        .get('button[aria-label="Hide password"]')
        .attributes("aria-pressed"),
    ).toBe("true");
  });
});
