import { Button } from "@mui/material";
import type { Category, Concepts } from "../Concepts";
import { darken, styled } from "@mui/material/styles";
import { ArrowDropDown, ArrowDropUp } from "@mui/icons-material";
import { colorStep, textColor } from "../../lib/utils";
import { useState, useEffect } from "react";
import ConceptsAndCategories from "./ConceptsAndCategories";
import { useAppSelector } from "../../store/hooks";
import config from "../../config";
import { APIRequest } from "../../api";
type CategoryProps = {
  category: Category;
  conceptType: "cohort" | "table" | "analysis";
};

const CategoryButton = styled(Button)(() => ({
  justifyContent: "start",
  color: config.table.conceptHeaderColor[900],
  borderRadius: 0,
  borderCollapse: "collapse",
  border: "1px solid",
  borderColor: config.table.conceptHeaderColor[400],
  textTransform: "none",
  textAlign: "left",
}));

export default function Category({ category, conceptType }: CategoryProps) {
  const [expanded, setExpanded] = useState<boolean>(false);
  const [data, setData] = useState<Concepts | null>(null);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);

  useEffect(() => {
    if (expanded) {
      APIRequest(
        "GET",
        `/api/v2/${dataset}/concept_categories/${category.id}/`
      ).then((data) => {
        setData(data);
      });
    }
  }, [expanded, category.id, dataset]);

  const prefix = ">".repeat(category.get_level);
  return (
    <>
      <CategoryButton
        fullWidth
        sx={{
          my: 0.25,
          justifyContent: "space-between",
          border: 0,
          bgcolor: colorStep(category.get_level),
          color: textColor(category.get_level),
          ":hover": {
            bgcolor: darken(colorStep(category.get_level), 0.05),
          },
        }}
        onClick={() => setExpanded(!expanded)}
        title={category.name}
      >
        {prefix} {category.name}{" "}
        {expanded ? <ArrowDropDown /> : <ArrowDropUp />}
      </CategoryButton>
      {expanded ? (
        <ConceptsAndCategories data={data} conceptType={conceptType} />
      ) : null}
    </>
  );
}
