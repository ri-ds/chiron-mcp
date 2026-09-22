/// <reference types="cypress" />

// Tests navigation between components after specific changes have occurred elsewhere

describe("Reset Events", () => {
  beforeEach(() => {
    cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
    cy.intercept("/api/v2/dataset/", { fixture: "datasets" }).as("getDatasets");
    cy.intercept("/api/v2/dataset/performance_tests", {
      fixture: "authDataset",
    }).as("getDataset");

    cy.intercept("/api/v2/performance_tests/query_tools/count", {
      count: "40000",
      cohort_def: [],
    }).as("getCount");
  });

  it.skip("Shows default query page rather than skeleton after criteria selected outside of filter context", () => {
    cy.intercept("/api/v2/performance_tests/cohort_def/", {
      fixture: "cohort_def",
    }).as("getCohortDef");

    cy.intercept(
      "/api/v2/performance_tests/concept_categories/?cohort_type=analysis",
      {
        fixture: "concept_categories",
      }
    ).as("getConceptCategories");
    cy.intercept(
      "/api/v2/performance_tests/analysis_def/",
      { times: 1 },
      {
        fixture: "/aggregate/empty_aggregate.json",
      }
    ).as("getAggregateDef");
    cy.intercept(
      "/api/v2/performance_tests/concept_categories/?cohort_type=cohort",
      {
        fixture: "concept_categories",
      }
    ).as("getConceptCategories");
    cy.intercept("/api/v2/performance_tests/concept_categories/1", {
      fixture: "concept_categories_cat1",
    }).as("conceptCat1");
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
    cy.contains("Query").click();
    cy.contains("Quick Start Guide");
  });
});
