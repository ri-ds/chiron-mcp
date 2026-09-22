/// <reference types="cypress" />

describe("Aggregate", () => {
  context("setting up auth state before tests", () => {
    beforeEach(() => {
      cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
      cy.intercept("/api/v2/dataset/", { fixture: "datasets" }).as(
        "getDatasets"
      );
      cy.intercept("/api/v2/dataset/performance_tests", {
        fixture: "authDataset",
      }).as("getDataset");
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "cohort_def",
      }).as("getCohortDef");

      cy.intercept(
        "/api/v2/performance_tests/concept_categories/?cohort_type=analysis",
        {
          fixture: "concept_categories",
        }
      ).as("getConceptCategories");

      cy.intercept("/api/v2/performance_tests/query_tools/count", {
        count: "40000",
        cohort_def: [],
      }).as("getCount");
    });
    //need to update all these
    it.only("Navigate to Empty Aggregate", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/empty_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/empty_run_analysis.json",
      }).as("runAnalysis");

      cy.visit("/performance_tests/aggregate");
      cy.contains("Aggregate Data View");
      cy.contains("Add Columns");
      cy.contains("Add Rows");
    });

    it.only("Navigate to Non Empty Aggregate", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/nonempty_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/nonempty_run_analysis.json",
      }).as("runAnalysis");
      cy.visit("/performance_tests/aggregate");
      cy.contains("Aggregate Data View");
      cy.contains("Gender");
      cy.contains("F");
      cy.contains("13375");
    });

    it("Navigate to Empty Aggregate, Add column (implicitly tests row)", () => {
      cy.intercept(
        "/api/v2/performance_tests/analysis_def/",
        { times: 1 },
        {
          fixture: "/aggregate/empty_aggregate.json",
        }
      ).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/empty_run_analysis.json",
      }).as("runAnalysis");
      cy.intercept("/api/v2/performance_tests/concept_categories/1", {
        fixture: "concept_categories_cat1",
      }).as("conceptCat1");
      cy.visit("/performance_tests/aggregate");
      cy.contains("Aggregate Data View");
      cy.get("button").contains("Edit Columns").click();
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/nonempty_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/nonempty_run_analysis.json",
      }).as("runAnalysis");
      cy.contains("Demographics").click();
      cy.contains("Gender").click();
      cy.get('[data-rfd-droppable-id="aggregate-modal_Columns"]')
        .children()
        .contains("Gender");
      cy.contains("Update").click();
      cy.contains("Gender");
      cy.contains("F");
      cy.contains("13284");
    });

    it("Clear All button resets to empty Aggregate", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/nonempty_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/nonempty_run_analysis.json",
      }).as("runAnalysis");
      cy.visit("/performance_tests/aggregate");
      cy.contains("Gender").click();
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/empty_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/empty_run_analysis.json",
      }).as("runAnalysis");
      cy.contains("Clear All").click();
      cy.contains("Add Columns");
      cy.contains("Add Rows");
    });

    it("2 row 2 column Analysis Table Shows correctly", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/complex_run_analysis.json",
      }).as("runAnalysis");

      cy.visit("/performance_tests/aggregate");
      cy.get(".header-group").first().contains("Facility");
      cy.get(".header-group").contains("ER");
      cy.get(".header-group").contains("Birthdate");
      cy.get(".header-group").contains("Death Date");
      // cy.get('[data-field="MIkaIqexKZ7a"]').first().siblings().first().contains("Death Date")
      // cy.get('[data-field="MIkaIqexKZ7a"]').first().siblings().next().contains("Gender")
      cy.contains("Death Date");
      cy.contains("Gender");
    });

    it("should remove 1 column from table, by way of the remove icon in table", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/complex_run_analysis.json",
      }).as("runAnalysis");

      cy.visit("/performance_tests/aggregate");

      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/remove_column_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/remove_column_run_analysis.json",
      }).as("runAnalysis");
      cy.get('[data-testid="RemoveCircleIcon"]').first().click({ force: true });
      //cy.get('[data-field="TdRClkNLJ7LK"]').siblings().first().contains("Death Date")
      //cy.get('[data-field="TdRClkNLJ7LK"]').siblings().first().next().contains("Gender")
      cy.contains("Death Date");
      cy.contains("Gender");
      cy.contains("Facility").should("not.exist");
    });

    it("should reorder rows", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/complex_run_analysis.json",
      }).as("runAnalysis");

      cy.visit("/performance_tests/aggregate");

      cy.get("button").contains("Edit Rows").click();

      cy.get(".MuiListItem-root").first().contains("Birthdate");
      cy.get(".MuiListItem-root").contains("Death Date");
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/reorder_row_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/reorder_row_run_analysis.json",
      }).as("runAnalysis");

      cy.get('[data-rfd-draggable-id="lS9nOYA3ksa9"]').drag(
        '[data-rfd-droppable-id="aggregate-modal_Rows"]'
      );
      cy.get(".MuiListItem-root").last().contains("Death Date");
      cy.get(".MuiListItem-root").contains("Birthdate");

      cy.contains("Update").click();
      // cy.get('[data-field="rWoQW7pFsw0z"]').first().siblings().first().contains("Birthdate")
      // cy.get('[data-field="rWoQW7pFsw0z"]').first().siblings().next().contains("Gender")
      cy.contains("Birthdate");
      cy.contains("Gender");
    });

    it("Swap Rows and Columns button swaps displays", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/complex_run_analysis.json",
      }).as("runAnalysis");
      cy.visit("/performance_tests/aggregate");
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate_switch.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/complex_run_analysis_switch.json",
      }).as("runAnalysis");
      cy.get('[data-field="swap-cols-button"]').first().click();
      cy.get(".header-group").first().contains("Birthdate");
      cy.get(".header-group").contains("1920s");
      cy.get(".header-group").contains("Facility");
      cy.get(".header-group").contains("Death Date");
      //cy.get('[data-field="p94YUUvIj5QJ"]').first().siblings().first().contains("Gender")
      //cy.get('[data-field="p94YUUvIj5QJ"]').first().siblings().next().contains("Death Date")
      cy.contains("Death Date");
      cy.contains("Gender");
    });

    it("Download button", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/complex_run_analysis.json",
      }).as("runAnalysis");
      cy.intercept(
        "/api/v2/performance_tests/analysis_tools/export_csv/?use_active_cohort=true",
        {
          fixture: "/aggregate/download_csv.json",
        }
      );
      cy.visit("/performance_tests/aggregate");
      cy.get("button").contains("Download CSV").click();
      cy.readFile("cypress/downloads/aggregate_export.csv");
    });

    it("Should correctly parse concepts with parentheses characters in their name", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/special_char_run_analysis.json",
      }).as("runAnalysis");
      cy.visit("/performance_tests/aggregate");
      cy.contains("AL Deficiency (Argininosuccinic Aciduria, ASA)");
    });

    it("Should display info alert instead of constantly loading when returned table data is {}", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/empty_dataset_run_analysis.json",
      }).as("runAnalysis");
      cy.visit("/performance_tests/aggregate");
      cy.contains("Aggregate data empty for selected concepts");
    });

    it("Internal single quotes don't break", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/special_char_run_analysis2.json",
      }).as("runAnalysis");
      cy.visit("/performance_tests/aggregate");
      cy.contains("ACT");
    });
    it("Internal single quotes don't break when grouped with boolean", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/special_char_run_analysis3.json",
      }).as("runAnalysis");
      cy.visit("/performance_tests/aggregate");
      cy.contains("AL Deficiency (Argininosuccinic Aciduria, ASA)");
    });
    it("Internal single quotes don't break when grouped with boolean two", () => {
      cy.intercept("/api/v2/performance_tests/analysis_def/", {
        fixture: "/aggregate/complex_aggregate.json",
      }).as("getAggregateDef");
      cy.intercept("/api/v2/performance_tests/analysis_tools/run_analysis", {
        fixture: "/aggregate/special_char_run_analysis4.json",
      }).as("runAnalysis");
      cy.visit("/performance_tests/aggregate");
      cy.contains("AL Deficiency (Argininosuccinic Aciduria, ASA)");
    });
  });
});
