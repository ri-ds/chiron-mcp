import { describe, test, expect } from "vitest";
import { screen, renderComponent } from "./utils";
import initialState from "../src/store/cohortSlice";
import Filters from "../src/components/Filters";
import DescribeFilters from "../src/components/Filters/DescribeFilters";
import userEvent from "@testing-library/user-event";
import { CRITERIA_SETS_MOCK } from "./cohortMocks";

describe("Filter functionality", function () {
  test("renders base filters component", () => {
    const cohortState = {
      ...initialState,
      cohortState: "done",
      showCriteriaSets: false,
      showDescribeFilters: true,
      extended_cohort_def: [],
      cohortPage: "query",
      count: 17396,
    };
    renderComponent(
      <Filters resultsDisplay={false} currentPage="query"></Filters>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    expect(screen.getByText("17,396")).toBeInTheDocument();
    //expect(screen.getByText("Criteria")).toBeInTheDocument();
    expect(screen.getByText("Criteria")).toBeInTheDocument();
    expect(screen.getByText("Add Criteria Set")).toBeInTheDocument();
  });

  test("toggles criteria set button", async function () {
    const cohortState = {
      ...initialState,
      cohortState: "done",
      showCriteriaSets: false,
      extended_cohort_def: [],
      count: 17396,
      cohortPage: "query",
      criteriaSets: CRITERIA_SETS_MOCK,
    };
    renderComponent(
      <Filters resultsDisplay={true} currentPage="query"></Filters>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    await userEvent.click(screen.getByText("Add Criteria Set"));
    expect(screen.getByText(CRITERIA_SETS_MOCK[0].name)).toBeInTheDocument();
    await userEvent.click(screen.getByText("Add Criteria Set"));
    expect(
      screen.queryByText(CRITERIA_SETS_MOCK[0].name)
    ).not.toBeInTheDocument();
  });

  test("Describe Filters dialogue works & closes", () => {
    const cohortState = {
      ...initialState,
      showDescribeFilters: true,
    };
    const testDescription = "test description";
    renderComponent(
      <DescribeFilters
        disabled={false}
        description={testDescription}
      ></DescribeFilters>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    userEvent.click(screen.getByTestId("CloseIcon"));
    expect(screen.getByText(testDescription)).not.toBeVisible;
    userEvent.click(screen.getByText("Describe Filters"));
    expect(screen.getByText(testDescription)).toBeVisible;
  });
});
