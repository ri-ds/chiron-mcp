import { describe, test, expect } from "vitest";
import { screen, renderComponent } from "./utils";
import initialState from "../src/store/cohortSlice";
import DisplayConceptFilter from "../src/components/DisplayConceptFilter";
import {
  AGE_CONCEPT_DETAILEDDATA,
  CATEGORY_CONCEPT_DETAILEDDATA,
  DATE_CONCEPT_DETAILEDDATA,
  TEXT_CONCEPT_DETAILEDDATA,
} from "./cohortMocks";
import userEvent from "@testing-library/user-event";

describe("Concept Filter Displays (middle pane)", () => {
  test("Displays age concept", async () => {
    const cohortState = {
      ...initialState,
      queryConceptDetailedData: AGE_CONCEPT_DETAILEDDATA,
      transformationErrors: [],
      transformationWarnings: [],
    };
    renderComponent(
      <DisplayConceptFilter type={"age"}></DisplayConceptFilter>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    expect(screen.getByLabelText(/min year/i).getAttribute("placeholder")).toBe(
      AGE_CONCEPT_DETAILEDDATA.stats.min_year.toString()
    );
    expect(screen.getByLabelText(/max year/i).getAttribute("placeholder")).toBe(
      AGE_CONCEPT_DETAILEDDATA.stats.max_year.toString()
    );
  });

  test("Displays Category or Boolean filter", async () => {
    const cohortState = {
      ...initialState,
      queryConceptDetailedData: CATEGORY_CONCEPT_DETAILEDDATA,
      transformationErrors: [],
      transformationWarnings: [],
    };
    renderComponent(
      <DisplayConceptFilter type={"category"}></DisplayConceptFilter>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    expect(
      screen.getByText(CATEGORY_CONCEPT_DETAILEDDATA.values[0].category)
    ).toBeInTheDocument();
    expect(
      screen.getByText(CATEGORY_CONCEPT_DETAILEDDATA.values[1].category)
    ).toBeInTheDocument();
    expect(
      screen.getByText(CATEGORY_CONCEPT_DETAILEDDATA.values[2].category)
    ).toBeInTheDocument();
  });

  test("Displays Date filter", async () => {
    const cohortState = {
      ...initialState,
      queryConceptDetailedData: DATE_CONCEPT_DETAILEDDATA,
      transformationErrors: [],
      transformationWarnings: [],
    };
    renderComponent(
      <DisplayConceptFilter type={"date"}></DisplayConceptFilter>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    expect(screen.getByText(/filter by date range/i)).toBeInTheDocument();
    expect(
      screen.getByText(DATE_CONCEPT_DETAILEDDATA.stats.max)
    ).toBeInTheDocument();
    expect(
      screen.getByText(DATE_CONCEPT_DETAILEDDATA.stats.min)
    ).toBeInTheDocument();
  });
  test("Displays Text filter", async () => {
    const cohortState = {
      ...initialState,
      queryConceptValues: [],
      queryConceptDetailedData: TEXT_CONCEPT_DETAILEDDATA,
      transformationErrors: [],
      transformationWarnings: [],
    };
    renderComponent(
      <DisplayConceptFilter type={"text"}></DisplayConceptFilter>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    expect(screen.getByLabelText("Search values ...")).toBeInTheDocument();
    expect(
      screen.getByText(
        TEXT_CONCEPT_DETAILEDDATA.paginated_results[0].unique_values
      )
    );
    expect(
      screen.getByText(
        TEXT_CONCEPT_DETAILEDDATA.paginated_results[1].unique_values
      )
    );
    await userEvent.click(
      screen.getByText(
        TEXT_CONCEPT_DETAILEDDATA.paginated_results[1].unique_values
      )
    );
    await userEvent.click(screen.getByTestId("add-button"));
    expect(
      screen.getAllByText(
        TEXT_CONCEPT_DETAILEDDATA.paginated_results[1].unique_values
      )
    ).toHaveLength(2);
  });

  test("Unrecognized concept renders message", () => {
    const badType = "badtype";
    const cohortState = {
      ...initialState,
      queryConceptDetailedData: true,
    };
    renderComponent(
      <DisplayConceptFilter type={badType}></DisplayConceptFilter>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    expect(screen.getByRole("heading", { level: 5 })).toHaveTextContent(
      /could not load display/i
    );
  });
  test("No data in concept filter", () => {
    const cohortState = {
      ...initialState,
      queryConceptDetailedData: true,
    };
    const goodType = "age";
    renderComponent(
      <DisplayConceptFilter type={goodType}></DisplayConceptFilter>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    expect(screen.getByRole("heading", { level: 5 })).toHaveTextContent(
      /no data was found/i
    );
  });
});
