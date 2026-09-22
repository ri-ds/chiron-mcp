/// <reference types="cypress" />

describe("Result Table", () => {
  beforeEach(() => {
    cy.intercept("/api/v2/auth/", { fixture: "auth" }).as("getAuth");
    cy.intercept("/api/v2/dataset/", { fixture: "datasets" }).as("getDatasets");
    cy.intercept("/api/v2/dataset/performance_tests", {
      fixture: "authDataset",
    }).as("getDataset");
    cy.intercept("/api/v2/performance_tests/cohort_def/", {
      fixture: "cohort_def",
    }).as("getCohortDef");

    cy.intercept(
      "/api/v2/performance_tests/concept_categories/?cohort_type=table",
      {
        fixture: "concept_categories",
      }
    ).as("getConceptCategories");

    cy.intercept("/api/v2/performance_tests/query_tools/count", {
      count: "40000",
      cohort_def: [],
    }).as("getCount");
  });
  it("Navigate to Default Results", () => {
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/default_table.json",
      }
    ).as("getTableDef");

    cy.visit("/performance_tests/results");
    cy.contains("Patient ID");
    cy.contains("record");
    cy.contains("subject");
    cy.contains("Edit Columns");
    cy.contains("00002692010");
  });
  it("adds columns", () => {
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/default_table.json",
      }
    ).as("getTableDef");
    cy.intercept("/api/concept_categories/?cohort_type=table", {
      fixture: "concept_categories",
    }).as("getConceptCategories");

    cy.visit("/performance_tests/results");

    cy.intercept("/api/v2/performance_tests/concept_categories/1", {
      fixture: "concept_categories_cat1",
    }).as("conceptCat1");
    cy.intercept("api/v2/performance_tests/table_def/", {
      fixture: "/results/one_column_tabledef.json",
    }).as("tableDefResp");

    cy.contains("Edit Columns");
    cy.get('[data-testid="ViewColumnIcon"]').first().click();
    cy.contains("Selected Columns");
    cy.contains("Patient ID");
    cy.contains("Demographics").click();
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/two_column_table.json",
      }
    ).as("getTableDef");

    cy.contains("First Name").click();

    cy.get('[data-rfd-droppable-id="aggregate-modal_ResultsCols"]')
      .children()
      .first()
      .contains("Patient ID");
    cy.get('[data-rfd-droppable-id="aggregate-modal_ResultsCols"]')
      .children()
      .last()
      .contains("First Name");

    cy.contains("Update").click();

    cy.get("tr").first().children().first().contains("Patient ID");
    cy.get("tr").first().children().last().contains("First Name");
    cy.get("tr").last().children().first().contains("00044567890");
    cy.get("tr").last().children().last().contains("Lucas");
  });

  it("removes columns", () => {
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/three_column_table.json",
      }
    ).as("getTableDef");
    cy.intercept("/api/concept_categories/?cohort_type=table", {
      fixture: "concept_categories",
    }).as("getConceptCategories");

    cy.visit("/performance_tests/results");

    cy.intercept("/api/v2/performance_tests/concept_categories/1", {
      fixture: "concept_categories_cat1",
    }).as("conceptCat1");
    cy.intercept("api/v2/performance_tests/table_def/", {
      fixture: "/results/three_column_table.json",
    }).as("tableDefResp");

    cy.contains("Edit Columns");
    cy.get('[data-testid="ViewColumnIcon"]').first().click();
    cy.contains("Selected Columns");
    cy.contains(".MuiDialog-container", "Patient ID");
    cy.contains("button", "Demographics");
    cy.contains("button", "Demographics").click();
    cy.contains("button", "First Name").click();
    cy.get('[data-rfd-droppable-id="aggregate-modal_ResultsCols"]')
      .children()
      .first()
      .contains("Patient ID");
    cy.get('[data-rfd-droppable-id="aggregate-modal_ResultsCols"]')
      .children()
      .next()
      .contains("First Name")
      .click();
    cy.get('[data-rfd-droppable-id="aggregate-modal_ResultsCols"]')
      .children()
      .last()
      .contains("Gender")
      .click();

    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/three_column_remove.json",
      }
    ).as("getTableDef");
    cy.get('[data-testid="RemoveIcon"]').last().click();
    cy.contains("Update").click();

    cy.get("tr").first().children().first().contains("Patient ID");
    cy.get("tr").first().children().last().contains("First Name");
    cy.get("tr").contains("Gender").should("not.exist");
    cy.get("tr").contains("00006252435");
    cy.get("tr").contains("Maureen");
  });

  it("removes columns from table click", () => {
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/three_column_table.json",
      }
    ).as("getTableDef");
    cy.intercept("/api/concept_categories/?cohort_type=table", {
      fixture: "concept_categories",
    }).as("getConceptCategories");

    cy.visit("/performance_tests/results");
    cy.get("tr")
      .first()
      .children()
      .last()
      .contains("First Name")
      .should("not.exist");

    cy.intercept("api/v2/performance_tests/table_def/", {
      fixture: "/results/three_column_remove.json",
    }).as("tableDefResp");
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/three_column_remove.json",
      }
    ).as("getTableDef");

    cy.get('[data-testid="RemoveIcon"]').last().click();

    cy.get("tr").first().children().first().contains("Patient ID");
    cy.get("tr").first().children().last().contains("First Name");
    cy.get("tr").contains("Gender").should("not.exist");
    cy.get("tr").contains("00006252435");
    cy.get("tr").contains("Maureen");
  });

  it("changes column sorting", () => {
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/default_table.json",
      }
    );
    cy.intercept("/api/concept_categories/?cohort_type=table", {
      fixture: "concept_categories",
    }).as("getConceptCategories");

    cy.visit("/performance_tests/results");
    cy.get("tr").contains("00002692010");

    cy.intercept("api/v2/performance_tests/table_def/", {
      fixture: "/results/default_sorted.json",
    });
    cy.contains("Patient ID");
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/default_sorted.json",
      }
    ).as("getTableDef");
    cy.get('[data-testid="ArrowDropUpIcon"]').first().click();

    cy.get("tr").first().children().first().contains("Patient ID");
    cy.get("tr").contains("First Name").should("not.exist");
    cy.get("tr").contains("99999730127");
    cy.get('[data-testid="ArrowDropUpIcon"]').should("not.exist");
    cy.get('[data-testid="ArrowDropDownIcon"]').should("exist");
  });

  it("updates column aggregate", () => {
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/default_table.json",
      }
    ).as("getTableDef");
    cy.intercept("/api/concept_categories/?cohort_type=table", {
      fixture: "concept_categories",
    }).as("getConceptCategories");

    cy.intercept("api/v2/performance_tests/table_def/", {
      fixture: "/results/default_table.json",
    }).as("tableDefResp");
    cy.visit("/performance_tests/results");
    cy.get("tr").contains("00002692010");

    cy.intercept(
      "/api/v2/performance_tests/concepts/patient_id/?include_table_def_options=true&table_def_entry_id=PpdFNbA73YkI",
      {
        fixture: "/results/aggregate_modal.json",
      }
    );
    cy.intercept("api/v2/performance_tests/table_def/", {
      fixture: "/results/default_aggregated.json",
    }).as("tableDefResp");

    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/default_aggregated.json",
      }
    ).as("getTableDef");
    cy.get('[data-testid="EditIcon"]').first().click();
    cy.get("#mui-component-select-aggregation_method").click();
    cy.contains("Count All").click();
    cy.contains("Save Changes").click();
    cy.get("tr").first().children().first().contains("Patient ID");
    cy.get("tr").contains("40000");
  });

  it("resets columns", () => {
    cy.intercept("/api/concept_categories/?cohort_type=table", {
      fixture: "concept_categories",
    }).as("getConceptCategories");

    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/three_column_remove.json",
      }
    ).as("getTableDef");

    cy.intercept("api/v2/performance_tests/table_def/", {
      fixture: "/results/default_table.json",
    }).as("tableDefResp");

    cy.visit("/performance_tests/results");

    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/default_table.json",
      }
    ).as("getTableDef");
    cy.contains("Reset Columns");
    cy.contains("Reset Columns").click();

    cy.get("tr").first().children().first().contains("Patient ID");
    cy.get("tr").contains("First Name").should("not.exist");
    cy.get("tr").contains("00002692010");
  });

  it("reorders columns", () => {
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/one_column_table.json",
      }
    ).as("getTableDef");
    cy.intercept(
      "/api/v2/performance_tests/concept_categories/?cohort_type=table",
      {
        fixture: "concept_categories",
      }
    ).as("getConceptCategories");

    cy.visit("/performance_tests/results");

    cy.intercept("api/v2/performance_tests/table_def/", {
      fixture: "/results/reorder_column_tabledef.json",
    }).as("tableDefResp");

    cy.contains("Edit Columns");
    cy.get("button").contains("Edit Columns", { timeout: 3000 }).click();

    cy.get('[data-rfd-droppable-id="aggregate-modal_ResultsCols"]')
      .children()
      .first()
      .contains("Patient ID");
    cy.get('[data-rfd-droppable-id="aggregate-modal_ResultsCols"]')
      .children()
      .last()
      .contains("First Name");
    cy.get('[data-rfd-draggable-id="kpDqAFcMbYEs"]').drag(
      '[data-rfd-droppable-id="aggregate-modal_ResultsCols"]',
      { timeout: 8000 }
    );
    cy.intercept(
      "/api/v2/performance_tests/query_tools/preview/?page=1&records_per_page=25",
      {
        fixture: "/results/reorder_column_table.json",
      }
    ).as("getTableDef");
    cy.get("button").contains("Update").click();

    cy.get("tr").first().children().last().contains("Patient ID");
    cy.get("tr").first().children().first().contains("First Name");
    cy.get("tr").next().children().last().contains("00060704707");
    cy.get("tr").next().children().first().contains("Shelly");
  });
});
