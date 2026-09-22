import {
  Search,
  ChevronLeft,
  ChevronRight,
  ErrorOutlined,
} from "@mui/icons-material";
import {
  Box,
  Button,
  TextField,
  InputAdornment,
  Typography,
  Collapse,
  useMediaQuery,
  IconButton,
} from "@mui/material";
import { grey, red } from "@mui/material/colors";
import { KeyboardEvent, useEffect, useRef, useState } from "react";
import Concept from "./Concept";
import Category from "./Category";
import ConceptsAndCategories from "./ConceptsAndCategories";
import SearchResults, { type SearchConcepts } from "./SearchResults";
import { useAppSelector } from "../../store/hooks";
import config from "../../config";
import { APIRequest } from "../../api";

type ConceptsProps = {
  conceptType: "cohort" | "table" | "analysis";
};

export type Concept = {
  include_in_table_def: boolean;
  include_in_cohort_def: boolean;
  include_in_analysis_def: boolean;
  permanent_id: string;
  name: string;
  has_phi: boolean;
  category: string | null;
};

export type Category = {
  id: string;
  name: string;
  parent: string | null;
  get_level: number;
};

export type Concepts = {
  concepts: Concept[];
  categories: Category[];
};

function hasConceptsOrCategories(data: Concepts | null) {
  if (data == null) {
    return false;
  }

  const concepts = data?.concepts?.length || 0;
  const categories = data?.categories?.length || 0;
  return concepts + categories < 1;
}

export default function Concepts({ conceptType = "cohort" }: ConceptsProps) {
  const searchRef = useRef<null | { value: string }>(null);
  const [concepts, setConcepts] = useState<null | Concepts>(null);
  const [searchResults, setSearchResults] = useState<null | SearchConcepts>(
    null
  );
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const panelWidth = useMediaQuery("(max-width: 1200px)") ? 240 : 320;

  useEffect(() => {
    if (searchRef.current) {
      if (dataset) {
        APIRequest(
          "GET",
          `/api/v2/${dataset}/concept_categories/?cohort_type=${conceptType}`
        ).then((data) => {
          setConcepts(data);
        });
      }
    }
  }, [conceptType, dataset]);

  async function handleSearch() {
    if (searchRef.current) {
      const data = await APIRequest(
        "GET",
        `/api/v2/${dataset}/concept_categories/concept_search?search=${searchRef.current.value}&concept_type=${conceptType}`
      );
      setSearchResults(data);
    }
  }

  function handleKeyUp(e: KeyboardEvent<HTMLImageElement>) {
    if (e.key === "Enter") {
      if (searchRef.current && searchRef.current.value === "") {
        clearSearch();
      } else {
        handleSearch();
      }
    }
  }

  function clearSearch() {
    setSearchResults(null);

    if (searchRef.current) {
      searchRef.current.value = "";
    }
  }

  const [checked, setChecked] = useState(
    window.innerWidth > 1200 || conceptType != "cohort"
  );
  useEffect(() => {
    function handleResize() {
      setChecked(window.innerWidth > 1200 || conceptType != "cohort");
    }

    window.addEventListener("resize", handleResize);

    return () => window.removeEventListener("resize", handleResize);
  }, [conceptType]);

  const handleChange = () => {
    setChecked((prev) => !prev);
  };

  return (
    <Box borderRight={1} borderColor={grey[300]}>
      <Collapse orientation="horizontal" in={checked}>
        <Box
          width={panelWidth}
          height="80vh"
          p={1}
          sx={{ overflowY: "auto", paddingBottom: "16rem" }}
        >
          <Box display="flex" pb={1}>
            <TextField
              inputProps={{ ref: searchRef }}
              fullWidth
              name="search"
              margin="none"
              size="small"
              defaultValue={""}
              label="Search Concepts..."
              type="search"
              onKeyUp={handleKeyUp}
              InputLabelProps={{
                sx: { color: config.table.conceptHeaderColor[800] },
              }}
              InputProps={{
                endAdornment: (
                  <InputAdornment
                    position="end"
                    sx={{
                      cursor: "pointer",
                      color: config.table.conceptHeaderColor[800],
                    }}
                    onClick={handleSearch}
                  >
                    <Search />
                  </InputAdornment>
                ),
              }}
            />
          </Box>
          {searchResults ? (
            <>
              <Button fullWidth onClick={clearSearch}>
                <ChevronLeft /> Back to all concepts
              </Button>
              <Box p={1}>
                {searchResults.concepts.length > 0 ? (
                  <Typography>
                    Results for "{searchRef.current?.value}":
                  </Typography>
                ) : (
                  <Typography>
                    No concepts found for "{searchRef.current?.value}"
                  </Typography>
                )}
              </Box>
              <SearchResults
                concepts={searchResults.concepts}
                conceptType={conceptType}
              />
            </>
          ) : (
            <>
              <ConceptsAndCategories
                data={concepts}
                conceptType={conceptType}
              />
              {hasConceptsOrCategories(concepts) ? (
                <Box p={4} textAlign="center" color={red[800]}>
                  <ErrorOutlined fontSize="large" />
                  <Typography>Could not find any concepts</Typography>
                </Box>
              ) : null}
            </>
          )}
        </Box>
      </Collapse>
      {conceptType == "cohort" ? (
        <Box
          position="absolute"
          top={140}
          sx={{ transition: "left ease 0.3s" }}
          left={checked ? panelWidth - 12 : -10}
        >
          <IconButton
            size="small"
            title={checked ? "Hide Concepts" : "Show Concepts"}
            sx={{
              border: "1px solid",
              borderRadius: "100%",
              backgroundColor: "white",
              "&:hover": {
                backgroundColor: config.table.conceptHeaderColor,
                color:
                  config.table.conceptHeaderShade == "dark" ? "white" : "black",
              },
            }}
            onClick={handleChange}
          >
            {checked ? <ChevronLeft /> : <ChevronRight />}
          </IconButton>
        </Box>
      ) : null}
    </Box>
  );
}
