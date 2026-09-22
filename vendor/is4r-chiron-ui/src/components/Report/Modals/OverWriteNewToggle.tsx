import { ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import {
  createReport,
  toggleCreateReportMethod,
} from "../../../store/reportSlice";

export default function OverWriteNewToggle() {
  const createReportMethod = useAppSelector(
    (state) => state.report.createReportMethod
  );
  const dataset = useAppSelector((state) => state.auth.dataset?.unique_id);
  const dispatch = useAppDispatch();
  return (
    <ToggleButtonGroup>
      <ToggleButtonGroup
        aria-label="Toggle Report Edit"
        exclusive={true}
        value={createReportMethod}
      >
        <ToggleButton
          value="new"
          key="new"
          onClick={function () {
            dispatch(toggleCreateReportMethod("new"));
            dispatch(createReport({ dataset: dataset ? dataset : "" }));
          }}
        >
          Create a new Report
        </ToggleButton>
        <ToggleButton
          value="overwrite"
          key="overwrite"
          onClick={() => dispatch(toggleCreateReportMethod("overwrite"))}
        >
          Overwrite an existing report
        </ToggleButton>
      </ToggleButtonGroup>
    </ToggleButtonGroup>
  );
}
