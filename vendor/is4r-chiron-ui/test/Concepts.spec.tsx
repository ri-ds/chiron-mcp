import { describe, test, expect, vi } from "vitest";
import { screen, renderComponent } from "./utils";
import Concepts from "../src/components/Concepts";
import { act } from "@testing-library/react";
import {
  CONCEPT_COHORT_MOCK_RSLT,
  CONCEPT_CATEGORY_MOCK_RSLT,
  CONCEPT_SEARCH_RSLT,
} from "./cohortMocks";
import userEvent from "@testing-library/user-event";

global.fetch = vi.fn();

function createFetchResponse(data) {
  return { json: () => new Promise((resolve) => resolve(data)) };
}

describe("Concepts functionality", function () {
  test("renders concepts component, hierarchy", async function () {
    fetch.mockResolvedValue(createFetchResponse(CONCEPT_COHORT_MOCK_RSLT));
    await act(async () => renderComponent(<Concepts></Concepts>));
    expect(screen.getAllByLabelText("Search Concepts..."));
    expect(screen.getAllByRole("button")[0]).toHaveTextContent(
      CONCEPT_COHORT_MOCK_RSLT.concepts[0].name
    );
    expect(screen.getAllByRole("button")[1]).toHaveTextContent(
      CONCEPT_COHORT_MOCK_RSLT.categories[0].name
    );
    vi.clearAllMocks();
    fetch.mockResolvedValue(createFetchResponse(CONCEPT_CATEGORY_MOCK_RSLT));
    await userEvent.click(screen.getAllByRole("button")[1]);
    expect(
      screen.getByText(CONCEPT_CATEGORY_MOCK_RSLT.concepts[0].name)
    ).toBeInTheDocument();
  });

  test("concepts search", async function () {
    fetch.mockResolvedValue(createFetchResponse(CONCEPT_COHORT_MOCK_RSLT));
    await act(async () => renderComponent(<Concepts></Concepts>));
    vi.clearAllMocks();
    fetch.mockResolvedValue(createFetchResponse(CONCEPT_SEARCH_RSLT));
    await userEvent.type(screen.getByLabelText("Search Concepts..."), "first");
    await userEvent.click(screen.getByTestId("SearchIcon"));
    expect(screen.getByText(/results for/i)).toBeInTheDocument();
    expect(screen.getByText("first name")).toBeInTheDocument();
  });
  afterEach(() => {
    vi.clearAllMocks();
  });
});
