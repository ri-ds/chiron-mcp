/// <reference types="cypress" />

describe("Criteria Set", () => {
  context("setting up auth state before tests", () => {
    beforeEach(() => {
      cy.intercept("/api/v2/performance_tests/query_tools/count", {
        count: "40000",
        cohort_def: [],
      }).as("getCount");
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "cohort_def",
      }).as("getCohortDef");
      cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
      cy.intercept("/api/v2/dataset/", { fixture: "datasets" }).as(
        "getDatasets"
      );
      cy.intercept("/api/v2/dataset/performance_tests", {
        fixture: "authDataset",
      }).as("getDataset");
      cy.intercept(
        "/api/v2/performance_tests/concept_categories/?cohort_type=cohort",
        {
          fixture: "concept_categories",
        }
      ).as("getConceptCategories");
      cy.intercept("/api/v2/performance_tests/concept_categories/1", {
        fixture: "concept_categories_cat1",
      }).as("conceptCat1");
    });
    it("Toggles criteria sets view", () => {
      cy.intercept("/api/v2/performance_tests/collections", {
        fixture: "criteriasets/collections.json",
      });
      cy.visit("/performance_tests/query");
      cy.contains("40,000");
      cy.contains("Query");
      cy.contains("performance tests");
      cy.contains("Add Criteria Set").click();
      cy.get("button").should("have.length", 30);
      cy.contains("Add Criteria Set").click();
      cy.get("button").should("have.length", 23);
    });
    it("Adds criteria set", () => {
      cy.intercept("/api/v2/performance_tests/collections", {
        fixture: "criteriasets/collections.json",
      });

      cy.visit("/performance_tests/query");
      cy.contains("40,000");
      cy.contains("Query");
      cy.contains("performance tests");
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "criteriasets/subjectcriteria.json",
      });
      cy.contains("Add Criteria Set").click();
      cy.get('[data-testid="AddIcon"]').last().click({ force: true });
      cy.contains("Subject Criteria");
    });
    it("Removes criteria set", () => {
      cy.intercept("/api/v2/performance_tests/collections", {
        fixture: "criteriasets/collections.json",
      });
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "criteriasets/subjectcriteria.json",
      });

      cy.visit("/performance_tests/query");
      cy.contains("40,000");
      cy.contains("Query");
      cy.contains("performance tests");
      cy.contains("Subject Criteria");
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "cohort_def",
      }).as("getCohortDef");
      cy.get('[data-testid="RemoveIcon"]').last().click();
      cy.contains("Subject Criteria").should("not.exist");
    });
    it.only("Does not reset query view on filter removal", () => {
      cy.intercept("/api/v2/performance_tests/collections", {
        fixture: "criteriasets/collections.json",
      });
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "criteriasets/subjectcriteria.json",
      });
      cy.intercept(
        "/api/v2/performance_tests/concepts/gender/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/genderconcept.json",
        }
      ).as("genderconcept");
      cy.intercept(
        "/api/v2/performance_tests/concepts/gender/cohort_def_callback/?concept_id=gender&entry_id=&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/gendercohort.json",
        }
      ).as("gendercohort");

      cy.visit("/performance_tests/query");
      cy.contains("Demographics").click();
      cy.get("button").contains("Gender").click();
      cy.get("div").contains("13426 entries for 13426 subjects");
      cy.get('[data-testid="RemoveIcon"]').last().click();
      cy.get("div").contains("13426 entries for 13426 subjects");
    });
  });
});
