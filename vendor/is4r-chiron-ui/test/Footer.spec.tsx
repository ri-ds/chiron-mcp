import { describe, test, expect } from "vitest";
import { renderComponent, screen } from "./utils";
import Footer from "../src/components/Footer";
import {
  AUTHENTICATED_USER_AUTH_STATE,
  UNAUTHENTICATED_AUTH_STATE,
} from "./mocks";

describe("Footer Component tests", () => {
  test("renders the default footer", async () => {
    renderComponent(<Footer />, {
      preloadedState: {
        auth: UNAUTHENTICATED_AUTH_STATE,
      },
    });

    const year = new Date().getFullYear();
    expect(screen.getByText(`© ${year}`)).toBeInTheDocument();
    expect(screen.getByText("Chiron v0.0.0")).toBeInTheDocument();
  });

  test("renders the default footer", async () => {
    renderComponent(<Footer />, {
      preloadedState: {
        auth: AUTHENTICATED_USER_AUTH_STATE,
      },
    });

    const year = new Date().getFullYear();
    expect(screen.getByText(`© ${year}`)).toBeInTheDocument();
    expect(screen.getByText("TEST Chiron v0.0.0")).toBeInTheDocument();
  });
});
