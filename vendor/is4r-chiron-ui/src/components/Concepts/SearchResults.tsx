import { Button, Typography } from "@mui/material";
import { styled } from "@mui/material/styles";
import { grey } from "@mui/material/colors";
import { type Category } from "./";
import {
  selectQueryConcept,
  loadConceptDisplay,
} from "../../store/cohortSlice";
import { applyTransformation } from "../../store/tableSlice";
import { useAppDispatch, useAppSelector } from "../../store/hooks";
export type SearchConcepts = {
  concepts: SearchConcept[];
};

export type SearchConcept = {
  permanent_id: string;
  name: string;
  category_hierarchy: Category[] | null;
};

const SearchConceptButton = styled(Button)(() => ({
  flexDirection: "column",
  color: "black",
  alignItems: "start",
  borderColor: grey[400],
}));

export default function SearchResults({
  concepts,
  conceptType,
}: {
  concepts: SearchConcept[];
  conceptType: "cohort" | "table" | "analysis";
}) {
  const dispatch = useAppDispatch();
  const showDataType = useAppSelector((state) => state.cohort.showDataType);
  const queryConcept = useAppSelector((state) => state.cohort.queryConcept);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const aggSelect: "Rows" | "Columns" | undefined = useAppSelector(
    (state) => state.aggregate.modalView
  );
  const columns = useAppSelector((state) => state.table.columns);
  const aggColumns = useAppSelector((state) => state.aggregate.columns);
  const aggRows = useAppSelector((state) => state.aggregate.rows);

  //hiding based on concept settings
  return concepts.map((concept) => (
    <SearchConceptButton
      key={concept.permanent_id}
      fullWidth
      variant="outlined"
      sx={{
        display: {
          function() {
            const showString: string = `include_in_${conceptType}_def`;
            type ObjectKey = keyof typeof concept;
            const showProp = showString as ObjectKey;
            return concept[showProp] ? "" : "none";
          },
        },
      }}
      onClick={() => {
        let isSelected: undefined | boolean =
          queryConcept === concept.permanent_id;
        if (conceptType == "table") {
          isSelected = columns?.some(
            (column) => column.entryId === concept.permanent_id
          );
        }
        if (conceptType == "analysis") {
          isSelected = aggColumns
            .concat(aggRows)
            .some((column) => column.conceptId === concept.permanent_id);
        }
        dispatch(
          selectQueryConcept({
            dataset: dataset ? dataset : "",
            conceptId: concept.permanent_id,
            edit: undefined,
            conceptType,
          })
        );

        if (conceptType === "cohort") {
          dispatch(
            loadConceptDisplay({
              dataset: dataset ? dataset : "",
              conceptId: concept.permanent_id,
              showDataType,
            })
          );
        } else {
          if (!isSelected) {
            if (conceptType == "table") {
              dispatch(
                applyTransformation({
                  transformation: {
                    type: "add_entry",
                    concept_id: concept.permanent_id,
                  },
                  dataset: dataset ? dataset : "",
                })
              );
            }
            if (conceptType == "analysis") {
              if (aggSelect == "Rows" || aggSelect == "Columns") {
                dispatch(
                  applyTransformation({
                    transformation: {
                      type: "add_entry",
                      concept_id: concept.permanent_id,
                      role: aggSelect == "Rows" ? "rows" : "cols",
                    },
                    dataset: dataset ? dataset : "",
                  })
                );
              }
            }
          }
        }
      }}
    >
      <Typography
        variant="h6"
        textAlign="left"
        textTransform="none"
        fontSize="1rem"
      >
        {concept.name}
      </Typography>
      <Typography
        variant="subtitle1"
        textAlign="left"
        textTransform="none"
        color={grey[500]}
        fontSize="0.8rem"
      >
        {`${concept.category_hierarchy?.map((ch: Category) => ch.name).join(" > ")} > ${concept.name}`}
      </Typography>
    </SearchConceptButton>
  ));
}
