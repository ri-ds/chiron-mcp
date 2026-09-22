// <reference types="cypress" />

describe("Reports shows", () => {
  context("setting up auth state before tests", () => {
    beforeEach(() => {
      cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
      cy.intercept("/api/v2/dataset/", { fixture: "datasets" }).as(
        "getDatasets"
      );
      cy.intercept("/api/v2/dataset/performance_tests", {
        fixture: "authDataset",
      }).as("getDataset");
      cy.intercept("/api/v2/performance_tests/reports/viewable_reports/", {
        fixture: "reports/viewable_reports.json",
      }).as("viewableReports");
      cy.intercept("/api/v2/performance_tests/reports/?project_id=&state=", {
        fixture: "reports/reports.json",
      }).as("reports");
    });
    it("Navigate to reports page", () => {
      cy.visit("/performance_tests/reports");
      cy.contains("Reports");
      cy.contains("All Reports");
      cy.contains(
        "5 related subcollections plus 1 unrelated subcollection, all aggregated"
      );
    });
    it("Should show error when api returns with 500 and html page", () => {
      cy.intercept(
        "/api/v2/performance_tests/reports/41/edit_form/?output_type=json",
        {
          body: '<!DOCTYPE html><html lang="en"></html>',
          statusCode: 500,
        }
      ).as("errorModal");
      cy.visit("/performance_tests/reports");

      cy.get('[data-testid="EditIcon"]').first().click();
      cy.contains("Report failed to load");
    });
    it("Should show edit modal with empty project_id", () => {
      cy.intercept(
        "/api/v2/performance_tests/reports/41/edit_form/?output_type=json",
        {
          fixture: "reports/edit_form_empty_project.json",
        }
      ).as("editModalEmpty");
      cy.visit("/performance_tests/reports");

      cy.get('[data-testid="EditIcon"]').first().click();
      cy.contains("Project");
    });
    it("Should show edit modal", () => {
      cy.intercept(
        "/api/v2/performance_tests/reports/41/edit_form/?output_type=json",
        {
          fixture: "reports/edit_form.json",
        }
      ).as("editModal");
      cy.visit("/performance_tests/reports");

      cy.get('[data-testid="EditIcon"]').first().click();
      cy.contains(";");
    });
  });
});
