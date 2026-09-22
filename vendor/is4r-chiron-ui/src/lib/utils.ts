import { FC } from "react";
import { CriteriaSet, NumberConceptDetailedData } from "../store/cohortSlice";
import CategoryOrBoolean from "../components/DisplayConceptFilter/CategoryOrBoolean";
import Number from "../components/DisplayConceptFilter/Number";
import Ontology from "../components/DisplayConceptFilter/Ontology";
import Text from "../components/DisplayConceptFilter/Text";
import DateDisplay from "../components/DisplayConceptFilter/Date";
import AgeDisplay from "../components/DisplayConceptFilter/Age";
import config from "../config";
import { darken, lighten } from "@mui/material/styles";
import { grey } from "@mui/material/colors";

export function colorStep(step: number) {
  if (config.table.conceptHeaderShade == "dark") {
    // lighten colors
    return lighten(config.table.conceptHeaderColor, step * 0.3);
  }
  // darken colors
  return darken(config.table.conceptHeaderColor, step * 0.25);
}

export function textColor(step: number) {
  if (config.table.conceptHeaderShade == "dark") {
    return step < 2 ? grey[50] : grey[900];
  }
  // darken colors
  return step < 2 ? grey[900] : grey[50];
}

export function asyncResponseWithWait(
  data: any,
  wait: number | undefined = undefined
) {
  if (wait === undefined) {
    wait = 1000 + Math.random() * 2000;
  }

  return new Promise((resolve) => setTimeout(() => resolve(data), wait));
}

/**
 * Simple object check.
 * @param item
 * @returns {boolean}
 */
export function isObject(item: any) {
  return item && typeof item === "object" && !Array.isArray(item);
}

/**
 * Deep merge two objects.
 * @param target
 * @param ...sources
 */
export function deepMerge(target: any, ...sources: any): any {
  if (!sources.length) return target;
  const source = sources.shift();

  if (isObject(target) && isObject(source)) {
    for (const key in source) {
      if (isObject(source[key])) {
        if (!target[key]) Object.assign(target, { [key]: {} });
        deepMerge(target[key], source[key]);
      } else {
        Object.assign(target, { [key]: source[key] });
      }
    }
  }

  return deepMerge(target, ...sources);
}

/**
 * Convers a date string MM/DD/YYYY to YYYY-MM-DD
 *
 * @param dateString string value of the date
 * @returns the formated string value of the date
 */
export function convertDateFormatForTextField(dateString: string) {
  if (!dateString || dateString.indexOf("/") === -1) {
    return dateString;
  }

  const dateParts = dateString.split("/");

  return `${dateParts[2]}-${dateParts[0]}-${dateParts[1]}`;
}

export function pluralizeCount(
  count: number,
  singular: string,
  plural?: string
) {
  if (count == 1) {
    return `${count} ${singular}`;
  }

  if (!plural) {
    return `${count} ${singular}s`;
  }

  return `${count} ${plural}`;
}

export function toTitleCase(value: string) {
  return value.toLowerCase().replace(/\b[a-z]/g, function (letter) {
    return letter.toUpperCase();
  });
}

export function findEntryFromExtendedCohortDef(
  entryId: string,
  extendedCohortDef: CriteriaSet[]
) {
  let found = null;
  extendedCohortDef.some((criteriaSet) => {
    criteriaSet.entries.some((entry) => {
      if (entry.entry_id === entryId) {
        found = entry;
        return true;
      }

      return false;
    });
  });

  return found;
}

/**
 * Returns the chart data used for displaying a histogram
 *
 * @param {Object} data The data to display the histogram
 */
export const generateHistogramData = (
  data: NumberConceptDetailedData["histogram_data"]
) => {
  const labels = data.map((item) => item[0]);
  const values = data.map((item) => item[1]);

  return { labels, values };
};

export const componentMap: { [k: string]: FC<{ data: any }> } = {
  category: CategoryOrBoolean,
  boolean: CategoryOrBoolean,
  number_with_categories: Number,
  number: Number,
  ontology: Ontology,
  text: Text,
  date: DateDisplay,
  age: AgeDisplay,
};
