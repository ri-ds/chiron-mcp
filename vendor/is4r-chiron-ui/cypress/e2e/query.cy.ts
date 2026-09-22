/// <reference types="cypress" />

describe("Query shows", () => {
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
    it("Navigate to query", () => {
      cy.visit("/performance_tests/query");
      cy.contains("40,000");
      cy.contains("Query");
      cy.contains("performance tests");
    });
    it("Should show text filter, searches, applies to filter", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/first_name/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/firstnameconcept.json",
        }
      ).as("firstnameconcept");
      cy.intercept(
        "/api/v2/performance_tests/concepts/first_name/cohort_def_callback/?concept_id=first_name&entry_id=&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/firstnamecohort.json",
        }
      ).as("firstnamecohort");
      cy.visit("/performance_tests/query");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("First Name").click();
      cy.contains("Aaron");
      cy.contains("Alec");
      cy.intercept(
        "/api/v2/performance_tests/concepts/first_name/cohort_def_callback/?search=ab&page=1&prefilter_value=&show_all_data=true&records_per_page=3000",
        { fixture: "query/firstnamesearchpageresult.json" }
      ).as("searchResults");
      cy.get('input[type="search"').last().type("ab");
      cy.wait("@searchResults");
      cy.get("label").contains("Abigail").click();
      cy.get("label").last().contains("Abigail");
      cy.get('[data-id="sresults-selectall"]').click();
      cy.get("label").last().contains("Tabitha");
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "query/firstnameselectallfilter.json",
      });
      cy.get("button").contains("Apply new").click();
      cy.contains('First Name in "Abigail", "Elizabeth", "Gabriel",');
    });
    it("Paste text input should be interacted with, populate, validate, update, remove", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/first_name/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/firstnameconcept.json",
        }
      ).as("firstnameconcept");
      cy.intercept(
        "/api/v2/performance_tests/concepts/first_name/cohort_def_callback/?concept_id=first_name&entry_id=&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/firstnamecohort.json",
        }
      ).as("firstnamecohort");
      cy.visit("/performance_tests/query");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("First Name").click();
      cy.get("label").contains("Aaron").click();

      cy.get("textarea").type("\nInvalid!\n\n\nAlec\nLastBad");
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "query/firstnamemodalvalidateinput.json",
      });
      cy.get('[data-testid="ChevronRightIcon"]').first().click();
      cy.get("label").last().contains("Aaron");
      cy.get("label").last().prev().contains("Alec");
      cy.contains("Invalid!");
      cy.get("label").contains("Invalid!").should("not.exist");
      cy.get(".MuiAlert-message").contains("Remaining entries are invalid");
      cy.get("textarea").clear();
      cy.get('[data-testid="ChevronRightIcon"]').first().click();
      cy.get(".MuiAlert-message")
        .contains("Remaining entries are invalid")
        .should("be.not.visible", { setTimeout: 5000 });
      cy.get("label").contains("Aaron").click();
      cy.get("label").last().contains("Alec");
    });

    it("Should show category filter, add filtered concept", () => {
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
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("Gender").click();
      cy.get("div").contains("13426 entries for 13426 subjects").click();
      cy.get("div").contains("F");
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "/query/genderselectedcohort.json",
      });
      cy.intercept("/api/v2/performance_tests/query_tools/count/", {
        fixture: "/query/genderselectedcount.json",
      }).as("getCount");
      cy.get("button").contains("Apply new").click();
      cy.contains('Gender = "M"');
      cy.get("h6").contains("13,426");

      cy.get("button").contains("Update filter");
      cy.contains("Exclude Filter").click();
      cy.get("button").contains("Update filter");
      cy.intercept(
        "/api/v2/performance_tests/concepts/gender/?cohort_def_entry_id=56r5mnQfI5IS&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/genderexcludedcohort.json",
        }
      );
      cy.intercept("/api/v2/performance_tests/concepts/gender/cohort_def/", {
        fixture: "/query/genderexcludedconcept.json",
      }).as("gendercohort");
      cy.intercept("/api/v2/performance_tests/query_tools/count/", {
        fixture: "/query/genderexcludedcount.json",
      }).as("gendercohort");

      cy.get("button").contains("Update filter").click();
    });

    it("Should show date filter", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/birthdate/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/birthdateconcept.json",
        }
      ).as("birthdateconcept");
      cy.intercept(
        "/api/v2/performance_tests/concepts/birthdate/cohort_def_callback/?concept_id=birthdate&entry_id=&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/birthdatecohort.json",
        }
      ).as("birthdatecohort");
      cy.visit("/performance_tests/query");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("Birthdate").click();
      cy.get(".MuiChartsAxis-bottom").first().contains("1924");
    });
    it("Should show number filter", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/healthcare_expenses/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/healthcare_expensesconcept.json",
        }
      ).as("healthcare_expensesconcept");
      cy.intercept(
        "/api/v2/performance_tests/concepts/healthcare_expenses/cohort_def_callback/?concept_id=healthcare_expenses&entry_id=&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/healthcare_expensescohort.json",
        }
      ).as("healthcare_expensescohort");
      cy.visit("/performance_tests/query/");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("Healthcare Expenses").click();
      cy.get(".MuiChartsAxis-bottom").first().contains("0-1000");
    });
    it("Should show error on 404", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/healthcare_expenses/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/healthcare_expensesconcept.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/healthcare_expenses/cohort_def_callback/?concept_id=healthcare_expenses&entry_id=&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/data404.json",
          statusCode: 404,
        }
      );

      cy.visit("/performance_tests/query/");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("Healthcare Expenses").click();
      cy.contains("Not found");
    });
    it("Should display prefilter select for required concepts, add a filter, and load the filter", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/healthcare_expenses/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/prefilterrequirednumberconcept.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number/?cohort_def_entry_id=xMeR3VQAqsAc&include_cohort_def_options=true&prefilter_value=mg%2Fml&show_all_data=true",
        {
          fixture: "/query/prefilterrequirednumberprefilterconcept.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number_category/?page=1&search=&show_all_data=true&cohort_def=[]&records_per_page=1000&include_statistics=true",
        {
          fixture: "/query/prefilternumberselect.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number/cohort_def_callback/?concept_id=prefilter_number&entry_id=&prefilter_value=mg%2Fml&show_all_data=true",
        {
          fixture: "/query/prefilternumberresults.json",
        }
      );
      cy.intercept("/api/v2/performance_tests/cohort_def/", {
        fixture: "/query/prefilteraddfilter.json",
      });

      cy.visit("/performance_tests/query/");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("Healthcare Expenses").click();
      cy.contains("Please select a value to filter from");
      // click the dropdown
      cy.get("div.MuiFormControl-root input[type=text]").first().click();
      cy.get("div.MuiFormControl-root div[role=option]").first().click();
      // add a filter
      cy.get("label").contains("Max Value").siblings().first().type("100");
      cy.get("button").contains("Apply new filter").click();
      cy.contains("(mg/ml) Number <= 100.0");
      // load the filter
      cy.visit("/performance_tests/query/");
      cy.get("button[aria-label=filter-edit]").click();
      cy.get("label").contains("Max Value");
    });

    it("Should display prefilter select for optional concepts", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/healthcare_expenses/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/prefilteroptionalnumberconcept.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/DESCRIPTION_dokghoitxj/?page=1&search=&show_all_data=true&cohort_def=[]&records_per_page=1000&include_statistics=true",
        {
          fixture: "/query/prefilternumberselect.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/CODE_tguythbgor/cohort_def_callback/?concept_id=CODE_tguythbgor&entry_id=&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/prefilternumberresults.json",
        }
      );
      cy.visit("/performance_tests/query/");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("Healthcare Expenses").click();
      cy.contains("Optionally select a");
      cy.contains("Please select a value to filter from").should("not.exist");
    });
    it("Should display error if a prefilter has a nested prefilter specified", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/healthcare_expenses/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/prefilternestedconcept.json",
        }
      );

      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number/?page=1&search=&show_all_data=true&cohort_def=[]&records_per_page=1000&include_statistics=true",
        {
          fixture: "/query/prefiltererror.json",
        }
      );
      cy.visit("/performance_tests/query/");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("Healthcare Expenses").click();
      cy.get("div.MuiFormControl-root input[type=text]").first().click();
      cy.contains("Prefilter is configured incorrectly");
    });

    it("Should display a normal graph if the using the current filters toggle is checked", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/healthcare_expenses/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/prefilterrequirednumberconcept.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number_category/?page=1&search=&show_all_data=true&cohort_def=[]&records_per_page=1000&include_statistics=true",
        {
          fixture: "/query/prefilternumberselect.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=false",
        {
          fixture: "/query/prefilterrequirednumberprefilterconcept.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number/cohort_def_callback/?concept_id=prefilter_number&entry_id=&prefilter_value=mg%2Fml&show_all_data=true",
        {
          fixture: "/query/prefilternumberresults.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number/cohort_def_callback/?concept_id=prefilter_number&entry_id=&prefilter_value=mg%2Fml&show_all_data=false",
        {
          fixture: "/query/prefilternumberresults.json",
        }
      );

      cy.visit("/performance_tests/query/");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("Healthcare Expenses").click();
      cy.get('[data-testid="active-cohort-switch"]').click();
      cy.get("div.MuiFormControl-root input[type=text]").first().click();
      cy.get("div.MuiFormControl-root div[role=option]").first().click();
      cy.get("label").contains("Max Value");
    });
    it.only("Should allow for clearing the prefilter", () => {
      cy.intercept(
        "/api/v2/performance_tests/concepts/healthcare_expenses/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=true",
        {
          fixture: "/query/prefilterrequirednumberconcept.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number_category/?page=1&search=&show_all_data=true&cohort_def=[]&records_per_page=1000&include_statistics=true",
        {
          fixture: "/query/prefilternumberselect.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number/?cohort_def_entry_id=undefined&include_cohort_def_options=true&prefilter_value=&show_all_data=false",
        {
          fixture: "/query/prefilterrequirednumberprefilterconcept.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number/cohort_def_callback/?concept_id=prefilter_number&entry_id=&prefilter_value=mg%2Fml&show_all_data=true",
        {
          fixture: "/query/prefilternumberresults.json",
        }
      );
      cy.intercept(
        "/api/v2/performance_tests/concepts/prefilter_number/cohort_def_callback/?concept_id=prefilter_number&entry_id=&prefilter_value=mg%2Fml&show_all_data=false",
        {
          fixture: "/query/prefilternumberresults.json",
        }
      );

      cy.visit("/performance_tests/query/");
      cy.get("button").contains("Demographics").click();
      cy.get("button").contains("Healthcare Expenses").click();
      cy.get("div.MuiFormControl-root input[type=text]").first().click();
      cy.get("div.MuiFormControl-root div[role=option]").first().click();
      cy.get("label").contains("Max Value");
      cy.get('[data-testid="prefilter-select"] svg').first().click();
      cy.get("label").contains("Max Value").should("not.exist");
    });
  });
});
