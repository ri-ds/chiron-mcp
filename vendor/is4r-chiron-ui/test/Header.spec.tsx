import { describe, test, expect } from "vitest";
import { renderComponent, screen } from "./utils";
import Header from "../src/components/Header";
import {
  AUTHENTICATED_USER_AUTH_STATE,
  UNAUTHENTICATED_AUTH_STATE,
  SECOND_TEST_USER_DATASET,
} from "./mocks";

describe("Header Component tests", () => {
  test("renders the default header unauthenticated", () => {
    renderComponent(<Header />, {
      preloadedState: {
        auth: UNAUTHENTICATED_AUTH_STATE,
      },
    });

    // title
    expect(screen.getByText("Chiron")).toBeInTheDocument();

    // main links
    expect(screen.queryByText("Home")).not.toBeInTheDocument();
    expect(screen.queryByText("Query")).not.toBeInTheDocument();
    expect(screen.queryByText("Results")).not.toBeInTheDocument();
    expect(screen.queryByText("Reports")).not.toBeInTheDocument();

    // right links
    expect(screen.getByText("Login")).toBeInTheDocument();
  });

  test("renders the default header with user logged in", () => {
    renderComponent(<Header />, {
      preloadedState: {
        auth: AUTHENTICATED_USER_AUTH_STATE,
      },
    });

    // title
    expect(screen.getByText("TEST Chiron")).toBeInTheDocument();

    // main links
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Query")).toBeInTheDocument();
    expect(screen.getByText("Results")).toBeInTheDocument();
    expect(screen.getByText("Reports")).toBeInTheDocument();

    // right links
    expect(screen.queryByText("Login")).not.toBeInTheDocument();
    expect(screen.getByText("Test User")).toBeInTheDocument();
  });

  test("renders with a custom title", () => {
    renderComponent(<Header />, {
      preloadedState: {
        auth: {
          ...AUTHENTICATED_USER_AUTH_STATE,
          dataset: SECOND_TEST_USER_DATASET,
        },
      },
    });

    expect(screen.getByText("Other App")).toBeInTheDocument();
  });
});
