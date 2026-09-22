import { Box } from "@mui/material";
import Filters from "../components/Filters";
import AggregateHeader from "../components/Aggregate/Header";
import AggregateTable from "../components/Aggregate/Table";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { loadAggregateDef } from "../store/aggregateSlice";
import { useEffect } from "react";

export default function AggregateRoute() {
  const dispatch = useAppDispatch();

  const aggStatus = useAppSelector((state) => state.aggregate.aggStatus);
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);

  useEffect(() => {
    if (dataset) {
      dispatch(loadAggregateDef({ dataset: dataset }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset]);

  return (
    <Box display="flex">
      <Box flexGrow={1} overflow={"scroll"}>
        <Box>
          <AggregateHeader></AggregateHeader>
          {aggStatus != "failed" ? <AggregateTable></AggregateTable> : null}
        </Box>
      </Box>
      <Box>
        <Filters resultsDisplay />
      </Box>
    </Box>
  );
}
