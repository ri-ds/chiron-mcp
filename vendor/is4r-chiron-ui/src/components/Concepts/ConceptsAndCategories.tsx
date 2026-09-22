import { Box, Skeleton } from "@mui/material";
import Concept from "./Concept";
import Category from "./Category";
import { grey } from "@mui/material/colors";
import type { Concepts } from ".";

type ConceptsAndCategoriesProps = {
  data: Concepts | null;
  conceptType: "cohort" | "table" | "analysis";
};

export default function ConceptsAndCategories({
  data,
  conceptType,
}: ConceptsAndCategoriesProps) {
  if (!data) {
    return (
      <Box mt={1}>
        {Array(12)
          .fill(null)
          .map((_, i) => (
            <Skeleton
              key={i}
              variant="text"
              sx={{ my: -2, height: "3.5rem" }}
            />
          ))}
      </Box>
    );
  }

  return (
    <>
      {data.concepts.length ? (
        <Box sx={{ border: "1px solid", borderColor: grey[300] }}>
          {data.concepts.map((concept) => (
            <Concept
              key={concept.permanent_id}
              concept={concept}
              conceptType={conceptType}
            />
          ))}
        </Box>
      ) : null}
      {data.categories.length ? (
        <Box sx={{ border: "1px solid", borderColor: grey[300] }}>
          {data.categories.map((category) => (
            <Category
              key={category.id}
              category={category}
              conceptType={conceptType}
            />
          ))}
        </Box>
      ) : null}
    </>
  );
}
