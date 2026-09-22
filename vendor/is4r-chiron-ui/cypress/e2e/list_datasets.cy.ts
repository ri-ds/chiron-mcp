/// <reference types="cypress" />

describe("List datasets", () => {
  context("setting up auth state before tests", () => {
    beforeEach(() => {
      cy.intercept("/api/cohort_def/", { fixture: "cohort_def" }).as(
        "getCohortDef"
      );
      cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
      cy.intercept("/api/v2/dataset", { fixture: "datasets" });
    });
    it("Navigate to home", () => {
      cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
      cy.intercept("/api/v2/dataset", { fixture: "datasets" });
      cy.visit("/");
      cy.contains("Select a Dataset");
      cy.contains("Chiron performance tests");
      cy.contains("Just the Demographics information");
    });
    it("Select a Dataset", () => {
      cy.visit("/");
      cy.intercept("/api/v2/dataset/demographics", {
        fixture: "demographicsDataset",
      }).as("getAuth");

      cy.get('[data-field="dataset-button"]').last().click();
      cy.contains("Active Dataset");
      cy.contains("Demographics");
    });
  });
});
