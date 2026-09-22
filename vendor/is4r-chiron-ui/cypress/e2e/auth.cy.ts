/// <reference types="cypress" />

describe("Authentication", () => {
  context("Unauthenticated tests", () => {
    it("shows unauthenticated view", () => {
      cy.intercept("/api/v2/auth/", { fixture: "noauth" }).as("getAuth");
      cy.visit("/");
      cy.wait("@getAuth");
      cy.contains("Login");
      cy.contains("Query").should("not.exist");
      cy.contains("Results").should("not.exist");
      cy.contains("Reports").should("not.exist");
      cy.contains("Chiron");
    });
  });
  context("Authenticated tests", () => {
    it("shows authenticated view", () => {
      cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
      cy.intercept("/api/v2/dataset/performance_tests", {
        fixture: "authDataset",
      }).as("getDataset");
      cy.intercept("/api/v2/dataset/", { fixture: "datasets" }).as(
        "getDatasets"
      );
      cy.intercept("/api/v2/dataset", { fixture: "datasets" });
      cy.visit("/");
      cy.wait("@getAuth");
      cy.contains("Login").should("not.exist");
      cy.contains("Test User");
      cy.contains("Chiron");
      cy.contains("Select a Dataset");
      cy.contains("Chiron v0.0.0");
    });
  });
  context("Aggregate permissions on dataset limits header choices", () => {
    it("shows authenticated view", () => {
      cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
      cy.intercept("/api/v2/dataset/performance_tests", {
        fixture: "authAggDataset",
      }).as("getDataset");
      cy.intercept("/api/v2/dataset", { fixture: "datasets" });
      cy.visit("/");
      cy.wait("@getAuth");
      cy.contains("Login").should("not.exist");
      cy.contains("Test User");
      cy.contains("Chiron");
      cy.contains("Select a Dataset");
      cy.contains("Chiron v0.0.0");
      cy.get('[data-field="dataset-button"]').first().click();
      cy.contains("Results").should("not.exist");
      cy.contains("Reports").should("not.exist");
      cy.contains("Aggregate");
    });
  });
  context(
    "Can view workspace permissions false on dataset limits header choices",
    () => {
      it("shows authenticated view", () => {
        cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
        cy.intercept("/api/v2/dataset/performance_tests", {
          fixture: "authAggDataset",
        });
        cy.intercept("/api/v2/dataset", { fixture: "datasets" });
        cy.visit("/");
        cy.wait("@getAuth");
        cy.contains("Login").should("not.exist");
        cy.contains("Test User");
        cy.contains("Chiron");
        cy.contains("Select a Dataset");
        cy.contains("Chiron v0.0.0");
        cy.get('[data-field="dataset-button"]').first().click();
        cy.contains("Results").should("not.exist");
        cy.contains("Reports").should("not.exist");
        cy.contains("Aggregate");
      });

      it("shows no workspace permissions view", () => {
        cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
        cy.intercept("/api/v2/dataset/performance_tests", {
          fixture: "authNoWorkspaceDataset",
        });
        cy.intercept("/api/v2/dataset", { fixture: "datasets" });
        cy.visit("/");
        cy.wait("@getAuth");
        cy.contains("Login").should("not.exist");
        cy.contains("Test User");
        cy.contains("Chiron");
        cy.contains("Select a Dataset");
        cy.contains("Chiron v0.0.0");
        cy.get('[data-field="dataset-button"]').first().click();
        cy.contains("Results").should("not.exist");
        cy.contains("Reports");
        cy.contains("Aggregate").should("not.exist");
        cy.get('[data-testid="SearchIcon"]').should("not.exist");
      });
    }
  );
});
