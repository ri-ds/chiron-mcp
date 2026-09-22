import { describe, test, expect } from "vitest";
import { screen, renderComponent } from "./utils";
import initialState from "../src/store/cohortSlice";
import QueryConceptAddOrUpdateButton from "../src/components/QueryConceptAddOrUpdateButton";

describe("Query concept editing & saving button", function () {
  test("shows nothing when no query data", function () {
    renderComponent(
      <QueryConceptAddOrUpdateButton></QueryConceptAddOrUpdateButton>
    );
    expect(screen.queryByRole("button")).toBeNull();
  });
  test("shows add filter button when previous concept filter exists", function () {
    const cohortState = {
      ...initialState,
      queryConceptEditing: true,
      queryConceptData: true,
    };
    renderComponent(
      <QueryConceptAddOrUpdateButton></QueryConceptAddOrUpdateButton>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    expect(screen.queryByRole("button")).toHaveTextContent(/update/i);
  });
  test("shows edit filter button when no previous concept filter exists", function () {
    const cohortState = {
      ...initialState,
      queryConceptEditing: false,
      queryConceptData: true,
    };
    renderComponent(
      <QueryConceptAddOrUpdateButton></QueryConceptAddOrUpdateButton>,
      {
        preloadedState: {
          cohort: cohortState,
        },
      }
    );
    expect(screen.queryByRole("button")).toHaveTextContent(/apply new/i);
  });
});
