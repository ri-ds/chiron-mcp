import { describe, test, expect } from "vitest";
import { deepMerge, isObject } from "../src/lib/utils";

describe("Utils tests", () => {
  test("isObject tests", () => {
    let result = isObject("test");
    expect(result).toBeFalsy();
    result = isObject(1);
    expect(result).toBeFalsy();
    result = isObject(1.0);
    expect(result).toBeFalsy();
    result = isObject([]);
    expect(result).toBeFalsy();
    result = isObject({});
    expect(result).toBeTruthy();
    result = isObject({ test: "bleh" });
    expect(result).toBeTruthy();
  });

  test("DeepMerge tests", () => {
    let result = deepMerge({ test: { yeah: "no" } }, { test: { yeah: "yes" } });
    expect(result).toEqual({ test: { yeah: "yes" } });
    result = deepMerge(
      { test: { yeah: { another: "no" } } },
      { test: { yeah: { different: "yes" } } }
    );
    expect(result).toEqual({
      test: { yeah: { another: "no", different: "yes" } },
    });
  });
});
